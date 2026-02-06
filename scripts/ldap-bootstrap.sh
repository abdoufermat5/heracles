#!/bin/bash
# =============================================================================
# Heracles LDAP Bootstrap Script
# =============================================================================
# Unified script for all LDAP initialization tasks.
#
# Usage: ./scripts/ldap-bootstrap.sh [command]
#
# Commands:
#   init      Initialize LDAP with base OUs and admin user (default)
#   schemas   Load custom LDAP schemas
#   dns       Bootstrap DNS zones
#   dhcp      Bootstrap DHCP configuration
#   all       Run all bootstrap steps
#   help      Show this help
# =============================================================================

set -e

# Configuration
LDAP_HOST="${LDAP_HOST:-localhost}"
LDAP_PORT="${LDAP_PORT:-389}"
LDAP_ADMIN_DN="${LDAP_ADMIN_DN:-cn=admin,dc=heracles,dc=local}"
LDAP_ADMIN_PASSWORD="${LDAP_ADMIN_PASSWORD:-admin_secret}"
LDAP_BASE_DN="${LDAP_BASE_DN:-dc=heracles,dc=local}"
LDAP_CONTAINER="${LDAP_CONTAINER:-heracles-ldap}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
# Schema directories:
#   - Core schemas: docker/ldap/schemas/core/
#   - Plugin schemas: heracles_plugins/heracles_plugins/*/ldap/
#   - Compat symlinks: docker/ldap/schemas/ (symlinks to plugin schemas)
CORE_SCHEMAS_DIR="$PROJECT_ROOT/docker/ldap/schemas/core"
PLUGINS_DIR="$PROJECT_ROOT/heracles_plugins/heracles_plugins"
COMPAT_SCHEMAS_DIR="$PROJECT_ROOT/docker/ldap/schemas"

# Heracles admin user
HRC_ADMIN_USER="${HRC_ADMIN_USER:-hrc-admin}"
HRC_ADMIN_PASSWORD="${HRC_ADMIN_PASSWORD:-hrc-admin-secret}"
HRC_ADMIN_UID="${HRC_ADMIN_UID:-10000}"
HRC_ADMIN_GID="${HRC_ADMIN_GID:-10000}"

# =============================================================================
# Helper Functions
# =============================================================================

wait_for_ldap() {
    echo "[*] Waiting for LDAP server..."
    for i in {1..30}; do
        if ldapsearch -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -b "$LDAP_BASE_DN" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" "(objectClass=*)" dn > /dev/null 2>&1; then
            echo "[+] LDAP server is ready"
            return 0
        fi
        sleep 1
    done
    echo "[-] LDAP server failed to start"
    exit 1
}

# =============================================================================
# INIT: Base OUs and Admin User
# =============================================================================

cmd_init() {
    echo "========================================"
    echo "  LDAP Init: Base Structure"
    echo "========================================"
    wait_for_ldap

    # Check if already initialized
    if ldapsearch -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -b "$LDAP_BASE_DN" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" "(ou=people)" dn 2>/dev/null | grep -q "dn: ou=people"; then
        echo "[i] Already initialized. Skipping."
        return 0
    fi

    echo "[*] Creating organizational units..."
    for ou in people groups roles systems aclroles sudoers dns dhcp; do
        ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" <<EOF
dn: ou=$ou,$LDAP_BASE_DN
objectClass: organizationalUnit
ou: $ou
EOF
    done

    echo "[*] Creating systems sub-OUs..."
    for sub_ou in servers workstations terminals printers components phones mobile; do
        ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" <<EOF
dn: ou=$sub_ou,ou=systems,$LDAP_BASE_DN
objectClass: organizationalUnit
ou: $sub_ou
EOF
    done

    echo "[*] Creating admin user..."
    HRC_ADMIN_HASH=$(docker exec "$LDAP_CONTAINER" slappasswd -s "$HRC_ADMIN_PASSWORD" 2>/dev/null || echo "{SSHA}placeholder")
    ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" <<EOF
dn: uid=$HRC_ADMIN_USER,ou=people,$LDAP_BASE_DN
objectClass: inetOrgPerson
objectClass: posixAccount
objectClass: shadowAccount
cn: Heracles Administrator
sn: Administrator
uid: $HRC_ADMIN_USER
mail: admin@heracles.local
uidNumber: $HRC_ADMIN_UID
gidNumber: $HRC_ADMIN_GID
homeDirectory: /home/$HRC_ADMIN_USER
loginShell: /bin/bash
userPassword: $HRC_ADMIN_HASH
EOF

    echo "[*] Creating admins group..."
    ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" <<EOF
dn: cn=heraclesadmins,ou=groups,$LDAP_BASE_DN
objectClass: posixGroup
cn: heraclesadmins
gidNumber: $HRC_ADMIN_GID
memberUid: $HRC_ADMIN_USER
EOF

    echo "[+] LDAP init complete!"
}

# =============================================================================
# SCHEMAS: Load Custom Schemas
# =============================================================================
# Schema loading order:
#   1. Core configuration schemas (docker/ldap/schemas/core/)
#   2. Plugin schemas (heracles_plugins/heracles_plugins/*/ldap/)
#   3. Compat schemas (docker/ldap/schemas/ - non-plugin schemas only)
#
# Note: docker/ldap/schemas/ contains symlinks to plugin schemas for backward
# compatibility. These are skipped since plugins are loaded directly.
# =============================================================================

load_schema() {
    local ldif="$1"
    local schema_name=$(basename "$ldif" .ldif)
    
    if docker exec "$LDAP_CONTAINER" ldapsearch -Y EXTERNAL -H ldapi:/// -b "cn=schema,cn=config" "(cn=*${schema_name}*)" cn 2>/dev/null | grep -q "cn: {[0-9]*}${schema_name}"; then
        echo "[i] Schema $schema_name already loaded"
        return 0
    fi
    
    echo "[*] Loading $schema_name..."
    docker cp "$ldif" "$LDAP_CONTAINER:/tmp/${schema_name}.ldif"
    docker exec "$LDAP_CONTAINER" ldapadd -Y EXTERNAL -H ldapi:/// -f "/tmp/${schema_name}.ldif" 2>&1 || true
    docker exec "$LDAP_CONTAINER" rm -f "/tmp/${schema_name}.ldif"
}

cmd_schemas() {
    echo "========================================"
    echo "  LDAP Schemas (Auto-Discovery)"
    echo "========================================"

    if ! docker ps --format '{{.Names}}' | grep -q "^${LDAP_CONTAINER}$"; then
        echo "[-] Container $LDAP_CONTAINER not running"
        exit 1
    fi

    # 1. Load core configuration schemas
    echo ""
    echo "[*] Loading core schemas from: $CORE_SCHEMAS_DIR"
    if [ -d "$CORE_SCHEMAS_DIR" ]; then
        for ldif in "$CORE_SCHEMAS_DIR"/*.ldif; do
            [ -f "$ldif" ] || continue
            load_schema "$ldif"
        done
    else
        echo "[i] No core schemas directory found"
    fi

    # 2. Auto-discover and load plugin schemas
    echo ""
    echo "[*] Discovering plugin schemas from: $PLUGINS_DIR"
    for plugin_dir in "$PLUGINS_DIR"/*/; do
        plugin_name=$(basename "$plugin_dir")
        ldap_dir="$plugin_dir/ldap"
        
        if [ -d "$ldap_dir" ]; then
            echo "[*] Plugin: $plugin_name"
            for ldif in "$ldap_dir"/*.ldif; do
                [ -f "$ldif" ] || continue
                load_schema "$ldif"
            done
        fi
    done

    # 3. Load non-plugin schemas from compat directory (skip symlinks)
    echo ""
    echo "[*] Loading additional schemas from: $COMPAT_SCHEMAS_DIR"
    for ldif in "$COMPAT_SCHEMAS_DIR"/*.ldif; do
        [ -f "$ldif" ] || continue
        # Skip symlinks (they point to plugin schemas already loaded)
        [ -L "$ldif" ] && continue
        load_schema "$ldif"
    done
    
    echo ""
    echo "[+] Schemas loaded!"
}

# =============================================================================
# DNS: Bootstrap DNS Zones
# =============================================================================

cmd_dns() {
    echo "========================================"
    echo "  LDAP DNS Bootstrap"
    echo "========================================"
    wait_for_ldap

    DNS_ZONE="heracles.local"
    DNS_REVERSE="56.168.192.in-addr.arpa"
    DNS_TTL="86400"
    DNS_NS="ns1.heracles.local."
    DNS_ADMIN="admin.heracles.local."
    DNS_SERIAL=$(date +%Y%m%d)01

    # Check if already exists
    if ldapsearch -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -b "ou=dns,$LDAP_BASE_DN" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" "(zoneName=$DNS_ZONE)" dn 2>/dev/null | grep -q "^dn: zoneName="; then
        echo "[i] DNS zone already exists. Skipping."
        return 0
    fi

    echo "[*] Creating forward zone: $DNS_ZONE"
    ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" <<EOF
dn: zoneName=$DNS_ZONE,ou=dns,$LDAP_BASE_DN
objectClass: dNSZone
zoneName: $DNS_ZONE
relativeDomainName: @
dNSTTL: $DNS_TTL
sOARecord: $DNS_NS $DNS_ADMIN $DNS_SERIAL 3600 1800 604800 86400
nSRecord: $DNS_NS
EOF

    # Add A records
    for record in "ns1:192.168.56.20" "dhcp1:192.168.56.21" "ldap:192.168.56.1" "server1:192.168.56.10" "workstation1:192.168.56.11" "api:192.168.56.1" "ui:192.168.56.1"; do
        name="${record%%:*}"
        ip="${record##*:}"
        ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" <<EOF
dn: relativeDomainName=$name,zoneName=$DNS_ZONE,ou=dns,$LDAP_BASE_DN
objectClass: dNSZone
zoneName: $DNS_ZONE
relativeDomainName: $name
dNSTTL: $DNS_TTL
aRecord: $ip
EOF
    done

    echo "[*] Creating reverse zone: $DNS_REVERSE"
    ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" <<EOF
dn: zoneName=$DNS_REVERSE,ou=dns,$LDAP_BASE_DN
objectClass: dNSZone
zoneName: $DNS_REVERSE
relativeDomainName: @
dNSTTL: $DNS_TTL
sOARecord: $DNS_NS $DNS_ADMIN $DNS_SERIAL 3600 1800 604800 86400
nSRecord: $DNS_NS
EOF

    # Add PTR records
    for record in "1:ldap" "10:server1" "11:workstation1" "20:ns1"; do
        num="${record%%:*}"
        host="${record##*:}"
        ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" <<EOF
dn: relativeDomainName=$num,zoneName=$DNS_REVERSE,ou=dns,$LDAP_BASE_DN
objectClass: dNSZone
zoneName: $DNS_REVERSE
relativeDomainName: $num
dNSTTL: $DNS_TTL
pTRRecord: $host.$DNS_ZONE.
EOF
    done

    echo "[+] DNS bootstrap complete!"
}

# =============================================================================
# DHCP: Bootstrap DHCP Configuration
# =============================================================================

cmd_dhcp() {
    echo "========================================"
    echo "  LDAP DHCP Bootstrap"
    echo "========================================"
    wait_for_ldap

    DHCP_OU="ou=dhcp,${LDAP_BASE_DN}"
    DHCP_SERVICE="demo-dhcp-service"
    DHCP_SUBNET="192.168.56.0"

    # Check if already exists
    if ldapsearch -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -b "$DHCP_OU" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" "(cn=$DHCP_SERVICE)" dn 2>/dev/null | grep -q "^dn: cn="; then
        echo "[i] DHCP service already exists. Skipping."
        return 0
    fi

    echo "[*] Creating DHCP service..."
    ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" <<EOF
dn: cn=$DHCP_SERVICE,$DHCP_OU
objectClass: dhcpService
cn: $DHCP_SERVICE
dhcpStatements: authoritative
dhcpStatements: default-lease-time 3600
dhcpOption: domain-name "heracles.local"
dhcpOption: domain-name-servers 192.168.56.20
EOF

    echo "[*] Creating subnet..."
    ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" <<EOF
dn: cn=$DHCP_SUBNET,cn=$DHCP_SERVICE,$DHCP_OU
objectClass: dhcpSubnet
cn: $DHCP_SUBNET
dhcpNetMask: 24
dhcpOption: routers 192.168.56.1
EOF

    echo "[*] Creating dynamic pool..."
    ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" <<EOF
dn: cn=dynamic-pool,cn=$DHCP_SUBNET,cn=$DHCP_SERVICE,$DHCP_OU
objectClass: dhcpPool
cn: dynamic-pool
dhcpRange: 192.168.56.100 192.168.56.199
EOF

    echo "[*] Creating host reservations..."
    for host in "server1:192.168.56.10:08:00:27:00:00:10" "workstation1:192.168.56.11:08:00:27:00:00:11" "ns1:192.168.56.20:08:00:27:00:00:20" "dhcp1:192.168.56.21:08:00:27:00:00:21" "mail1:192.168.56.22:08:00:27:00:00:22"; do
        IFS=':' read -r name ip mac <<< "$host"
        ldapadd -x -H "ldap://${LDAP_HOST}:${LDAP_PORT}" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" <<EOF
dn: cn=$name,cn=$DHCP_SUBNET,cn=$DHCP_SERVICE,$DHCP_OU
objectClass: dhcpHost
cn: $name
dhcpHWAddress: ethernet $mac
dhcpStatements: fixed-address $ip
EOF
    done

    echo "[+] DHCP bootstrap complete!"
}

# =============================================================================
# ALL: Run Everything
# =============================================================================

cmd_all() {
    cmd_init
    echo ""
    cmd_schemas
    echo ""
    cmd_dns
    echo ""
    cmd_dhcp
}

# =============================================================================
# HELP
# =============================================================================

cmd_help() {
    echo "Heracles LDAP Bootstrap"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  init      Initialize base OUs and admin user (default)"
    echo "  schemas   Load custom LDAP schemas"
    echo "  dns       Bootstrap DNS zones"
    echo "  dhcp      Bootstrap DHCP configuration"
    echo "  all       Run all bootstrap steps"
    echo "  help      Show this help"
}

# =============================================================================
# Main
# =============================================================================

case "${1:-init}" in
    init)    cmd_init ;;
    schemas) cmd_schemas ;;
    dns)     cmd_dns ;;
    dhcp)    cmd_dhcp ;;
    all)     cmd_all ;;
    help|-h|--help) cmd_help ;;
    *)
        echo "Unknown command: $1"
        cmd_help
        exit 1
        ;;
esac
