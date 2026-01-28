#!/bin/bash
# =============================================================================
# LDAP SSH Public Keys Fetcher
# =============================================================================
# This script is called by OpenSSH's AuthorizedKeysCommand to fetch
# public keys from LDAP for a given username.
#
# Handles LDAP line folding (continuation lines starting with space).
#
# Usage: /usr/local/bin/ldap-ssh-keys.sh <username>
# =============================================================================

CONFIG_FILE="/etc/ssh/ldap-ssh-keys.conf"

if [[ -f "${CONFIG_FILE}" ]]; then
    source "${CONFIG_FILE}"
else
    echo "# Error: Config file not found: ${CONFIG_FILE}" >&2
    exit 1
fi

USERNAME="$1"

if [[ -z "${USERNAME}" ]]; then
    echo "# Error: No username provided" >&2
    exit 1
fi

# Sanitize username (prevent LDAP injection)
if [[ ! "${USERNAME}" =~ ^[a-zA-Z0-9._-]+$ ]]; then
    echo "# Error: Invalid username format" >&2
    exit 1
fi

# Fetch LDAP output and unfold continuation lines
# LDAP line folding: long lines are split with newline + single space
ldapsearch -x \
    -H "ldap://${LDAP_HOST}:${LDAP_PORT}" \
    -D "${LDAP_BIND_DN}" \
    -w "${LDAP_BIND_PASSWORD}" \
    -b "${LDAP_USER_BASE}" \
    -LLL \
    "(uid=${USERNAME})" \
    sshPublicKey 2>/dev/null | \
    awk '
    /^sshPublicKey:/ {
        # Start of a key - extract value after "sshPublicKey: "
        key = $0
        sub(/^sshPublicKey: */, "", key)
        next
    }
    /^ / {
        # Continuation line - append without the leading space
        sub(/^ /, "", $0)
        key = key $0
        next
    }
    key != "" {
        # Not a continuation - print collected key and reset
        print key
        key = ""
    }
    END {
        # Print last key if any
        if (key != "") print key
    }
    '

exit 0
