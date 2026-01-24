#!/bin/bash
#
# Script to load custom LDAP schemas into the running OpenLDAP container
# Usage: ./scripts/ldap-load-schemas.sh [schema_name]
#
# If no schema_name is provided, all schemas will be loaded.
# Available schemas: heracles-aux, sudo, openssh-lpk
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SCHEMAS_DIR="$PROJECT_ROOT/docker/ldap/schemas"
LDAP_CONTAINER="${LDAP_CONTAINER:-heracles-ldap}"

# LDAP admin credentials (from docker-compose)
LDAP_ADMIN_PASSWORD="${LDAP_ADMIN_PASSWORD:-admin}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if container is running
check_container() {
    if ! docker ps --format '{{.Names}}' | grep -q "^${LDAP_CONTAINER}$"; then
        log_error "LDAP container '$LDAP_CONTAINER' is not running"
        log_info "Start it with: docker compose up -d ldap"
        exit 1
    fi
}

# Check if schema is already loaded
schema_exists() {
    local schema_name="$1"
    docker exec "$LDAP_CONTAINER" ldapsearch -Y EXTERNAL -H ldapi:/// \
        -b "cn=schema,cn=config" "(cn=*${schema_name}*)" cn 2>/dev/null | grep -q "cn: {[0-9]*}${schema_name}"
}

# Load a schema from LDIF file
load_schema() {
    local schema_name="$1"
    local ldif_file="$SCHEMAS_DIR/${schema_name}.ldif"

    if [[ ! -f "$ldif_file" ]]; then
        log_error "Schema file not found: $ldif_file"
        return 1
    fi

    log_info "Checking if schema '$schema_name' is already loaded..."
    
    if schema_exists "$schema_name"; then
        log_warn "Schema '$schema_name' is already loaded, skipping"
        return 0
    fi

    log_info "Loading schema '$schema_name' from $ldif_file..."
    
    # Copy LDIF to container and load it
    docker cp "$ldif_file" "$LDAP_CONTAINER:/tmp/${schema_name}.ldif"
    
    if docker exec "$LDAP_CONTAINER" ldapadd -Y EXTERNAL -H ldapi:/// -f "/tmp/${schema_name}.ldif" 2>&1; then
        log_info "Schema '$schema_name' loaded successfully"
        # Cleanup
        docker exec "$LDAP_CONTAINER" rm -f "/tmp/${schema_name}.ldif"
        return 0
    else
        log_error "Failed to load schema '$schema_name'"
        docker exec "$LDAP_CONTAINER" rm -f "/tmp/${schema_name}.ldif"
        return 1
    fi
}

# List available schemas
list_schemas() {
    log_info "Available schemas in $SCHEMAS_DIR:"
    for ldif in "$SCHEMAS_DIR"/*.ldif; do
        if [[ -f "$ldif" ]]; then
            schema_name=$(basename "$ldif" .ldif)
            echo "  - $schema_name"
        fi
    done
}

# List loaded schemas
list_loaded_schemas() {
    log_info "Currently loaded custom schemas in LDAP:"
    docker exec "$LDAP_CONTAINER" ldapsearch -Y EXTERNAL -H ldapi:/// \
        -b "cn=schema,cn=config" "(objectClass=olcSchemaConfig)" cn 2>/dev/null | \
        grep "^cn:" | sed 's/cn: /  - /'
}

# Main function
main() {
    check_container

    if [[ "$1" == "--list" || "$1" == "-l" ]]; then
        list_schemas
        echo ""
        list_loaded_schemas
        exit 0
    fi

    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        echo "Usage: $0 [OPTIONS] [schema_name...]"
        echo ""
        echo "Load custom LDAP schemas into the running OpenLDAP container."
        echo ""
        echo "Options:"
        echo "  -l, --list    List available and loaded schemas"
        echo "  -h, --help    Show this help message"
        echo "  -a, --all     Load all available schemas"
        echo ""
        echo "Examples:"
        echo "  $0                    # Load all schemas"
        echo "  $0 openssh-lpk        # Load only openssh-lpk schema"
        echo "  $0 heracles-aux sudo  # Load specific schemas"
        exit 0
    fi

    local schemas_to_load=()
    
    if [[ $# -eq 0 || "$1" == "--all" || "$1" == "-a" ]]; then
        # Load all schemas
        for ldif in "$SCHEMAS_DIR"/*.ldif; do
            if [[ -f "$ldif" ]]; then
                schemas_to_load+=("$(basename "$ldif" .ldif)")
            fi
        done
    else
        schemas_to_load=("$@")
    fi

    if [[ ${#schemas_to_load[@]} -eq 0 ]]; then
        log_error "No schemas found to load"
        exit 1
    fi

    log_info "Schemas to load: ${schemas_to_load[*]}"
    echo ""

    local failed=0
    for schema in "${schemas_to_load[@]}"; do
        if ! load_schema "$schema"; then
            ((failed++))
        fi
        echo ""
    done

    if [[ $failed -eq 0 ]]; then
        log_info "All schemas loaded successfully!"
    else
        log_error "$failed schema(s) failed to load"
        exit 1
    fi
}

main "$@"
