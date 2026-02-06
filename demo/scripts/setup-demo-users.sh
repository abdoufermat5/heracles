#!/bin/bash
# =============================================================================
# Demo Environment Setup Script
# =============================================================================
# Creates demo users, groups, SSH keys, and sudo rules via the Heracles API
# This script demonstrates the full workflow of the Phase 3 plugins
#
# Prerequisites:
# - Docker infrastructure running (make dev-up)
# - LDAP bootstrapped (make ldap-bootstrap)
# - Demo VMs running (vagrant up)
# - SSH keys generated (./scripts/generate-keys.sh)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_DIR="$(dirname "$SCRIPT_DIR")"
KEYS_DIR="$DEMO_DIR/keys"

# API Configuration
API_URL="${API_URL:-http://localhost:8000}"
API_USER="${API_USER:-hrc-admin}"
API_PASSWORD="${API_PASSWORD:-hrc-admin-secret}"
ACCESS_TOKEN=""

echo "========================================"
echo "  Heracles Demo Setup"
echo "========================================"
echo "API URL: $API_URL"
echo "Keys Dir: $KEYS_DIR"
echo ""

# Check if keys exist
if [ ! -d "$KEYS_DIR" ] || [ ! -f "$KEYS_DIR/testuser.pub" ]; then
    echo "[!] SSH keys not found. Generating them now..."
    "$SCRIPT_DIR/generate-keys.sh"
    echo ""
fi

# Login and get access token
get_token() {
    local response
    response=$(curl -s -X POST "${API_URL}/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"username\": \"${API_USER}\", \"password\": \"${API_PASSWORD}\"}")
    
    ACCESS_TOKEN=$(echo "$response" | jq -r '.access_token // empty')
    if [ -z "$ACCESS_TOKEN" ]; then
        echo "[-] Failed to get access token"
        echo "    Response: $response"
        exit 1
    fi
}

# Helper function for API calls using Bearer token
api_call() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    
    if [ -n "$data" ]; then
        curl -s -X "$method" "${API_URL}${endpoint}" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer ${ACCESS_TOKEN}" \
            -d "$data"
    else
        curl -s -X "$method" "${API_URL}${endpoint}" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer ${ACCESS_TOKEN}"
    fi
}

# Wait for API to be ready
echo "[*] Waiting for API..."
for i in {1..30}; do
    if curl -s "${API_URL}/api/health" > /dev/null 2>&1; then
        echo "[+] API is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "[-] API failed to respond"
        exit 1
    fi
    sleep 1
done

# Get authentication token
echo "[*] Authenticating..."
get_token
echo "[+] Authenticated successfully"

echo ""
echo "=========================================================================="
echo "[*] STEP 1: Create Demo Users via API"
echo "=========================================================================="

# Create testuser
echo ""
echo "[*] Creating testuser..."
result=$(api_call POST "/api/v1/users" '{
    "uid": "testuser",
    "givenName": "Test",
    "sn": "User",
    "cn": "Test User",
    "mail": "testuser@heracles.local",
    "password": "Testpassword123"
}')
echo "$result" | jq -r '.uid // .detail // .' 2>/dev/null || echo "$result"

# Create devuser
echo ""
echo "[*] Creating devuser..."
result=$(api_call POST "/api/v1/users" '{
    "uid": "devuser",
    "givenName": "Dev",
    "sn": "User",
    "cn": "Developer User",
    "mail": "devuser@heracles.local",
    "password": "Devpassword123"
}')
echo "$result" | jq -r '.uid // .detail // .' 2>/dev/null || echo "$result"

# Create opsuser
echo ""
echo "[*] Creating opsuser..."
result=$(api_call POST "/api/v1/users" '{
    "uid": "opsuser",
    "givenName": "Ops",
    "sn": "User",
    "cn": "Operations User",
    "mail": "opsuser@heracles.local",
    "password": "Opspassword123"
}')
echo "$result" | jq -r '.uid // .detail // .' 2>/dev/null || echo "$result"

echo ""
echo "=========================================================================="
echo "[*] STEP 2: Create POSIX Groups (required before activating POSIX on users)"
echo "=========================================================================="

# Create testusers group (primary group for testuser)
echo ""
echo "[*] Creating testusers group (gid 10001)..."
result=$(api_call POST "/api/v1/posix/groups" '{
    "cn": "testusers",
    "gidNumber": 10001,
    "description": "Test users primary group"
}')
echo "$result" | jq -r '.cn // .detail // .' 2>/dev/null || echo "$result"

# Create developers group
echo ""
echo "[*] Creating developers group (gid 10002)..."
result=$(api_call POST "/api/v1/posix/groups" '{
    "cn": "developers",
    "gidNumber": 10002,
    "description": "Developers group"
}')
echo "$result" | jq -r '.cn // .detail // .' 2>/dev/null || echo "$result"

# Create ops group
echo ""
echo "[*] Creating ops group (gid 10003)..."
result=$(api_call POST "/api/v1/posix/groups" '{
    "cn": "ops",
    "gidNumber": 10003,
    "description": "Operations team"
}')
echo "$result" | jq -r '.cn // .detail // .' 2>/dev/null || echo "$result"

echo ""
echo "=========================================================================="
echo "[*] STEP 3: Activate POSIX for Users"
echo "=========================================================================="

# Activate POSIX for testuser (with full host access)
echo ""
echo "[*] Activating POSIX for testuser (trustMode: fullaccess)..."
result=$(api_call POST "/api/v1/users/testuser/posix" '{
    "uidNumber": 10001,
    "gidNumber": 10001,
    "homeDirectory": "/home/testuser",
    "loginShell": "/bin/bash",
    "trustMode": "fullaccess"
}')
echo "$result" | jq -r '.hasPosix // .detail // .' 2>/dev/null || echo "$result"

# Activate POSIX for devuser (restricted to server1 only)
echo ""
echo "[*] Activating POSIX for devuser (trustMode: byhost - server1 only)..."
result=$(api_call POST "/api/v1/users/devuser/posix" '{
    "uidNumber": 10002,
    "gidNumber": 10002,
    "homeDirectory": "/home/devuser",
    "loginShell": "/bin/bash",
    "trustMode": "byhost",
    "host": ["server1"]
}')
echo "$result" | jq -r '.hasPosix // .detail // .' 2>/dev/null || echo "$result"

# Activate POSIX for opsuser (with full host access)
echo ""
echo "[*] Activating POSIX for opsuser (trustMode: fullaccess)..."
result=$(api_call POST "/api/v1/users/opsuser/posix" '{
    "uidNumber": 10003,
    "gidNumber": 10003,
    "homeDirectory": "/home/opsuser",
    "loginShell": "/bin/bash",
    "trustMode": "fullaccess"
}')
echo "$result" | jq -r '.hasPosix // .detail // .' 2>/dev/null || echo "$result"

echo ""
echo "=========================================================================="
echo "[*] STEP 4: Add Users to Secondary Groups"
echo "=========================================================================="

# Add users to developers group
echo ""
echo "[*] Adding testuser and devuser to developers group..."
result=$(api_call PUT "/api/v1/posix/groups/developers" '{
    "memberUid": ["devuser", "testuser"]
}')
echo "$result" | jq -r '.cn // .detail // .' 2>/dev/null || echo "$result"

# Add opsuser to ops group
echo ""
echo "[*] Adding opsuser to ops group..."
result=$(api_call PUT "/api/v1/posix/groups/ops" '{
    "memberUid": ["opsuser"]
}')
echo "$result" | jq -r '.cn // .detail // .' 2>/dev/null || echo "$result"

echo ""
echo "=========================================================================="
echo "[*] STEP 5: Activate SSH with Keys"
echo "=========================================================================="

# Function to activate SSH and add key for a user
activate_ssh() {
    local user="$1"
    local keyfile="$KEYS_DIR/${user}.pub"
    
    if [ ! -f "$keyfile" ]; then
        echo "  [!] Key file not found: $keyfile"
        return 1
    fi
    
    local pubkey=$(cat "$keyfile")
    echo ""
    echo "[*] Activating SSH for $user..."
    # First activate SSH (no payload needed)
    result=$(api_call POST "/api/v1/ssh/users/${user}/activate" "")
    echo "    Activated: $(echo "$result" | jq -r '.hasSsh // .detail // .' 2>/dev/null)"
    
    # Then add the key
    echo "    Adding key..."
    result=$(api_call POST "/api/v1/ssh/users/${user}/keys" "{\"key\": \"$pubkey\"}")
    echo "    Keys: $(echo "$result" | jq -r '.keyCount // .detail // .' 2>/dev/null)"
}

activate_ssh "testuser"
activate_ssh "devuser"
activate_ssh "opsuser"

echo ""
echo "=========================================================================="
echo "[*] STEP 6: Create Sudo Rules"
echo "=========================================================================="

# Sudo rule: testuser can run ALL commands with NOPASSWD
echo ""
echo "[*] Creating sudo rule for testuser (ALL NOPASSWD)..."
result=$(api_call POST "/api/v1/sudo/roles" '{
    "cn": "testuser-sudo",
    "sudoUser": ["testuser"],
    "sudoHost": ["ALL"],
    "sudoCommand": ["ALL"],
    "sudoOption": ["!authenticate"]
}')
echo "$result" | jq -r '.cn // .detail // .' 2>/dev/null || echo "$result"

# Sudo rule: developers can run specific commands
echo ""
echo "[*] Creating sudo rule for developers (limited)..."
result=$(api_call POST "/api/v1/sudo/roles" '{
    "cn": "developers-sudo",
    "sudoUser": ["%developers"],
    "sudoHost": ["ALL"],
    "sudoCommand": ["/usr/bin/apt", "/usr/bin/apt-get", "/usr/bin/systemctl status *", "/usr/bin/journalctl"]
}')
echo "$result" | jq -r '.cn // .detail // .' 2>/dev/null || echo "$result"

# Sudo rule: ops can run ALL commands (with password)
echo ""
echo "[*] Creating sudo rule for ops (ALL with password)..."
result=$(api_call POST "/api/v1/sudo/roles" '{
    "cn": "ops-sudo",
    "sudoUser": ["%ops"],
    "sudoHost": ["ALL"],
    "sudoCommand": ["ALL"]
}')
echo "$result" | jq -r '.cn // .detail // .' 2>/dev/null || echo "$result"

echo ""
echo "=========================================================================="
echo "[*] STEP 7: Register Systems"
echo "=========================================================================="

# Create server1
echo ""
echo "[*] Registering server1..."
result=$(api_call POST "/api/v1/systems" '{
    "cn": "server1",
    "systemType": "server",
    "description": "Demo server VM - Debian Bookworm",
    "ipHostNumber": ["192.168.56.10"],
    "l": "Demo Environment"
}')
echo "$result" | jq -r '.cn // .detail // .' 2>/dev/null || echo "$result"

# Create workstation1
echo ""
echo "[*] Registering workstation1..."
result=$(api_call POST "/api/v1/systems" '{
    "cn": "workstation1",
    "systemType": "workstation",
    "description": "Demo workstation VM - Debian Bookworm",
    "ipHostNumber": ["192.168.56.11"],
    "l": "Demo Environment"
}')
echo "$result" | jq -r '.cn // .detail // .' 2>/dev/null || echo "$result"

# Create mail1
echo ""
echo "[*] Registering mail1..."
result=$(api_call POST "/api/v1/systems" '{
    "cn": "mail1",
    "systemType": "server",
    "description": "Demo mail server VM - Postfix + Dovecot",
    "ipHostNumber": ["192.168.56.22"],
    "l": "Demo Environment"
}')
echo "$result" | jq -r '.cn // .detail // .' 2>/dev/null || echo "$result"

echo ""
echo "=========================================================================="
echo "[*] STEP 8: Create DNS Records for Mail Server"
echo "=========================================================================="

# mail1 A record
echo ""
echo "[*] Creating DNS A record: mail1 -> 192.168.56.22..."
result=$(api_call POST "/api/v1/dns/zones/heracles.local/records" '{
    "name": "mail1",
    "recordType": "A",
    "value": "192.168.56.22",
    "ttl": 3600
}')
echo "$result" | jq -r '.name // .detail // .' 2>/dev/null || echo "$result"

# mail CNAME record
echo ""
echo "[*] Creating DNS CNAME record: mail -> mail1.heracles.local..."
result=$(api_call POST "/api/v1/dns/zones/heracles.local/records" '{
    "name": "mail",
    "recordType": "CNAME",
    "value": "mail1.heracles.local.",
    "ttl": 3600
}')
echo "$result" | jq -r '.name // .detail // .' 2>/dev/null || echo "$result"

# MX record for the zone
echo ""
echo "[*] Creating DNS MX record: heracles.local -> mail1.heracles.local (priority 10)..."
result=$(api_call POST "/api/v1/dns/zones/heracles.local/records" '{
    "name": "@",
    "recordType": "MX",
    "value": "mail1.heracles.local.",
    "ttl": 3600,
    "priority": 10
}')
echo "$result" | jq -r '.name // .detail // .' 2>/dev/null || echo "$result"

# PTR record in reverse zone
echo ""
echo "[*] Creating DNS PTR record: 22 -> mail1.heracles.local..."
result=$(api_call POST "/api/v1/dns/zones/56.168.192.in-addr.arpa/records" '{
    "name": "22",
    "recordType": "PTR",
    "value": "mail1.heracles.local.",
    "ttl": 3600
}')
echo "$result" | jq -r '.name // .detail // .' 2>/dev/null || echo "$result"

# Trigger DNS sync on ns1
echo ""
echo "[*] Syncing DNS records to BIND on ns1..."
DEMO_DIR_PARENT="$(dirname "$(dirname "$SCRIPT_DIR")")"
if command -v vagrant &>/dev/null && [ -f "$DEMO_DIR/Vagrantfile" ]; then
    (cd "$DEMO_DIR" && vagrant ssh ns1 -c 'sudo /usr/local/bin/ldap-dns-sync.sh && sudo systemctl reload named' 2>/dev/null)
    echo "[+] DNS synced and reloaded on ns1"
else
    echo "[!] Vagrant not available — DNS will sync within 5 minutes via cron"
fi

echo ""
echo "=========================================================================="
echo "[*] STEP 9: Create DHCP Reservation for Mail Server"
echo "=========================================================================="

echo ""
echo "[*] Creating DHCP host reservation: mail1 (08:00:27:00:00:22 -> 192.168.56.22)..."
result=$(api_call POST "/api/v1/dhcp/demo-dhcp-service/hosts" '{
    "cn": "mail1",
    "dhcpHWAddress": "ethernet 08:00:27:00:00:22",
    "fixedAddress": "192.168.56.22",
    "comments": "Mail server - Postfix + Dovecot + Roundcube"
}')
echo "$result" | jq -r '.cn // .detail // .' 2>/dev/null || echo "$result"

# Trigger DHCP sync on dhcp1
echo ""
echo "[*] Syncing DHCP config on dhcp1..."
if command -v vagrant &>/dev/null && [ -f "$DEMO_DIR/Vagrantfile" ]; then
    if (cd "$DEMO_DIR" && vagrant ssh dhcp1 -c 'sudo /usr/local/bin/ldap-dhcp-sync.sh' 2>/dev/null); then
        echo "[+] DHCP synced and reloaded on dhcp1"
    else
        echo "[!] DHCP sync failed — will retry via cron within 5 minutes"
    fi
else
    echo "[!] Vagrant not available — DHCP will sync within 5 minutes via cron"
fi

echo ""
echo "=========================================================================="
echo "[*] STEP 10: Activate Mail Plugin on Users"
echo "=========================================================================="

# Activate mail for testuser
echo ""
echo "[*] Activating mail for testuser..."
result=$(api_call POST "/api/v1/mail/users/testuser/activate" '{
    "mail": "testuser@heracles.local",
    "mailServer": "mail1.heracles.local",
    "quotaMb": 1024,
    "alternateAddresses": ["tuser@heracles.local"]
}')
echo "$result" | jq -r '.hasMail // .detail // .' 2>/dev/null || echo "$result"

# Activate mail for devuser
echo ""
echo "[*] Activating mail for devuser..."
result=$(api_call POST "/api/v1/mail/users/devuser/activate" '{
    "mail": "devuser@heracles.local",
    "mailServer": "mail1.heracles.local",
    "quotaMb": 512,
    "alternateAddresses": ["dev@heracles.local"]
}')
echo "$result" | jq -r '.hasMail // .detail // .' 2>/dev/null || echo "$result"

# Activate mail for opsuser (with forwarding to testuser)
echo ""
echo "[*] Activating mail for opsuser (with forwarding)..."
result=$(api_call POST "/api/v1/mail/users/opsuser/activate" '{
    "mail": "opsuser@heracles.local",
    "mailServer": "mail1.heracles.local",
    "quotaMb": 1024,
    "alternateAddresses": ["ops@heracles.local"],
    "forwardingAddresses": ["testuser@heracles.local"]
}')
echo "$result" | jq -r '.hasMail // .detail // .' 2>/dev/null || echo "$result"

echo ""
echo "=========================================================================="
echo "[*] STEP 11: Create Mailing List Group & Activate Mail"
echo "=========================================================================="
# Note: The mail plugin requires groupOfNames (not posixGroup).
# We create a dedicated groupOfNames group for the mailing list,
# add developer members, then activate the mail plugin on it.

echo ""
echo "[*] Creating developers-ml groupOfNames group..."
result=$(api_call POST "/api/v1/groups" '{
    "cn": "developers-ml",
    "description": "Developers mailing list"
}')
echo "$result" | jq -r '.cn // .detail // .' 2>/dev/null || echo "$result"

# Add members
echo "[*] Adding testuser and devuser to developers-ml..."
api_call POST "/api/v1/groups/developers-ml/members" '{"uid": "testuser"}' > /dev/null 2>&1
api_call POST "/api/v1/groups/developers-ml/members" '{"uid": "devuser"}' > /dev/null 2>&1
echo "    Members added"

# Activate mailing list
echo ""
echo "[*] Activating mailing list on developers-ml..."
result=$(api_call POST "/api/v1/mail/groups/developers-ml/activate" '{
    "mail": "developers@heracles.local",
    "mailServer": "mail1.heracles.local",
    "alternateAddresses": ["dev-team@heracles.local"]
}')
echo "$result" | jq -r '.active // .detail // .' 2>/dev/null || echo "$result"

echo ""
echo "=========================================================================="
echo "[+] Demo Setup Complete!"
echo "=========================================================================="
echo ""
echo "[i] Users created:"
echo "   ┌─────────────┬──────────────────┬─────────────────────────────────────┐"
echo "   │ User        │ Password         │ Sudo Permissions                    │"
echo "   ├─────────────┼──────────────────┼─────────────────────────────────────┤"
echo "   │ testuser    │ Testpassword123  │ ALL (NOPASSWD)                      │"
echo "   │ devuser     │ Devpassword123   │ apt, systemctl status, journalctl   │"
echo "   │ opsuser     │ Opspassword123   │ ALL (with password)                 │"
echo "   └─────────────┴──────────────────┴─────────────────────────────────────┘"
echo ""
echo "[i] Mail accounts:"
echo "   ┌─────────────┬─────────────────────────────┬──────────────────────────┐"
echo "   │ User        │ Email                       │ Aliases                  │"
echo "   ├─────────────┼─────────────────────────────┼──────────────────────────┤"
echo "   │ testuser    │ testuser@heracles.local      │ tuser@heracles.local     │"
echo "   │ devuser     │ devuser@heracles.local       │ dev@heracles.local       │"
echo "   │ opsuser     │ opsuser@heracles.local       │ ops@heracles.local       │"
echo "   └─────────────┴─────────────────────────────┴──────────────────────────┘"
echo ""
echo "[i] Mailing lists:"
echo "   ┌─────────────────┬──────────────────────────────┬────────────────────────────┐"
echo "   │ Group           │ Email                        │ Aliases                    │"
echo "   ├─────────────────┼──────────────────────────────┼────────────────────────────┤"
echo "   │ developers-ml   │ developers@heracles.local     │ dev-team@heracles.local    │"
echo "   └─────────────────┴──────────────────────────────┴────────────────────────────┘"
echo ""
echo "[i] Systems registered:"
echo "   ┌──────────────┬─────────────┬────────────────┐"
echo "   │ Hostname     │ Type        │ IP Address     │"
echo "   ├──────────────┼─────────────┼────────────────┤"
echo "   │ server1      │ server      │ 192.168.56.10  │"
echo "   │ workstation1 │ workstation │ 192.168.56.11  │"
echo "   │ mail1        │ server      │ 192.168.56.22  │"
echo "   └──────────────┴─────────────┴────────────────┘"
echo ""
echo "[i] DNS records created:"
echo "   ┌──────────┬───────┬────────────────────────────┐"
echo "   │ Name     │ Type  │ Value                      │"
echo "   ├──────────┼───────┼────────────────────────────┤"
echo "   │ mail1    │ A     │ 192.168.56.22              │"
echo "   │ mail     │ CNAME │ mail1.heracles.local.      │"
echo "   │ @        │ MX    │ 10 mail1.heracles.local.   │"
echo "   │ 22 (PTR) │ PTR   │ mail1.heracles.local.      │"
echo "   └──────────┴───────┴────────────────────────────┘"
echo ""
echo "[i] DHCP reservations created:"
echo "   ┌──────────────┬─────────────────────┬────────────────┐"
echo "   │ Host         │ MAC Address         │ Fixed IP       │"
echo "   ├──────────────┼─────────────────────┼────────────────┤"
echo "   │ mail1        │ 08:00:27:00:00:22   │ 192.168.56.22  │"
echo "   └──────────────┴─────────────────────┴────────────────┘"
echo ""
echo "[*] SSH Keys location: $KEYS_DIR"
echo ""
echo "[i] Test SSH access:"
echo "   ssh -i $KEYS_DIR/testuser testuser@192.168.56.10"
echo "   ssh -i $KEYS_DIR/devuser devuser@192.168.56.10"
echo "   ssh -i $KEYS_DIR/opsuser opsuser@192.168.56.10"
echo ""
echo "[i] Test sudo:"
echo "   # testuser - should work without password"
echo "   ssh -i $KEYS_DIR/testuser testuser@192.168.56.10 'sudo whoami'"
echo ""
echo "   # devuser - allowed commands only"
echo "   ssh -i $KEYS_DIR/devuser devuser@192.168.56.10 'sudo /usr/bin/apt --version'"
echo ""
echo "[i] Test mail:"
echo "   # Send a test email (from the mail1 VM):"
echo "   vagrant ssh mail1 -c 'swaks --to testuser@heracles.local --from admin@heracles.local --server localhost --body \"Hello from Heracles!\"'"
echo ""
echo "   # Send via authenticated submission:"
echo "   vagrant ssh mail1 -c 'swaks --to devuser@heracles.local --from testuser@heracles.local --server localhost:587 --tls --auth-user testuser --auth-password Testpassword123'"
echo ""
echo "   # Check mailbox:"
echo "   vagrant ssh mail1 -c 'sudo doveadm mailbox list -u testuser'"
echo ""
echo "   # Clear SSSD cache on VMs if users don't appear:"
echo "   vagrant ssh server1 -c 'sudo sss_cache -E && sudo systemctl restart sssd'"
