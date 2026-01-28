#!/bin/bash
# =============================================================================
# Heracles DHCP Bootstrap Script
# =============================================================================
# This script populates the LDAP directory with DHCP configuration for the
# heracles.local domain. The configuration is stored using the dhcpService,
# dhcpSubnet, dhcpPool, dhcpHost, and dhcpDnsZone objectClasses and can be
# served by ISC DHCP server with LDAP backend.
#
# Structure created:
#   ou=dhcp,dc=heracles,dc=local
#   └── cn=demo-dhcp-service (dhcpService)
#       ├── cn=192.168.56.0 (dhcpSubnet)
#       │   ├── cn=dynamic-pool (dhcpPool)
#       │   ├── cn=server1 (dhcpHost) - fixed address
#       │   ├── cn=workstation1 (dhcpHost) - fixed address
#       │   ├── cn=ns1 (dhcpHost) - fixed address
#       │   └── cn=dhcp1 (dhcpHost) - fixed address
#       └── cn=heracles.local (dhcpDnsZone) - for DDNS
#
# Usage: ./scripts/ldap-dhcp-bootstrap.sh
# =============================================================================

set -e

LDAP_HOST="${LDAP_HOST:-localhost}"
LDAP_PORT="${LDAP_PORT:-389}"
LDAP_ADMIN_DN="${LDAP_ADMIN_DN:-cn=admin,dc=heracles,dc=local}"
LDAP_ADMIN_PASSWORD="${LDAP_ADMIN_PASSWORD:-admin_secret}"
LDAP_BASE_DN="${LDAP_BASE_DN:-dc=heracles,dc=local}"

# DHCP configuration
DHCP_OU="ou=dhcp,${LDAP_BASE_DN}"
DHCP_SERVICE_CN="demo-dhcp-service"
DHCP_SUBNET="192.168.56.0"
DHCP_NETMASK="24"
DHCP_ROUTER="192.168.56.1"
DHCP_DNS="192.168.56.20"
DHCP_DOMAIN="heracles.local"
DHCP_RANGE_START="192.168.56.100"
DHCP_RANGE_END="192.168.56.199"
DHCP_LEASE_TIME="3600"

echo "========================================"
echo "  Heracles DHCP Bootstrap"
echo "========================================"
echo "Host: $LDAP_HOST:$LDAP_PORT"
echo "Base DN: $LDAP_BASE_DN"
echo "DHCP OU: $DHCP_OU"
echo "Subnet: $DHCP_SUBNET/$DHCP_NETMASK"
echo "Pool: $DHCP_RANGE_START - $DHCP_RANGE_END"
echo ""

# Wait for LDAP to be ready
echo "[*] Waiting for LDAP server..."
for i in {1..30}; do
    if ldapsearch -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -b "$LDAP_BASE_DN" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" "(objectClass=organization)" dn > /dev/null 2>&1; then
        echo "[+] LDAP server is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "[-] LDAP server failed to respond"
        exit 1
    fi
    sleep 1
done

# Check if ou=dhcp already exists
dhcp_ou_exists=$(ldapsearch -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -b "$LDAP_BASE_DN" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" "(ou=dhcp)" dn 2>/dev/null | grep -c "numEntries" || echo "0")

if ! ldapsearch -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -b "$LDAP_BASE_DN" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" "(ou=dhcp)" dn 2>/dev/null | grep -q "ou=dhcp"; then
    echo "[*] Creating ou=dhcp organizational unit..."
    ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" << EOF
dn: ou=dhcp,${LDAP_BASE_DN}
objectClass: organizationalUnit
ou: dhcp
description: DHCP Configuration
EOF
    echo "[+] ou=dhcp created"
else
    echo "[i] ou=dhcp already exists"
fi

# Check if DHCP service already exists
existing=$(ldapsearch -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -b "$DHCP_OU" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" "(cn=${DHCP_SERVICE_CN})" dn 2>/dev/null | grep -c "^dn:") || existing=0

if [ "$existing" -gt 0 ]; then
    echo "[i] DHCP service '${DHCP_SERVICE_CN}' already exists in LDAP"
    echo "    Skipping bootstrap..."
    echo ""
    echo "Existing DHCP entries:"
    ldapsearch -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -b "$DHCP_OU" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" "(objectClass=*)" dn | grep -E "^dn:" | head -20
    exit 0
fi

echo ""
echo "[*] Creating DHCP Service: ${DHCP_SERVICE_CN}"
echo "========================================"

# Create the DHCP Service
echo "    Creating DHCP service..."
ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" << EOF
dn: cn=${DHCP_SERVICE_CN},${DHCP_OU}
objectClass: dhcpService
cn: ${DHCP_SERVICE_CN}
dhcpStatements: authoritative
dhcpStatements: ddns-update-style interim
dhcpStatements: ddns-updates on
dhcpStatements: update-static-leases on
dhcpStatements: default-lease-time ${DHCP_LEASE_TIME}
dhcpStatements: max-lease-time 7200
dhcpOption: domain-name "${DHCP_DOMAIN}"
dhcpOption: domain-name-servers ${DHCP_DNS}
dhcpComments: Heracles Demo DHCP Service
EOF

DHCP_SERVICE_DN="cn=${DHCP_SERVICE_CN},${DHCP_OU}"

echo ""
echo "[*] Creating DNS Zone for DDNS: ${DHCP_DOMAIN}"
echo "========================================"

# Create DHCP DNS Zone for dynamic DNS updates
echo "    Creating DHCP DNS Zone..."
ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" << EOF
dn: cn=${DHCP_DOMAIN},${DHCP_SERVICE_DN}
objectClass: dhcpDnsZone
cn: ${DHCP_DOMAIN}
dhcpDnsZoneServer: ${DHCP_DNS}
dhcpComments: Forward DNS zone for DDNS updates
EOF

# Create reverse DNS zone for DDNS
echo "    Creating reverse DNS Zone for DDNS..."
ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" << EOF
dn: cn=56.168.192.in-addr.arpa,${DHCP_SERVICE_DN}
objectClass: dhcpDnsZone
cn: 56.168.192.in-addr.arpa
dhcpDnsZoneServer: ${DHCP_DNS}
dhcpComments: Reverse DNS zone for DDNS updates
EOF

echo ""
echo "[*] Creating Subnet: ${DHCP_SUBNET}/${DHCP_NETMASK}"
echo "========================================"

# Create the subnet
echo "    Creating subnet ${DHCP_SUBNET}..."
ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" << EOF
dn: cn=${DHCP_SUBNET},${DHCP_SERVICE_DN}
objectClass: dhcpSubnet
cn: ${DHCP_SUBNET}
dhcpNetMask: ${DHCP_NETMASK}
dhcpStatements: option routers ${DHCP_ROUTER}
dhcpStatements: option broadcast-address 192.168.56.255
dhcpStatements: option subnet-mask 255.255.255.0
dhcpOption: routers ${DHCP_ROUTER}
dhcpOption: broadcast-address 192.168.56.255
dhcpComments: Demo subnet for Heracles environment
EOF

DHCP_SUBNET_DN="cn=${DHCP_SUBNET},${DHCP_SERVICE_DN}"

echo ""
echo "[*] Creating Dynamic Pool: ${DHCP_RANGE_START} - ${DHCP_RANGE_END}"
echo "========================================"

# Create the dynamic address pool
echo "    Creating dynamic pool..."
ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" << EOF
dn: cn=dynamic-pool,${DHCP_SUBNET_DN}
objectClass: dhcpPool
cn: dynamic-pool
dhcpRange: ${DHCP_RANGE_START} ${DHCP_RANGE_END}
dhcpPermitList: allow unknown-clients
dhcpStatements: default-lease-time ${DHCP_LEASE_TIME}
dhcpStatements: max-lease-time 7200
dhcpComments: Dynamic address pool for demo clients
EOF

echo ""
echo "[*] Creating Static Host Reservations"
echo "========================================"

# Create static host entries with placeholder MAC addresses
# These can be updated later with actual VirtualBox MACs

# Helper function to create host reservation
create_host_reservation() {
    local host="$1"
    local ip="$2"
    local mac="$3"
    
    echo "    Creating host reservation: $host -> $ip ($mac)"
    ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" << EOF
dn: cn=${host},${DHCP_SUBNET_DN}
objectClass: dhcpHost
cn: ${host}
dhcpHWAddress: ethernet ${mac}
dhcpStatements: fixed-address ${ip}
dhcpOption: host-name "${host}"
dhcpComments: Static reservation for ${host}.${DHCP_DOMAIN}
EOF
}

# Create host reservations
create_host_reservation "server1" "192.168.56.10" "08:00:27:00:00:10"
create_host_reservation "workstation1" "192.168.56.11" "08:00:27:00:00:11"
create_host_reservation "ns1" "192.168.56.20" "08:00:27:00:00:20"
create_host_reservation "dhcp1" "192.168.56.21" "08:00:27:00:00:21"

# Create a DHCP group for demo hosts
echo ""
echo "[*] Creating Host Group: demo-servers"
echo "========================================"

echo "    Creating host group..."
ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" << EOF
dn: cn=demo-servers,${DHCP_SERVICE_DN}
objectClass: dhcpGroup
cn: demo-servers
dhcpStatements: default-lease-time 86400
dhcpStatements: max-lease-time 172800
dhcpOption: domain-name "${DHCP_DOMAIN}"
dhcpComments: Group for demo server hosts with longer lease times
EOF

echo ""
echo "========================================"
echo "  DHCP Bootstrap Complete!"
echo "========================================"
echo ""
echo "DHCP Service DN: ${DHCP_SERVICE_DN}"
echo "Subnet DN: ${DHCP_SUBNET_DN}"
echo ""
echo "Configuration summary:"
echo "  - Service: ${DHCP_SERVICE_CN}"
echo "  - Subnet: ${DHCP_SUBNET}/${DHCP_NETMASK}"
echo "  - Dynamic Pool: ${DHCP_RANGE_START} - ${DHCP_RANGE_END}"
echo "  - Router: ${DHCP_ROUTER}"
echo "  - DNS Server: ${DHCP_DNS}"
echo "  - Domain: ${DHCP_DOMAIN}"
echo "  - Static Hosts: ${#STATIC_HOSTS[@]}"
echo "  - DDNS Zones: 2 (forward + reverse)"
echo ""
echo "Next steps:"
echo "  1. Start the dhcp1 VM: make demo-up"
echo "  2. The DHCP server will sync config from LDAP"
echo "  3. Test with: vagrant ssh server1 -c 'sudo dhclient -v eth1'"
echo ""
