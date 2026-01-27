#!/bin/bash
# =============================================================================
# Heracles LDAP Bootstrap Script
# =============================================================================
# This script initializes the LDAP directory with base organizational units
# and creates the admin user. Run this after docker compose up.
#
# For demo users (devuser, opsuser, etc.), use the demo setup script:
#   cd demo && ./scripts/setup-demo-users.sh

set -e

LDAP_HOST="${LDAP_HOST:-localhost}"
LDAP_PORT="${LDAP_PORT:-389}"
LDAP_ADMIN_DN="${LDAP_ADMIN_DN:-cn=admin,dc=heracles,dc=local}"
LDAP_ADMIN_PASSWORD="${LDAP_ADMIN_PASSWORD:-admin_secret}"
LDAP_BASE_DN="${LDAP_BASE_DN:-dc=heracles,dc=local}"

# Heracles admin user credentials (for API authentication)
HRC_ADMIN_USER="${HRC_ADMIN_USER:-hrc-admin}"
HRC_ADMIN_PASSWORD="${HRC_ADMIN_PASSWORD:-hrc-admin-secret}"
HRC_ADMIN_UID="${HRC_ADMIN_UID:-10000}"
HRC_ADMIN_GID="${HRC_ADMIN_GID:-10000}"

echo "========================================"
echo "  Heracles LDAP Bootstrap"
echo "========================================"
echo "Host: $LDAP_HOST:$LDAP_PORT"
echo "Base DN: $LDAP_BASE_DN"
echo ""

# Wait for LDAP to be ready
echo "[*] Waiting for LDAP server..."
for i in {1..30}; do
    if ldapsearch -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -b "$LDAP_BASE_DN" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" "(objectClass=*)" dn > /dev/null 2>&1; then
        echo "[+] LDAP server is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "[-] LDAP server failed to start"
        exit 1
    fi
    sleep 1
done

# Check if already initialized
existing=$(ldapsearch -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -b "$LDAP_BASE_DN" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" "(ou=people)" dn 2>/dev/null | grep "numEntries" | awk '{print $3}')

if [ "$existing" != "" ] && [ "$existing" -gt 0 ]; then
    echo "[i] LDAP already initialized (found ou=people)"
    echo "    Skipping bootstrap..."
    exit 0
fi

echo ""
echo "[*] Creating base organizational units..."

# Create OUs one by one
create_ou() {
    local ou_name="$1"
    local description="$2"
    echo "    Creating ou=$ou_name..."
    ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" <<EOF
dn: ou=$ou_name,$LDAP_BASE_DN
objectClass: organizationalUnit
ou: $ou_name
description: $description
EOF
}

create_ou "people" "Container for user accounts"
create_ou "groups" "Container for groups"
create_ou "systems" "Container for system entries"
create_ou "aclroles" "Container for ACL roles"
create_ou "sudoers" "Container for sudo rules"
create_ou "dns" "Container for DNS zones"
create_ou "dhcp" "Container for DHCP configuration"
create_ou "heracles" "Heracles configuration"

echo ""
echo "[*] Creating systems sub-organizational units..."

# Create systems sub-OUs
create_systems_sub_ou() {
    local ou_name="$1"
    local description="$2"
    echo "    Creating ou=$ou_name,ou=systems..."
    ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" <<EOF
dn: ou=$ou_name,ou=systems,$LDAP_BASE_DN
objectClass: organizationalUnit
ou: $ou_name
description: $description
EOF
}

create_systems_sub_ou "servers" "Container for servers"
create_systems_sub_ou "workstations" "Container for workstations"
create_systems_sub_ou "terminals" "Container for terminals"
create_systems_sub_ou "printers" "Container for printers"
create_systems_sub_ou "components" "Container for network components"
create_systems_sub_ou "phones" "Container for phones"
create_systems_sub_ou "mobile" "Container for mobile phones"

echo ""
echo "[*] Creating Heracles admin user (hrc-admin)..."
# Generate SSHA password hash using slappasswd inside the LDAP container
HRC_ADMIN_HASH=$(docker exec heracles-ldap slappasswd -s "$HRC_ADMIN_PASSWORD" 2>/dev/null || echo "{SSHA}placeholder")
ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" <<EOF
dn: uid=$HRC_ADMIN_USER,ou=people,$LDAP_BASE_DN
objectClass: inetOrgPerson
objectClass: organizationalPerson
objectClass: person
objectClass: posixAccount
objectClass: shadowAccount
cn: Heracles Administrator
sn: Administrator
givenName: Heracles
uid: $HRC_ADMIN_USER
mail: admin@heracles.local
uidNumber: $HRC_ADMIN_UID
gidNumber: $HRC_ADMIN_GID
homeDirectory: /home/$HRC_ADMIN_USER
loginShell: /bin/bash
userPassword: $HRC_ADMIN_HASH
shadowLastChange: 19750
shadowMax: 99999
shadowWarning: 7
EOF

echo ""
echo "[*] Creating Heracles admins group..."
ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" <<EOF
dn: cn=heraclesadmins,ou=groups,$LDAP_BASE_DN
objectClass: posixGroup
cn: heraclesadmins
description: Heracles administrators with full access
gidNumber: $HRC_ADMIN_GID
memberUid: $HRC_ADMIN_USER
EOF

echo ""
echo "========================================"
echo "  LDAP Bootstrap Complete!"
echo "========================================"
echo ""
echo "Admin user created:"
echo "  - hrc-admin (password: hrc-admin-secret)"
echo ""
echo "To set up demo users with SSH keys and sudo rules, run:"
echo "  cd demo && ./scripts/setup-demo-users.sh"
echo ""
echo "Current LDAP structure:"
ldapsearch -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -b "$LDAP_BASE_DN" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" "(objectClass=*)" dn | grep "^dn:"
