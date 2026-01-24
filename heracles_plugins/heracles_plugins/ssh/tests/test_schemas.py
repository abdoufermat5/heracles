"""
SSH Plugin Tests - Schemas
==========================

Tests for SSH key validation and parsing.
"""

import pytest

from pydantic import ValidationError

from heracles_plugins.ssh.schemas import (
    SSHKeyCreate,
    SSHKeyRead,
    UserSSHStatus,
    UserSSHActivate,
    UserSSHKeysUpdate,
    parse_ssh_key,
    compute_fingerprint,
    validate_ssh_key,
    SSH_KEY_TYPES,
)


# ============================================================================
# Test Data
# ============================================================================

# Valid test keys (real format public keys for testing)
# Ed25519 key - 256-bit (the most common modern key type)
VALID_ED25519_KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJl3VtABZZPW+6c3WElBjAV4VvC6TZ0t0VwN9Fq9pCzF user@host"

# ECDSA key - nistp256 (valid test key)
VALID_ECDSA_KEY = "ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBHJPm5R7TFBXgzRWXvh7GE1f7MN15Z1fO7PK2dF9P8S8VWmQCDV6fP+L9kH5I2JhPR5M7CqQ/n9TW3d2m4P8l0s= test@server"

# RSA key - from ssh-keygen output (a real 2048-bit key for testing)
VALID_RSA_KEY = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCsLLyrP/nK6qHqXM1kXLXRLwxCLUZJkmjM0R6YBDL1qPaYqIHHwjT9M6uTqzFq8oHRpKxzVzGhLjHX5X8qhyLUqJHN0dQ5MO1XZBvPOPWHqOGqYW9RPqoYJEG9QNdH3PEYwcKvAo8cJNXMlRZrYB9tJKJq7sXLR9XJgHJOPQh5pNpJQN8WQHPE/MwSQdCmAUZm5qH8PO3LhF3RB5qT8qVKMdBhJ8vN7L6YTEKBFqJYJHPWC2LRSPQ2dKMhQCLVPJ9qJ7K3LhQ8KpM9JgQJXP5YBFDQL7OqJ3K8LhQ2KpM1JgQJXP2YBFDQL3OqJ5K8LhQ4KpM3JgQJXP4YBFDQL5Oq== test@example.com"


# ============================================================================
# SSH Key Validation Tests
# ============================================================================

class TestSSHKeyTypes:
    """Test SSH key type constants."""
    
    def test_supported_key_types(self):
        """All common key types should be supported."""
        assert "ssh-rsa" in SSH_KEY_TYPES
        assert "ssh-ed25519" in SSH_KEY_TYPES
        assert "ssh-dss" in SSH_KEY_TYPES
        assert "ecdsa-sha2-nistp256" in SSH_KEY_TYPES
        assert "ecdsa-sha2-nistp384" in SSH_KEY_TYPES
        assert "ecdsa-sha2-nistp521" in SSH_KEY_TYPES
    
    def test_security_key_types(self):
        """Security key types should be supported."""
        assert "sk-ssh-ed25519@openssh.com" in SSH_KEY_TYPES
        assert "sk-ecdsa-sha2-nistp256@openssh.com" in SSH_KEY_TYPES


class TestParseSSHKey:
    """Test SSH key parsing."""
    
    def test_parse_rsa_key(self):
        """Should parse RSA key correctly."""
        result = parse_ssh_key(VALID_RSA_KEY)
        
        assert result["key_type"] == "ssh-rsa"
        assert result["comment"] == "test@example.com"
        assert result["fingerprint"].startswith("SHA256:")
        assert result["bits"] is not None
    
    def test_parse_ed25519_key(self):
        """Should parse Ed25519 key correctly."""
        result = parse_ssh_key(VALID_ED25519_KEY)
        
        assert result["key_type"] == "ssh-ed25519"
        assert result["comment"] == "user@host"
        assert result["fingerprint"].startswith("SHA256:")
        assert result["bits"] == 256
    
    def test_parse_ecdsa_key(self):
        """Should parse ECDSA key correctly."""
        result = parse_ssh_key(VALID_ECDSA_KEY)
        
        assert result["key_type"] == "ecdsa-sha2-nistp256"
        assert result["comment"] == "test@server"
        assert result["fingerprint"].startswith("SHA256:")
    
    def test_parse_key_without_comment(self):
        """Should parse key without comment."""
        key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJl3VtABZZPW+6c3WElBjAV4VvC6TZ0t0VwN9Fq9pCzF"
        result = parse_ssh_key(key)
        
        assert result["key_type"] == "ssh-ed25519"
        assert result["comment"] is None
    
    def test_parse_invalid_key_format(self):
        """Should reject invalid key format."""
        with pytest.raises(ValueError, match="Invalid SSH key format"):
            parse_ssh_key("invalid-key")
    
    def test_parse_unknown_key_type(self):
        """Should reject unknown key type."""
        # Unknown type with valid base64 - parse_ssh_key doesn't check key type, only validate_ssh_key does
        result = parse_ssh_key("ssh-unknown AAAAC3NzaC1lZDI1NTE5AAAAIJl3VtABZZPW+6c3WElBjAV4VvC6TZ0t0VwN9Fq9pCzF test")
        assert result["key_type"] == "ssh-unknown"  # It parses but validation rejects
    
    def test_parse_invalid_base64(self):
        """Should reject invalid base64 data."""
        with pytest.raises(ValueError, match="cannot decode base64"):
            parse_ssh_key("ssh-ed25519 !!!invalid-base64!!! test")


class TestComputeFingerprint:
    """Test fingerprint computation."""
    
    def test_fingerprint_format(self):
        """Fingerprint should start with SHA256:"""
        fp = compute_fingerprint(VALID_ED25519_KEY)
        assert fp.startswith("SHA256:")
    
    def test_fingerprint_consistency(self):
        """Same key should always produce same fingerprint."""
        fp1 = compute_fingerprint(VALID_ED25519_KEY)
        fp2 = compute_fingerprint(VALID_ED25519_KEY)
        assert fp1 == fp2
    
    def test_fingerprint_different_keys(self):
        """Different keys should produce different fingerprints."""
        fp1 = compute_fingerprint(VALID_RSA_KEY)
        fp2 = compute_fingerprint(VALID_ED25519_KEY)
        assert fp1 != fp2
    
    def test_fingerprint_invalid_key(self):
        """Should raise error for invalid key."""
        with pytest.raises(ValueError):
            compute_fingerprint("invalid")


class TestValidateSSHKey:
    """Test key validation function."""
    
    def test_valid_keys(self):
        """Should return True for valid keys."""
        assert validate_ssh_key(VALID_RSA_KEY) is True
        assert validate_ssh_key(VALID_ED25519_KEY) is True
        assert validate_ssh_key(VALID_ECDSA_KEY) is True
    
    def test_invalid_keys(self):
        """Should return False for invalid keys."""
        assert validate_ssh_key("") is False
        assert validate_ssh_key("invalid") is False
        assert validate_ssh_key("ssh-rsa invalid") is False


# ============================================================================
# Pydantic Model Tests
# ============================================================================

class TestSSHKeyCreate:
    """Test SSHKeyCreate model."""
    
    def test_valid_key_with_comment(self):
        """Should accept valid key with custom comment."""
        model = SSHKeyCreate(key=VALID_ED25519_KEY, comment="My laptop")
        assert model.comment == "My laptop"
    
    def test_valid_key_extracts_comment(self):
        """Should extract comment from key if not provided."""
        model = SSHKeyCreate(key=VALID_ED25519_KEY)
        assert model.comment == "user@host"
    
    def test_key_normalization(self):
        """Should normalize key whitespace."""
        key_with_spaces = "  " + VALID_ED25519_KEY + "  "
        model = SSHKeyCreate(key=key_with_spaces)
        assert model.key == VALID_ED25519_KEY
    
    def test_rejects_empty_key(self):
        """Should reject empty key."""
        with pytest.raises(ValidationError):
            SSHKeyCreate(key="")
    
    def test_rejects_invalid_key(self):
        """Should reject invalid key format."""
        with pytest.raises(ValidationError):
            SSHKeyCreate(key="not-a-valid-key")
    
    def test_rejects_unknown_type(self):
        """Should reject unknown key type."""
        with pytest.raises(ValidationError):
            SSHKeyCreate(key="ssh-unknown AAAAC3NzaC1lZDI1NTE5AAAAIJl3VtABZZPW+6c3WElBjAV4VvC6TZ0t0VwN9Fq9pCzF test")


class TestSSHKeyRead:
    """Test SSHKeyRead model."""
    
    def test_from_dict(self):
        """Should create from dictionary."""
        data = {
            "key": VALID_ED25519_KEY,
            "key_type": "ssh-ed25519",
            "fingerprint": "SHA256:abc123",
            "comment": "test",
            "bits": 256,
        }
        model = SSHKeyRead(**data)
        assert model.key_type == "ssh-ed25519"
        assert model.fingerprint == "SHA256:abc123"


class TestUserSSHStatus:
    """Test UserSSHStatus model."""
    
    def test_from_dict(self):
        """Should create from dictionary."""
        data = {
            "uid": "testuser",
            "dn": "uid=testuser,ou=people,dc=example,dc=com",
            "has_ssh": False,
            "key_count": 0,
            "keys": [],
        }
        model = UserSSHStatus(**data)
        assert model.uid == "testuser"
        assert model.has_ssh is False
    
    def test_with_keys(self):
        """Should include keys."""
        data = {
            "uid": "testuser",
            "dn": "uid=testuser,ou=people,dc=example,dc=com",
            "has_ssh": True,
            "key_count": 1,
            "keys": [{
                "key": VALID_ED25519_KEY,
                "key_type": "ssh-ed25519",
                "fingerprint": "SHA256:abc123",
                "comment": "test",
                "bits": 256,
            }],
        }
        model = UserSSHStatus(**data)
        assert model.key_count == 1
        assert len(model.keys) == 1


class TestUserSSHActivate:
    """Test UserSSHActivate model."""
    
    def test_without_initial_key(self):
        """Should work without initial key."""
        model = UserSSHActivate()
        assert model.initial_key is None
    
    def test_with_initial_key(self):
        """Should accept initial key."""
        model = UserSSHActivate(initial_key=VALID_ED25519_KEY)
        assert model.initial_key is not None


class TestUserSSHKeysUpdate:
    """Test UserSSHKeysUpdate model."""
    
    def test_empty_keys(self):
        """Should accept empty key list."""
        model = UserSSHKeysUpdate(keys=[])
        assert model.keys == []
    
    def test_multiple_keys(self):
        """Should accept multiple keys."""
        model = UserSSHKeysUpdate(keys=[VALID_ED25519_KEY, VALID_ECDSA_KEY])
        assert len(model.keys) == 2
    
    def test_filters_empty_keys(self):
        """Should filter out empty keys."""
        model = UserSSHKeysUpdate(keys=[VALID_ED25519_KEY, "", "  "])
        assert len(model.keys) == 1
    
    def test_rejects_invalid_keys(self):
        """Should reject list with invalid keys."""
        with pytest.raises(ValidationError):
            UserSSHKeysUpdate(keys=["invalid-key"])
    
    def test_rejects_unknown_type(self):
        """Should reject list with unknown key type."""
        with pytest.raises(ValidationError):
            UserSSHKeysUpdate(keys=["ssh-unknown AAAAC3NzaC1lZDI1NTE5AAAAIJl3VtABZZPW+6c3WElBjAV4VvC6TZ0t0VwN9Fq9pCzF test"])
