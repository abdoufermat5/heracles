#!/bin/bash
# =============================================================================
# Heracles Demo - Sudo LDAP Setup
# =============================================================================
# This script configures sudo to fetch sudoers rules from LDAP via SSSD.
# Rules are stored in the sudoRole objectClass under ou=sudoers.
#
# Arguments:
#   $1 - LDAP server IP
#   $2 - LDAP port
#   $3 - LDAP base DN
#   $4 - LDAP bind DN
#   $5 - LDAP bind password
# =============================================================================

set -e

LDAP_SERVER_IP="${1:-192.168.56.1}"
LDAP_PORT="${2:-389}"
LDAP_BASE_DN="${3:-dc=heracles,dc=local}"
LDAP_BIND_DN="${4:-cn=admin,dc=heracles,dc=local}"
LDAP_BIND_PASSWORD="${5:-admin_secret}"
HOSTNAME="$(hostname -s)"

echo "=============================================="
echo "  Heracles Demo - Sudo LDAP Setup"
echo "=============================================="
echo "LDAP Server: ${LDAP_SERVER_IP}:${LDAP_PORT}"
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

# Ensure sudoers uses SSSD
if ! grep -q "^sudoers:.*sss" /etc/nsswitch.conf; then
    # Add or update sudoers line
    if grep -q "^sudoers:" /etc/nsswitch.conf; then
        sed -i 's/^sudoers:.*/sudoers: files sss/' /etc/nsswitch.conf
    else
        echo "sudoers: files sss" >> /etc/nsswitch.conf
    fi
fi

echo "✅ nsswitch.conf updated for sudoers"

# -----------------------------------------------------------------------------
# Configure sudo to use SSSD
# -----------------------------------------------------------------------------
echo "[3/4] Configuring sudo..."

# Create a sudoers.d file for LDAP configuration
cat > /etc/sudoers.d/heracles-ldap << 'EOF'
# =============================================================================
# Heracles LDAP Sudo Configuration
# =============================================================================
# This file configures sudo to fetch rules from LDAP via SSSD.
# Rules are stored as sudoRole objects under ou=sudoers,dc=heracles,dc=local
#
# sudoRole attributes:
#   - cn: Rule name
#   - sudoUser: Users/groups (prefix % for groups, + for netgroups)
#   - sudoHost: Hosts (ALL or specific hostnames)
#   - sudoCommand: Commands (with optional NOPASSWD:, NOEXEC:, etc.)
#   - sudoRunAsUser: Run as user (defaults to root)
#   - sudoRunAsGroup: Run as group
#   - sudoOption: Options like !authenticate, env_keep, etc.
#   - sudoOrder: Priority (lower = higher priority)
#
# Example rule in LDAP:
#   dn: cn=admins,ou=sudoers,dc=heracles,dc=local
#   objectClass: sudoRole
#   cn: admins
#   sudoUser: %heraclesadmins
#   sudoHost: ALL
#   sudoCommand: ALL
#   sudoOption: !authenticate
#   sudoOrder: 1
# =============================================================================

# Default settings
Defaults    env_reset
Defaults    mail_badpass
Defaults    secure_path="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Log sudo commands
Defaults    logfile="/var/log/sudo.log"
Defaults    log_input, log_output

# Root always has sudo access (local fallback)
root    ALL=(ALL:ALL) ALL

# Allow members of sudo group to execute any command (local fallback)
%sudo   ALL=(ALL:ALL) ALL

# LDAP sudo rules are fetched via SSSD automatically
# Check /etc/nsswitch.conf for "sudoers: files sss"
EOF

chmod 440 /etc/sudoers.d/heracles-ldap

# Validate sudoers configuration
if visudo -c; then
    echo "✅ Sudoers configuration is valid"
else
    echo "❌ Sudoers configuration has errors"
    rm -f /etc/sudoers.d/heracles-ldap
    exit 1
fi

# -----------------------------------------------------------------------------
# Configure SSSD for sudo
# -----------------------------------------------------------------------------
echo "[4/4] Verifying SSSD sudo configuration..."

# Check if SSSD is configured for sudo
if grep -q "sudo" /etc/sssd/sssd.conf 2>/dev/null; then
    echo "✅ SSSD is configured for sudo"
else
    echo "⚠️  SSSD may not be configured for sudo"
    echo "    Ensure 'sudo' is in the services line in /etc/sssd/sssd.conf"
fi

# Clear SSSD sudo cache to pick up new rules
sss_cache -s 2>/dev/null || true

# Restart SSSD to apply changes
systemctl restart sssd

# -----------------------------------------------------------------------------
# Create test script for sudo rules
# -----------------------------------------------------------------------------
cat > /usr/local/bin/test-sudo-ldap.sh << 'EOF'
#!/bin/bash
# =============================================================================
# Test script to verify sudo LDAP rules
# =============================================================================

echo "=============================================="
echo "  Sudo LDAP Rules Test"
echo "=============================================="
echo ""

# Show current user
echo "Current user: $(whoami)"
echo "Hostname: $(hostname -s)"
echo ""

# List sudo rules for current user
echo "Sudo privileges for $(whoami):"
echo "--------------------------------"
sudo -l 2>&1 || echo "(No sudo rules found or sudo not allowed)"
echo ""

# Test SSSD sudo cache
echo "SSSD sudo cache status:"
echo "--------------------------------"
sssctl domain-status heracles.local 2>/dev/null || echo "(sssctl not available)"
echo ""

# Search LDAP for sudo rules (requires ldap-utils)
HOSTNAME=$(hostname -s)
echo "Sudo rules in LDAP matching this host (${HOSTNAME}):"
echo "--------------------------------"
if command -v ldapsearch &> /dev/null; then
    ldapsearch -x \
        -H "ldap://$(grep LDAP_HOST /etc/ssh/ldap-ssh-keys.conf 2>/dev/null | cut -d'=' -f2 | tr -d '"' || echo '192.168.56.1')" \
        -D "cn=admin,dc=heracles,dc=local" \
        -w "admin_secret" \
        -b "ou=sudoers,dc=heracles,dc=local" \
        -LLL \
        "(|(sudoHost=ALL)(sudoHost=${HOSTNAME}))" \
        cn sudoUser sudoHost sudoCommand sudoOption 2>/dev/null || \
        echo "(LDAP search failed)"
else
    echo "(ldapsearch not installed)"
fi
echo ""
EOF

chmod 755 /usr/local/bin/test-sudo-ldap.sh

# -----------------------------------------------------------------------------
# Verification
# -----------------------------------------------------------------------------
echo ""
echo "=============================================="
echo "  Sudo LDAP Setup Complete!"
echo "=============================================="
echo ""
echo "SSSD is configured to fetch sudo rules from LDAP."
echo ""
echo "To create a sudo rule in Heracles:"
echo ""
echo "  1. Go to Heracles UI > Sudo > Create Rule"
echo ""
echo "  2. Configure the rule:"
echo "     - Name: admins"
echo "     - Users: %heraclesadmins (% prefix for groups)"
echo "     - Hosts: ALL or ${HOSTNAME}"
echo "     - Commands: ALL"
echo "     - Options: NOPASSWD (optional)"
echo ""
echo "  3. Test sudo on this VM:"
echo "     ssh user@$(hostname -I | awk '{print $2}')"
echo "     sudo whoami"
echo ""
echo "To verify sudo rules:"
echo "  /usr/local/bin/test-sudo-ldap.sh"
echo ""
echo "To debug SSSD sudo:"
echo "  sudo sssctl domain-status heracles.local"
echo "  sudo sss_cache -E  # Clear all caches"
echo "  journalctl -u sssd -f"
echo ""
