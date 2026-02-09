#!/bin/bash
# =============================================================================
# Heracles Demo - Sudo LDAP Setup
# =============================================================================
# This script configures sudo to fetch sudoers rules from LDAP via SSSD.
#
# Configuration is loaded from /vagrant/config/demo.conf
# Templates are in /vagrant/config/templates/
# =============================================================================

set -e

# Load configuration
CONFIG_DIR="/vagrant/config"
source "${CONFIG_DIR}/demo.conf"

HOSTNAME="$(hostname -s)"

echo "=============================================="
echo "  Heracles Demo - Sudo LDAP Setup"
echo "=============================================="
echo "LDAP Server: ${LDAP_HOST}:${LDAP_PORT}"
echo "Base DN: ${LDAP_BASE_DN}"
echo "Hostname: ${HOSTNAME}"
echo "=============================================="

# -----------------------------------------------------------------------------
# Install required packages
# -----------------------------------------------------------------------------
echo "[1/4] Installing sudo and dependencies..."
export DEBIAN_FRONTEND=noninteractive
apt-get install -y -qq \
    sudo \
    ldap-utils \
    2>/dev/null

# -----------------------------------------------------------------------------
# Configure nsswitch.conf for sudo
# -----------------------------------------------------------------------------
echo "[2/4] Configuring nsswitch.conf for sudo..."

# Ensure sudoers uses SSSD (should already be done by setup-sssd.sh)
if ! grep -q "^sudoers:.*sss" /etc/nsswitch.conf; then
    if grep -q "^sudoers:" /etc/nsswitch.conf; then
        sed -i 's/^sudoers:.*/sudoers:        files sss/' /etc/nsswitch.conf
    else
        echo "sudoers:        files sss" >> /etc/nsswitch.conf
    fi
fi

# -----------------------------------------------------------------------------
# Configure sudo-ldap.conf (backup for SSSD)
# -----------------------------------------------------------------------------
echo "[3/4] Configuring sudo-ldap.conf..."

# Process template (should already be done by setup-sssd.sh but ensure it exists)
if [ ! -f /etc/sudo-ldap.conf ]; then
    bash "${CONFIG_DIR}/process_template.sh" \
        "${CONFIG_DIR}/templates/sudo-ldap.conf.template" \
        /etc/sudo-ldap.conf
    chmod 440 /etc/sudo-ldap.conf
fi

# -----------------------------------------------------------------------------
# Clear SSSD cache to pick up sudo rules
# -----------------------------------------------------------------------------
echo "[4/4] Clearing SSSD cache for sudo rules..."

# Clear SSSD sudo cache
sss_cache -s 2>/dev/null || true

# Restart SSSD to ensure it picks up sudo rules
systemctl restart sssd 2>/dev/null || true

# -----------------------------------------------------------------------------
# Verification
# -----------------------------------------------------------------------------
echo ""
echo "=============================================="
echo "  Sudo LDAP Setup Complete!"
echo "=============================================="
echo ""
echo "To test sudo rules from LDAP, run:"
echo "  sudo -l -U <username>"
echo ""
echo "To list sudo rules from LDAP:"
echo "  ldapsearch -x -H ldaps://${LDAP_HOST}:${LDAP_PORT} \\"
echo "    -b 'ou=sudoers,${LDAP_BASE_DN}' '(objectClass=sudoRole)'"
echo ""
