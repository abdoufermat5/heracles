#!/bin/bash
# =============================================================================
# Generate SSH Keys for Demo Users
# =============================================================================
# Creates SSH key pairs for demo testing in the demo/keys directory

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_DIR="$(dirname "$SCRIPT_DIR")"
KEYS_DIR="$DEMO_DIR/keys"

echo "[*] Generating SSH Keys for Demo"
echo "================================"
echo "Keys directory: $KEYS_DIR"
echo ""

# Create keys directory
mkdir -p "$KEYS_DIR"

# Function to generate a key if it doesn't exist
generate_key() {
    local username="$1"
    local keyfile="$KEYS_DIR/$username"
    
    if [ -f "$keyfile" ]; then
        echo "  [i]  Key for $username already exists, skipping"
    else
        echo "  [*] Generating key for $username..."
        ssh-keygen -t ed25519 -f "$keyfile" -N "" -C "${username}@heracles-demo" -q
        chmod 600 "$keyfile"
        chmod 644 "${keyfile}.pub"
    fi
}

# Generate keys for demo users
generate_key "testuser"
generate_key "devuser"
generate_key "opsuser"

echo ""
echo "✅ SSH keys generated!"
echo ""
echo "📁 Keys location: $KEYS_DIR"
ls -la "$KEYS_DIR"
echo ""
echo "💡 Usage example:"
echo "   ssh -i $KEYS_DIR/testuser testuser@192.168.56.10"
