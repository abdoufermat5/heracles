#!/bin/bash
# =============================================================================
# Heracles Demo - ISC DHCP Server Setup
# =============================================================================
# This script configures ISC DHCP server with LDAP backend for the
# heracles.local domain, with configuration synchronized from LDAP.
#
# Configuration is loaded from /vagrant/config/demo.conf
# Templates are in /vagrant/config/templates/
# =============================================================================

set -e

# Load configuration
CONFIG_DIR="/vagrant/config"
source "${CONFIG_DIR}/demo.conf"

echo "=============================================="
echo "  Heracles Demo - ISC DHCP Server Setup"
echo "=============================================="
echo "LDAP Server: ${LDAP_HOST}:${LDAP_PORT}"
echo "Base DN: ${LDAP_BASE_DN}"
echo "DHCP Subnet: ${DHCP_SUBNET}/${DHCP_NETMASK}"
echo "Dynamic Pool: ${DHCP_RANGE_START} - ${DHCP_RANGE_END}"
echo "=============================================="

# -----------------------------------------------------------------------------
# Install ISC DHCP Server
# -----------------------------------------------------------------------------
echo "[1/7] Installing ISC DHCP Server..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
    isc-dhcp-server \
    ldap-utils \
    ca-certificates \
    2>/dev/null

# -----------------------------------------------------------------------------
# Install dev CA certificate
# -----------------------------------------------------------------------------
echo "[2/7] Installing Heracles dev CA..."
if [ -f "${DEV_CA_CERT_SOURCE}" ]; then
    cp "${DEV_CA_CERT_SOURCE}" "${LDAP_CA_CERT}"
    update-ca-certificates 2>/dev/null || true
else
    echo "⚠️  Dev CA not found at ${DEV_CA_CERT_SOURCE}"
fi

# -----------------------------------------------------------------------------
# Configure network interface for DHCP
# -----------------------------------------------------------------------------
echo "[3/7] Configuring DHCP network interface..."

# Determine the interface for the private network (192.168.56.0/24)
DHCP_INTERFACE=$(ip -o addr show | grep "192.168.56" | awk '{print $2}' | head -1)

if [ -z "$DHCP_INTERFACE" ]; then
    echo "WARNING: Could not detect DHCP interface, using eth1 as default"
    DHCP_INTERFACE="eth1"
fi

echo "DHCP will listen on interface: $DHCP_INTERFACE"

# Configure ISC DHCP defaults
cat > /etc/default/isc-dhcp-server << EOF
# Defaults for isc-dhcp-server (sourced by /etc/init.d/isc-dhcp-server)

# Path to dhcpd's config file
DHCPDv4_CONF=/etc/dhcp/dhcpd.conf

# Interface(s) on which dhcpd should serve DHCP requests
INTERFACESv4="$DHCP_INTERFACE"
INTERFACESv6=""
EOF

# -----------------------------------------------------------------------------
# Create base DHCP configuration from template
# -----------------------------------------------------------------------------
echo "[4/7] Creating base DHCP configuration..."

# Process template
bash "${CONFIG_DIR}/process_template.sh" \
    "${CONFIG_DIR}/templates/dhcpd.conf.template" \
    /etc/dhcp/dhcpd.conf.base

# Copy base config as initial config
cp /etc/dhcp/dhcpd.conf.base /etc/dhcp/dhcpd.conf

# -----------------------------------------------------------------------------
# Install LDAP DHCP sync script
# -----------------------------------------------------------------------------
echo "[5/7] Installing LDAP DHCP sync script..."

# Process template
bash "${CONFIG_DIR}/process_template.sh" \
    "${CONFIG_DIR}/templates/ldap-dhcp-sync.sh.template" \
    /usr/local/bin/ldap-dhcp-sync.sh

chmod 755 /usr/local/bin/ldap-dhcp-sync.sh

# Create cron job for periodic sync
cat > /etc/cron.d/ldap-dhcp-sync << EOF
# Sync DHCP configuration from LDAP every 5 minutes
*/5 * * * * root /usr/local/bin/ldap-dhcp-sync.sh >/var/log/ldap-dhcp-sync.log 2>&1 && systemctl reload isc-dhcp-server >/dev/null 2>&1 || true
EOF

# Create systemd timer as alternative
cat > /etc/systemd/system/ldap-dhcp-sync.service << EOF
[Unit]
Description=Sync DHCP configuration from LDAP
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/ldap-dhcp-sync.sh
ExecStartPost=/bin/sh -c 'systemctl reload isc-dhcp-server || true'
StandardOutput=append:/var/log/ldap-dhcp-sync.log
StandardError=append:/var/log/ldap-dhcp-sync.log
EOF

cat > /etc/systemd/system/ldap-dhcp-sync.timer << EOF
[Unit]
Description=Run LDAP DHCP sync every 5 minutes

[Timer]
OnBootSec=1min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable ldap-dhcp-sync.timer
systemctl start ldap-dhcp-sync.timer

# -----------------------------------------------------------------------------
# Create initial minimal configuration for startup
# -----------------------------------------------------------------------------
echo "[6/7] Creating initial DHCP configuration..."

# Create a minimal valid config that will be replaced by sync
cat > /etc/dhcp/dhcpd.conf << EOF
# =============================================================================
# ISC DHCP Server Configuration
# =============================================================================
# This file is managed by LDAP sync script
# Manual changes will be overwritten
# =============================================================================

authoritative;
ddns-update-style interim;
ddns-updates on;
update-static-leases on;
log-facility local7;

default-lease-time ${DHCP_LEASE_TIME};
max-lease-time 7200;

option domain-name "${DOMAIN}";
option domain-name-servers ${DHCP_DNS};

ddns-domainname "${DOMAIN}.";
ddns-rev-domainname "in-addr.arpa.";

# DDNS zones
zone ${DOMAIN}. {
    primary ${DHCP_DNS};
}

zone 56.168.192.in-addr.arpa. {
    primary ${DHCP_DNS};
}

# Subnet configuration
subnet ${DHCP_SUBNET} netmask 255.255.255.0 {
    option routers ${DHCP_ROUTER};
    option broadcast-address 192.168.56.255;
    option subnet-mask 255.255.255.0;
    
    pool {
        range ${DHCP_RANGE_START} ${DHCP_RANGE_END};
        allow unknown-clients;
        default-lease-time ${DHCP_LEASE_TIME};
        max-lease-time 7200;
    }
}

# Static host reservations will be added by LDAP sync
EOF

# Create lease file
touch /var/lib/dhcp/dhcpd.leases
chown dhcpd:dhcpd /var/lib/dhcp/dhcpd.leases 2>/dev/null || true

# -----------------------------------------------------------------------------
# Start DHCP Server
# -----------------------------------------------------------------------------
echo "[7/7] Starting ISC DHCP Server..."

# Validate configuration
if dhcpd -t -cf /etc/dhcp/dhcpd.conf; then
    echo "✅ DHCP configuration is valid"
else
    echo "❌ DHCP configuration is invalid"
    exit 1
fi

# Enable and start DHCP server
systemctl enable isc-dhcp-server
systemctl restart isc-dhcp-server

# Wait for service to start
sleep 2

if systemctl is-active --quiet isc-dhcp-server; then
    echo "✅ ISC DHCP Server is running"
else
    echo "❌ ISC DHCP Server failed to start"
    journalctl -u isc-dhcp-server --no-pager -n 20
    exit 1
fi

# Initial sync from LDAP (may fail if LDAP doesn't have DHCP config yet)
echo ""
echo "Running initial LDAP sync..."
/usr/local/bin/ldap-dhcp-sync.sh 2>&1 || echo "⚠️ Initial sync failed (DHCP config may not exist in LDAP yet)"

# Reload config if sync succeeded
if [ -f /etc/dhcp/dhcpd.conf ]; then
    systemctl reload isc-dhcp-server 2>/dev/null || true
fi

echo ""
echo "=============================================="
echo "  DHCP Server Setup Complete!"
echo "=============================================="
echo ""
echo "DHCP Configuration:"
echo "  - Interface: $DHCP_INTERFACE"
echo "  - Subnet: ${DHCP_SUBNET}/${DHCP_NETMASK}"
echo "  - Pool: ${DHCP_RANGE_START} - ${DHCP_RANGE_END}"
echo "  - Router: ${DHCP_ROUTER}"
echo "  - DNS: ${DHCP_DNS}"
echo "  - Domain: ${DOMAIN}"
echo ""
echo "LDAP Sync:"
echo "  - Script: /usr/local/bin/ldap-dhcp-sync.sh"
echo "  - Interval: Every 5 minutes"
echo "  - Log: /var/log/ldap-dhcp-sync.log"
echo ""
echo "Testing:"
echo "  - View leases: cat /var/lib/dhcp/dhcpd.leases"
echo "  - View config: cat /etc/dhcp/dhcpd.conf"
echo "  - Logs: journalctl -u isc-dhcp-server -f"
echo ""
