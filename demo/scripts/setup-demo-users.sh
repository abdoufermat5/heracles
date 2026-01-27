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
    "password": "testpassword123"
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
    "password": "devpassword123"
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
    "password": "opspassword123"
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

echo ""
echo "=========================================================================="
echo "[+] Demo Setup Complete!"
echo "=========================================================================="
echo ""
echo "[i] Users created:"
echo "   ┌─────────────┬──────────────────┬─────────────────────────────────────┐"
echo "   │ User        │ Password         │ Sudo Permissions                    │"
echo "   ├─────────────┼──────────────────┼─────────────────────────────────────┤"
echo "   │ testuser    │ testpassword123  │ ALL (NOPASSWD)                      │"
echo "   │ devuser     │ devpassword123   │ apt, systemctl status, journalctl   │"
echo "   │ opsuser     │ opspassword123   │ ALL (with password)                 │"
echo "   └─────────────┴──────────────────┴─────────────────────────────────────┘"
echo ""
echo "[i] Systems registered:"
echo "   ┌──────────────┬─────────────┬────────────────┐"
echo "   │ Hostname     │ Type        │ IP Address     │"
echo "   ├──────────────┼─────────────┼────────────────┤"
echo "   │ server1      │ server      │ 192.168.56.10  │"
echo "   │ workstation1 │ workstation │ 192.168.56.11  │"
echo "   └──────────────┴─────────────┴────────────────┘"
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
echo "   # Clear SSSD cache on VMs if users don't appear:"
echo "   vagrant ssh server1 -c 'sudo sss_cache -E && sudo systemctl restart sssd'"
