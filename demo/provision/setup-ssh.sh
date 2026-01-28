#!/bin/bash
# =============================================================================
# Heracles Demo - SSH Setup for LDAP Public Keys
# =============================================================================
# This script configures OpenSSH to fetch authorized keys from LDAP using
# the AuthorizedKeysCommand directive.
#
# Configuration is loaded from /vagrant/config/demo.conf
# Templates are in /vagrant/config/templates/
# =============================================================================

set -e

# Load configuration
CONFIG_DIR="/vagrant/config"
source "${CONFIG_DIR}/demo.conf"

echo "=============================================="
echo "  Heracles Demo - SSH LDAP Keys Setup"
echo "=============================================="
echo "LDAP Server: ${LDAP_HOST}:${LDAP_PORT}"
echo "Base DN: ${LDAP_BASE_DN}"
echo "=============================================="

# -----------------------------------------------------------------------------
# Install required packages
# -----------------------------------------------------------------------------
echo "[1/4] Installing SSH and LDAP utilities..."
export DEBIAN_FRONTEND=noninteractive
apt-get install -y -qq \
    openssh-server \
    ldap-utils \
    libsss-sudo \
    2>/dev/null

# -----------------------------------------------------------------------------
# Create SSH LDAP key fetcher script from template
# -----------------------------------------------------------------------------
echo "[2/4] Creating SSH authorized keys command script..."

# Process template
bash "${CONFIG_DIR}/process_template.sh" \
    "${CONFIG_DIR}/templates/ldap-ssh-keys.sh.template" \
    /usr/local/bin/ldap-ssh-keys.sh

chmod 755 /usr/local/bin/ldap-ssh-keys.sh

# -----------------------------------------------------------------------------
# Configure SSH daemon
# -----------------------------------------------------------------------------
echo "[3/4] Configuring SSH daemon..."

# Backup original sshd_config
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak

# Process template
bash "${CONFIG_DIR}/process_template.sh" \
    "${CONFIG_DIR}/templates/sshd_config.template" \
    /etc/ssh/sshd_config

# Validate SSH config
if sshd -t; then
    echo "✅ SSH config is valid"
else
    echo "❌ SSH config is invalid, restoring backup"
    cp /etc/ssh/sshd_config.bak /etc/ssh/sshd_config
    exit 1
fi

# -----------------------------------------------------------------------------
# Restart SSH service
# -----------------------------------------------------------------------------
echo "[4/4] Restarting SSH service..."

systemctl restart sshd

if systemctl is-active --quiet sshd; then
    echo "✅ SSH service is running"
else
    echo "❌ SSH service failed to start"
    exit 1
fi

# -----------------------------------------------------------------------------
# Verification
# -----------------------------------------------------------------------------
echo ""
echo "=============================================="
echo "  SSH LDAP Keys Setup Complete!"
echo "=============================================="
echo ""
echo "To test SSH with LDAP public keys, run from host:"
echo "  ssh -i ~/.ssh/id_ed25519 <username>@$(hostname -I | awk '{print $2}')"
echo ""
echo "To manually test key fetching:"
echo "  /usr/local/bin/ldap-ssh-keys.sh <username>"
echo ""
