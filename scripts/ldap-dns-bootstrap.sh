#!/bin/bash
# =============================================================================
# Heracles DNS Bootstrap Script
# =============================================================================
# This script populates the LDAP directory with DNS zone data for the
# heracles.local domain and reverse DNS zone. The zones are stored using
# the dNSZone objectClass and can be served by BIND9 with DLZ LDAP backend.
#
# Zones created:
#   - heracles.local (forward zone)
#   - 56.168.192.in-addr.arpa (reverse zone for 192.168.56.0/24)
#
# Usage: ./scripts/ldap-dns-bootstrap.sh
# =============================================================================

set -e

LDAP_HOST="${LDAP_HOST:-localhost}"
LDAP_PORT="${LDAP_PORT:-389}"
LDAP_ADMIN_DN="${LDAP_ADMIN_DN:-cn=admin,dc=heracles,dc=local}"
LDAP_ADMIN_PASSWORD="${LDAP_ADMIN_PASSWORD:-admin_secret}"
LDAP_BASE_DN="${LDAP_BASE_DN:-dc=heracles,dc=local}"

# DNS configuration
DNS_ZONE="heracles.local"
DNS_REVERSE_ZONE="56.168.192.in-addr.arpa"
DNS_TTL="86400"
DNS_ADMIN="admin.heracles.local."
DNS_NS="ns1.heracles.local."
DNS_SERIAL=$(date +%Y%m%d)01

echo "========================================"
echo "  Heracles DNS Bootstrap"
echo "========================================"
echo "Host: $LDAP_HOST:$LDAP_PORT"
echo "Base DN: $LDAP_BASE_DN"
echo "Zone: $DNS_ZONE"
echo "Reverse Zone: $DNS_REVERSE_ZONE"
echo ""

# Wait for LDAP to be ready
echo "[*] Waiting for LDAP server..."
for i in {1..30}; do
    if ldapsearch -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -b "$LDAP_BASE_DN" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" "(ou=dns)" dn > /dev/null 2>&1; then
        echo "[+] LDAP server is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "[-] LDAP server failed to respond"
        exit 1
    fi
    sleep 1
done

# Check if ou=dns exists
if ! ldapsearch -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -b "$LDAP_BASE_DN" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" "(ou=dns)" dn 2>/dev/null | grep -q "ou=dns"; then
    echo "[-] ou=dns not found. Run 'make bootstrap' first."
    exit 1
fi

# Check if zone already exists
existing=$(ldapsearch -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -b "ou=dns,$LDAP_BASE_DN" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" "(zoneName=$DNS_ZONE)" dn 2>/dev/null | grep "numEntries" | awk '{print $3}')

if [ "$existing" != "" ] && [ "$existing" -gt 0 ]; then
    echo "[i] DNS zone '$DNS_ZONE' already exists in LDAP"
    echo "    Skipping bootstrap..."
    echo ""
    echo "Existing DNS entries:"
    ldapsearch -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -b "ou=dns,$LDAP_BASE_DN" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" "(objectClass=dNSZone)" dn relativeDomainName | grep -E "^(dn:|relativeDomainName:)"
    exit 0
fi

# Helper function to add DNS record
add_dns_record() {
    local zone="$1"
    local name="$2"
    local ttl="$3"
    shift 3
    # Remaining args are attribute pairs: type value type value ...
    
    echo "    Adding $name.$zone..."
    
    # Build the LDIF - records are children of the zone container
    local ldif="dn: relativeDomainName=$name,zoneName=$zone,ou=dns,$LDAP_BASE_DN
objectClass: dNSZone
zoneName: $zone
relativeDomainName: $name
dNSTTL: $ttl"
    
    # Add record attributes
    while [ $# -ge 2 ]; do
        ldif="$ldif
$1: $2"
        shift 2
    done
    
    echo "$ldif" | ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" 2>/dev/null || {
        echo "      [!] Failed to add $name.$zone"
        return 1
    }
}

echo ""
echo "[*] Creating forward DNS zone: $DNS_ZONE"
echo "========================================"

# Create the zone apex entry with SOA and NS records
# FusionDirectory compatible structure:
#   - Zone entry at zoneName=X,ou=dns,... with relativeDomainName=@ as attribute
#   - Child records at relativeDomainName=Y,zoneName=X,ou=dns,...
echo "    Creating zone: zoneName=$DNS_ZONE (FusionDirectory compatible)..."
ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" << EOF
dn: zoneName=$DNS_ZONE,ou=dns,$LDAP_BASE_DN
objectClass: dNSZone
zoneName: $DNS_ZONE
relativeDomainName: @
dNSTTL: $DNS_TTL
dNSClass: IN
sOARecord: $DNS_NS $DNS_ADMIN $DNS_SERIAL 3600 1800 604800 86400
nSRecord: $DNS_NS
EOF

# A records for infrastructure
add_dns_record "$DNS_ZONE" "ns1" "$DNS_TTL" "aRecord" "192.168.56.20"
add_dns_record "$DNS_ZONE" "ldap" "$DNS_TTL" "aRecord" "192.168.56.1"
add_dns_record "$DNS_ZONE" "server1" "$DNS_TTL" "aRecord" "192.168.56.10"
add_dns_record "$DNS_ZONE" "workstation1" "$DNS_TTL" "aRecord" "192.168.56.11"

# CNAME aliases
add_dns_record "$DNS_ZONE" "dns" "$DNS_TTL" "cNAMERecord" "ns1.$DNS_ZONE."
add_dns_record "$DNS_ZONE" "api" "$DNS_TTL" "cNAMERecord" "ldap.$DNS_ZONE."
add_dns_record "$DNS_ZONE" "ui" "$DNS_TTL" "cNAMERecord" "ldap.$DNS_ZONE."

# MX record for mail (pointing to ldap for demo)
echo "    Adding mail.$DNS_ZONE..."
ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" << EOF
dn: relativeDomainName=mail,zoneName=$DNS_ZONE,ou=dns,$LDAP_BASE_DN
objectClass: dNSZone
zoneName: $DNS_ZONE
relativeDomainName: mail
dNSTTL: $DNS_TTL
aRecord: 192.168.56.1
EOF

# Update zone apex with MX record
echo "    Updating zone apex with MX record..."
ldapmodify -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" << EOF
dn: zoneName=$DNS_ZONE,ou=dns,$LDAP_BASE_DN
changetype: modify
add: mXRecord
mXRecord: 10 mail.$DNS_ZONE.
EOF

echo ""
echo "[*] Creating reverse DNS zone: $DNS_REVERSE_ZONE"
echo "========================================"

# Create the reverse zone apex entry with SOA and NS records
# FusionDirectory compatible: nested under forward zone or standalone
echo "    Creating zone: zoneName=$DNS_REVERSE_ZONE (FusionDirectory compatible)..."
ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" << EOF
dn: zoneName=$DNS_REVERSE_ZONE,ou=dns,$LDAP_BASE_DN
objectClass: dNSZone
zoneName: $DNS_REVERSE_ZONE
relativeDomainName: @
dNSTTL: $DNS_TTL
dNSClass: IN
sOARecord: $DNS_NS $DNS_ADMIN $DNS_SERIAL 3600 1800 604800 86400
nSRecord: $DNS_NS
EOF

# PTR records
add_dns_record "$DNS_REVERSE_ZONE" "1" "$DNS_TTL" "pTRRecord" "ldap.$DNS_ZONE."
add_dns_record "$DNS_REVERSE_ZONE" "10" "$DNS_TTL" "pTRRecord" "server1.$DNS_ZONE."
add_dns_record "$DNS_REVERSE_ZONE" "11" "$DNS_TTL" "pTRRecord" "workstation1.$DNS_ZONE."
add_dns_record "$DNS_REVERSE_ZONE" "20" "$DNS_TTL" "pTRRecord" "ns1.$DNS_ZONE."

echo ""
echo "========================================"
echo "  DNS Bootstrap Complete!"
echo "========================================"
echo ""
echo "Zones created:"
echo "  - $DNS_ZONE (forward)"
echo "  - $DNS_REVERSE_ZONE (reverse)"
echo ""
echo "Records:"
ldapsearch -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -b "ou=dns,$LDAP_BASE_DN" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" "(objectClass=dNSZone)" dn relativeDomainName zoneName 2>/dev/null | grep -E "^(dn:|relativeDomainName:|zoneName:)" | head -40
echo ""
echo "Next steps:"
echo "  1. Start the ns1 VM: cd demo && vagrant up ns1"
echo "  2. Test DNS: dig @192.168.56.20 server1.heracles.local"
echo "  3. Test reverse: dig @192.168.56.20 -x 192.168.56.10"
echo ""
