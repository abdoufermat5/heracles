#!/bin/bash
# =============================================================================
# Heracles LDAP Bootstrap Script
# =============================================================================
# This script initializes the LDAP directory with base organizational units
# Run this after docker compose up when starting with fresh volumes

set -e

LDAP_HOST="${LDAP_HOST:-localhost}"
LDAP_PORT="${LDAP_PORT:-389}"
LDAP_ADMIN_DN="${LDAP_ADMIN_DN:-cn=admin,dc=heracles,dc=local}"
LDAP_ADMIN_PASSWORD="${LDAP_ADMIN_PASSWORD:-admin_secret}"
LDAP_BASE_DN="${LDAP_BASE_DN:-dc=heracles,dc=local}"

echo "🚀 Heracles LDAP Bootstrap"
echo "=========================="
echo "Host: $LDAP_HOST:$LDAP_PORT"
echo "Base DN: $LDAP_BASE_DN"
echo ""

# Wait for LDAP to be ready
echo "⏳ Waiting for LDAP server..."
for i in {1..30}; do
    if ldapsearch -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -b "$LDAP_BASE_DN" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" "(objectClass=*)" dn > /dev/null 2>&1; then
        echo "✅ LDAP server is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ LDAP server failed to start"
        exit 1
    fi
    sleep 1
done

# Check if already initialized
existing=$(ldapsearch -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -b "$LDAP_BASE_DN" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" "(ou=people)" dn 2>/dev/null | grep "numEntries" | awk '{print $3}')

if [ "$existing" != "" ] && [ "$existing" -gt 0 ]; then
    echo "ℹ️  LDAP already initialized (found ou=people)"
    echo "   Skipping bootstrap..."
    exit 0
fi

echo ""
echo "📦 Creating base organizational units..."

# Create OUs one by one
create_ou() {
    local ou_name="$1"
    local description="$2"
    echo "  Creating ou=$ou_name..."
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
create_ou "fusiondirectory" "FusionDirectory configuration"

echo ""
echo "📦 Creating systems sub-organizational units..."

# Create systems sub-OUs
create_systems_sub_ou() {
    local ou_name="$1"
    local description="$2"
    echo "  Creating ou=$ou_name,ou=systems..."
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
echo "👤 Creating test user..."
ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" <<EOF
dn: uid=testuser,ou=people,$LDAP_BASE_DN
objectClass: inetOrgPerson
objectClass: organizationalPerson
objectClass: person
cn: Test User
sn: User
givenName: Test
uid: testuser
mail: testuser@heracles.local
userPassword: {SSHA}test_password_will_be_hashed
EOF

echo ""
echo "👥 Creating default admin group..."
ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" <<EOF
dn: cn=admins,ou=groups,$LDAP_BASE_DN
objectClass: groupOfNames
cn: admins
description: Heracles administrators
member: uid=testuser,ou=people,$LDAP_BASE_DN
EOF

echo ""
echo "✅ LDAP bootstrap complete!"
echo ""
echo "📊 Current LDAP structure:"
ldapsearch -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -b "$LDAP_BASE_DN" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" "(objectClass=*)" dn | grep "^dn:"
