#!/bin/bash
# =============================================================================
# Heracles Demo - SSSD Setup for LDAP Authentication
# =============================================================================
# This script configures SSSD (System Security Services Daemon) to authenticate
# users against the Heracles LDAP server.
#
# Arguments:
#   $1 - Hostname (for host-based access filtering)
#
# Configuration is loaded from /vagrant/config/demo.conf
# Templates are in /vagrant/config/templates/
# =============================================================================

set -e

# Load configuration
CONFIG_DIR="/vagrant/config"
source "${CONFIG_DIR}/demo.conf"

HOSTNAME="${1:-$(hostname -s)}"

echo "=============================================="
echo "  Heracles Demo - SSSD Setup"
echo "=============================================="
echo "LDAP Server: ${LDAP_HOST}:${LDAP_PORT}"
echo "Base DN: ${LDAP_BASE_DN}"
echo "Hostname: ${HOSTNAME}"
echo "=============================================="

# -----------------------------------------------------------------------------
# Install required packages
# -----------------------------------------------------------------------------
echo "[1/7] Installing SSSD and dependencies..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
    sssd \
    sssd-ldap \
    sssd-tools \
    ldap-utils \
    libnss-sss \
    libpam-sss \
    libsss-sudo \
    oddjob-mkhomedir \
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
# Configure SSSD from template
# -----------------------------------------------------------------------------
echo "[3/7] Configuring SSSD from template..."

# Process template
bash "${CONFIG_DIR}/process_template.sh" \
    "${CONFIG_DIR}/templates/sssd.conf.template" \
    /etc/sssd/sssd.conf

# Set proper permissions
chmod 600 /etc/sssd/sssd.conf
chown root:root /etc/sssd/sssd.conf

# -----------------------------------------------------------------------------
# Configure NSS (Name Service Switch)
# -----------------------------------------------------------------------------
echo "[4/7] Configuring NSS..."

# Backup original nsswitch.conf
cp /etc/nsswitch.conf /etc/nsswitch.conf.bak

# Process template
bash "${CONFIG_DIR}/process_template.sh" \
    "${CONFIG_DIR}/templates/nsswitch.conf.template" \
    /etc/nsswitch.conf

# -----------------------------------------------------------------------------
# Configure PAM for home directory creation
# -----------------------------------------------------------------------------
echo "[5/7] Configuring PAM for automatic home directory creation..."

# Enable mkhomedir in PAM
cat > /usr/share/pam-configs/mkhomedir << EOF
Name: Create home directory on login
Default: yes
Priority: 900
Session-Type: Additional
Session:
    required    pam_mkhomedir.so umask=0077 skel=/etc/skel
EOF

# Update PAM configuration
pam-auth-update --enable mkhomedir --force 2>/dev/null || true

# Alternative: Direct PAM configuration
if ! grep -q "pam_mkhomedir.so" /etc/pam.d/common-session; then
    echo "session required pam_mkhomedir.so skel=/etc/skel umask=0077" >> /etc/pam.d/common-session
fi

# -----------------------------------------------------------------------------
# Configure sudoers to use SSSD
# -----------------------------------------------------------------------------
echo "[6/7] Configuring sudoers for SSSD..."

# Process template
bash "${CONFIG_DIR}/process_template.sh" \
    "${CONFIG_DIR}/templates/sudo-ldap.conf.template" \
    /etc/sudo-ldap.conf

chmod 440 /etc/sudo-ldap.conf

# -----------------------------------------------------------------------------
# Start and enable SSSD
# -----------------------------------------------------------------------------
echo "[7/7] Starting SSSD service..."

# Clear SSSD cache
rm -rf /var/lib/sss/db/* 2>/dev/null || true
rm -rf /var/lib/sss/mc/* 2>/dev/null || true

# Enable and restart SSSD
systemctl enable sssd
systemctl restart sssd

# Wait for SSSD to be ready
sleep 3

# Verify SSSD is running
if systemctl is-active --quiet sssd; then
    echo "✅ SSSD is running"
else
    echo "❌ SSSD failed to start"
    journalctl -u sssd --no-pager -n 20
    exit 1
fi

# -----------------------------------------------------------------------------
# Verification
# -----------------------------------------------------------------------------
echo ""
echo "=============================================="
echo "  SSSD Setup Complete!"
echo "=============================================="
echo ""
echo "Testing LDAP connectivity..."
if LDAPTLS_CACERT="${LDAP_CA_CERT}" LDAPTLS_REQCERT=hard ldapsearch -x -H "ldaps://${LDAP_HOST}:${LDAP_PORT}" -b "${LDAP_BASE_DN}" -D "${LDAP_BIND_DN}" -w "${LDAP_BIND_PASSWORD}" "(objectClass=organization)" dn 2>/dev/null | grep -q "dn:"; then
    echo "✅ LDAP connection successful"
else
    echo "⚠️  LDAP connection test failed (server may not be ready)"
fi

echo ""
echo "To verify LDAP users are visible, run:"
echo "  getent passwd"
echo ""
