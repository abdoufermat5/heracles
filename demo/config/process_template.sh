#!/bin/bash
# =============================================================================
# Template Processor for Heracles Demo
# =============================================================================
# Substitutes variables in template files using values from demo.conf
#
# Usage:
#   process_template.sh <template_file> <output_file>
#   process_template.sh <template_file>  # outputs to stdout
#
# Variables in templates use @VARIABLE_NAME@ format
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/demo.conf"

# Source configuration
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
elif [ -f "/vagrant/config/demo.conf" ]; then
    source "/vagrant/config/demo.conf"
else
    echo "ERROR: Cannot find demo.conf" >&2
    exit 1
fi

# Process template
process_template() {
    local template="$1"
    local output="$2"
    
    if [ ! -f "$template" ]; then
        echo "ERROR: Template file not found: $template" >&2
        exit 1
    fi
    
    # Create sed substitution commands
    local sed_cmd=""
    sed_cmd+="s|@HOST_IP@|${HOST_IP}|g;"
    sed_cmd+="s|@NS1_IP@|${NS1_IP}|g;"
    sed_cmd+="s|@SERVER1_IP@|${SERVER1_IP}|g;"
    sed_cmd+="s|@WORKSTATION1_IP@|${WORKSTATION1_IP}|g;"
    sed_cmd+="s|@DOMAIN@|${DOMAIN}|g;"
    sed_cmd+="s|@LDAP_HOST@|${LDAP_HOST}|g;"
    sed_cmd+="s|@LDAP_PORT@|${LDAP_PORT}|g;"
    sed_cmd+="s|@LDAP_URI@|${LDAP_URI}|g;"
    sed_cmd+="s|@LDAP_BASE_DN@|${LDAP_BASE_DN}|g;"
    sed_cmd+="s|@LDAP_USERS_DN@|${LDAP_USERS_DN}|g;"
    sed_cmd+="s|@LDAP_GROUPS_DN@|${LDAP_GROUPS_DN}|g;"
    sed_cmd+="s|@LDAP_SYSTEMS_DN@|${LDAP_SYSTEMS_DN}|g;"
    sed_cmd+="s|@LDAP_SUDOERS_DN@|${LDAP_SUDOERS_DN}|g;"
    sed_cmd+="s|@LDAP_DNS_DN@|${LDAP_DNS_DN}|g;"
    sed_cmd+="s|@LDAP_ADMIN_DN@|${LDAP_ADMIN_DN}|g;"
    sed_cmd+="s|@LDAP_ADMIN_PASSWORD@|${LDAP_ADMIN_PASSWORD}|g;"
    sed_cmd+="s|@LDAP_BIND_DN@|${LDAP_BIND_DN}|g;"
    sed_cmd+="s|@LDAP_BIND_PASSWORD@|${LDAP_BIND_PASSWORD}|g;"
    sed_cmd+="s|@DNS_SERVER@|${DNS_SERVER}|g;"
    sed_cmd+="s|@DNS_FORWARDER@|${DNS_FORWARDER}|g;"
    sed_cmd+="s|@DNS_SEARCH_DOMAIN@|${DNS_SEARCH_DOMAIN}|g;"
    sed_cmd+="s|@DNS_FORWARD_ZONE@|${DNS_FORWARD_ZONE}|g;"
    sed_cmd+="s|@DNS_REVERSE_ZONE@|${DNS_REVERSE_ZONE}|g;"
    sed_cmd+="s|@SSSD_CACHE_TIMEOUT@|${SSSD_CACHE_TIMEOUT}|g;"
    sed_cmd+="s|@SSSD_ENUM_CACHE_TIMEOUT@|${SSSD_ENUM_CACHE_TIMEOUT}|g;"
    
    if [ -n "$output" ]; then
        sed "$sed_cmd" "$template" > "$output"
    else
        sed "$sed_cmd" "$template"
    fi
}

# Main
if [ $# -lt 1 ]; then
    echo "Usage: $0 <template_file> [output_file]" >&2
    exit 1
fi

process_template "$1" "$2"
