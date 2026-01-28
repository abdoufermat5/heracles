#!/bin/bash
# =============================================================================
# Heracles Demo - BIND9 DNS Server Setup
# =============================================================================
# This script configures BIND9 as an authoritative DNS server for the
# heracles.local domain, with zone data synchronized from LDAP.
#
# Configuration is loaded from /vagrant/config/demo.conf
# Templates are in /vagrant/config/templates/
# =============================================================================

set -e

# Load configuration
CONFIG_DIR="/vagrant/config"
source "${CONFIG_DIR}/demo.conf"

echo "=============================================="
echo "  Heracles Demo - BIND9 DNS Server Setup"
echo "=============================================="
echo "LDAP Server: ${LDAP_HOST}:${LDAP_PORT}"
echo "Base DN: ${LDAP_BASE_DN}"
echo "Forward Zone: ${DNS_FORWARD_ZONE}"
echo "Reverse Zone: ${DNS_REVERSE_ZONE}"
echo "=============================================="

# -----------------------------------------------------------------------------
# Install BIND9
# -----------------------------------------------------------------------------
echo "[1/5] Installing BIND9..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
    bind9 \
    bind9-dnsutils \
    ldap-utils \
    2>/dev/null

# -----------------------------------------------------------------------------
# Configure BIND options from template
# -----------------------------------------------------------------------------
echo "[2/5] Configuring BIND9 options..."

# Process template
bash "${CONFIG_DIR}/process_template.sh" \
    "${CONFIG_DIR}/templates/named.conf.options.template" \
    /etc/bind/named.conf.options

# -----------------------------------------------------------------------------
# Configure local zones from template
# -----------------------------------------------------------------------------
echo "[3/5] Configuring local zones..."

# Process template
bash "${CONFIG_DIR}/process_template.sh" \
    "${CONFIG_DIR}/templates/named.conf.local.template" \
    /etc/bind/named.conf.local

# Create zone files directory
mkdir -p /var/lib/bind
chown bind:bind /var/lib/bind

# Create initial empty zone files (will be populated by LDAP sync)
cat > "/var/lib/bind/${DNS_FORWARD_ZONE}.zone" << EOF
; Zone file for ${DNS_FORWARD_ZONE}
; Placeholder - will be populated by LDAP sync
\$TTL 86400
\$ORIGIN ${DNS_FORWARD_ZONE}.

@    IN    SOA    ns1.${DNS_FORWARD_ZONE}. admin.${DNS_FORWARD_ZONE}. (
    $(date +%Y%m%d)01  ; Serial
    3600               ; Refresh
    1800               ; Retry
    604800             ; Expire
    86400              ; Minimum TTL
)

@    IN    NS    ns1.${DNS_FORWARD_ZONE}.
ns1  IN    A     ${NS1_IP}
EOF

cat > "/var/lib/bind/${DNS_REVERSE_ZONE}.zone" << EOF
; Reverse zone file for ${DNS_REVERSE_ZONE}
; Placeholder - will be populated by LDAP sync
\$TTL 86400
\$ORIGIN ${DNS_REVERSE_ZONE}.

@    IN    SOA    ns1.${DNS_FORWARD_ZONE}. admin.${DNS_FORWARD_ZONE}. (
    $(date +%Y%m%d)01  ; Serial
    3600               ; Refresh
    1800               ; Retry
    604800             ; Expire
    86400              ; Minimum TTL
)

@    IN    NS    ns1.${DNS_FORWARD_ZONE}.
20   IN    PTR   ns1.${DNS_FORWARD_ZONE}.
EOF

chown bind:bind /var/lib/bind/*.zone
chmod 644 /var/lib/bind/*.zone

# -----------------------------------------------------------------------------
# Install LDAP DNS sync script
# -----------------------------------------------------------------------------
echo "[4/5] Installing LDAP DNS sync script..."

# Process template
bash "${CONFIG_DIR}/process_template.sh" \
    "${CONFIG_DIR}/templates/ldap-dns-sync.sh.template" \
    /usr/local/bin/ldap-dns-sync.sh

chmod 755 /usr/local/bin/ldap-dns-sync.sh

# Create cron job for periodic sync
cat > /etc/cron.d/ldap-dns-sync << EOF
# Sync DNS zones from LDAP every 5 minutes
*/5 * * * * root /usr/local/bin/ldap-dns-sync.sh >/dev/null 2>&1 && systemctl reload named >/dev/null 2>&1
EOF

# Create systemd timer as alternative
cat > /etc/systemd/system/ldap-dns-sync.service << EOF
[Unit]
Description=Sync DNS zones from LDAP
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/ldap-dns-sync.sh
ExecStartPost=/usr/bin/systemctl reload named
EOF

cat > /etc/systemd/system/ldap-dns-sync.timer << EOF
[Unit]
Description=Run LDAP DNS sync every 5 minutes

[Timer]
OnBootSec=1min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable ldap-dns-sync.timer
systemctl start ldap-dns-sync.timer

# -----------------------------------------------------------------------------
# Start BIND9
# -----------------------------------------------------------------------------
echo "[5/5] Starting BIND9..."

# Validate configuration
if named-checkconf; then
    echo "✅ BIND9 configuration is valid"
else
    echo "❌ BIND9 configuration is invalid"
    exit 1
fi

# Enable and start BIND9
systemctl enable named
systemctl restart named

# Wait for service to start
sleep 2

if systemctl is-active --quiet named; then
    echo "✅ BIND9 is running"
else
    echo "❌ BIND9 failed to start"
    journalctl -u named --no-pager -n 20
    exit 1
fi

# Initial sync from LDAP
echo ""
echo "Running initial LDAP sync..."
/usr/local/bin/ldap-dns-sync.sh || echo "⚠️ Initial sync failed (zones may not exist in LDAP yet)"
systemctl reload named 2>/dev/null || true

# -----------------------------------------------------------------------------
# Verification
# -----------------------------------------------------------------------------
echo ""
echo "=============================================="
echo "  BIND9 DNS Server Setup Complete!"
echo "=============================================="
echo ""
echo "DNS Server: ${NS1_IP}"
echo "Forward Zone: ${DNS_FORWARD_ZONE}"
echo "Reverse Zone: ${DNS_REVERSE_ZONE}"
echo ""
echo "Test commands:"
echo "  dig @${NS1_IP} ns1.${DNS_FORWARD_ZONE}"
echo "  dig @${NS1_IP} -x ${NS1_IP}"
echo ""
echo "To manually sync from LDAP:"
echo "  /usr/local/bin/ldap-dns-sync.sh && systemctl reload named"
echo ""
