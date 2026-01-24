"""
SSH Plugin Tests - Service
==========================

Tests for SSHService with mocked LDAP.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from heracles_plugins.ssh.service import SSHService
from heracles_plugins.ssh.schemas import (
    SSHKeyCreate,
    SSHKeyRead,
    UserSSHStatus,
    UserSSHActivate,
    UserSSHKeysUpdate,
)


# ============================================================================
# Test Data
# ============================================================================

VALID_ED25519_KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJl3VtABZZPW+6c3WElBjAV4VvC6TZ0t0VwN9Fq9pCzF user@host"
VALID_RSA_KEY = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCsLLyrP/nK6qHqXM1kXLXRLwxCLUZJkmjM0R6YBDL1qPaYqIHHwjT9M6uTqzFq8oHRpKxzVzGhLjHX5X8qhyLUqJHN0dQ5MO1XZBvPOPWHqOGqYW9RPqoYJEG9QNdH3PEYwcKvAo8cJNXMlRZrYB9tJKJq7sXLR9XJgHJOPQh5pNpJQN8WQHPE/MwSQdCmAUZm5qH8PO3LhF3RB5qT8qVKMdBhJ8vN7L6YTEKBFqJYJHPWC2LRSPQ2dKMhQCLVPJ9qJ7K3LhQ8KpM9JgQJXP5YBFDQL7OqJ3K8LhQ2KpM1JgQJXP2YBFDQL3OqJ5K8LhQ4KpM3JgQJXP4YBFDQL5Oq== admin@server"
VALID_ECDSA_KEY = "ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBHJPm5R7TFBXgzRWXvh7GE1f7MN15Z1fO7PK2dF9P8S8VWmQCDV6fP+L9kH5I2JhPR5M7CqQ/n9TW3d2m4P8l0s= test@server"

TEST_USER_DN = "uid=testuser,ou=people,dc=heracles,dc=local"
TEST_BASE_DN = "dc=heracles,dc=local"


# ============================================================================
# Helper class for LDAP entry mock
# ============================================================================

class MockLdapEntry:
    """Mock LDAP entry with dn attribute."""
    def __init__(self, entry_dict: dict):
        self.dn = entry_dict.get("dn", "")
        self._data = entry_dict
    
    def get(self, key, default=None):
        return self._data.get(key, default)
    
    def __getitem__(self, key):
        return self._data[key]


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_ldap_service():
    """Create mock LDAP service."""
    ldap = AsyncMock()
    ldap.base_dn = TEST_BASE_DN
    ldap.search = AsyncMock()
    ldap.get_by_dn = AsyncMock()
    ldap.modify = AsyncMock()
    return ldap


@pytest.fixture
def ssh_service(mock_ldap_service):
    """Create SSHService with mocked LDAP."""
    return SSHService(mock_ldap_service, config={})


@pytest.fixture
def user_without_ssh():
    """User entry without SSH enabled."""
    return {
        "dn": TEST_USER_DN,
        "uid": "testuser",
        "cn": "Test User",
        "objectClass": ["inetOrgPerson", "organizationalPerson", "person"],
    }


@pytest.fixture
def user_with_ssh():
    """User entry with SSH enabled."""
    return {
        "dn": TEST_USER_DN,
        "uid": "testuser",
        "cn": "Test User",
        "objectClass": ["inetOrgPerson", "organizationalPerson", "person", "ldapPublicKey"],
        "sshPublicKey": [VALID_ED25519_KEY],
    }


@pytest.fixture
def user_with_multiple_keys():
    """User entry with multiple SSH keys."""
    return {
        "dn": TEST_USER_DN,
        "uid": "testuser",
        "cn": "Test User",
        "objectClass": ["inetOrgPerson", "organizationalPerson", "person", "ldapPublicKey"],
        "sshPublicKey": [VALID_ED25519_KEY, VALID_RSA_KEY],
    }


# ============================================================================
# Test User SSH Status
# ============================================================================

class TestGetUserSSHStatus:
    """Tests for get_user_ssh_status method."""
    
    @pytest.mark.asyncio
    async def test_user_without_ssh(self, ssh_service, mock_ldap_service, user_without_ssh):
        """Should return hasSsh=False for user without ldapPublicKey."""
        mock_ldap_service.search.return_value = [MockLdapEntry(user_without_ssh)]
        mock_ldap_service.get_by_dn.return_value = user_without_ssh
        
        result = await ssh_service.get_user_ssh_status("testuser")
        
        assert result.uid == "testuser"
        assert result.has_ssh is False
        assert result.keys == []
        assert result.key_count == 0
    
    @pytest.mark.asyncio
    async def test_user_with_ssh_enabled(self, ssh_service, mock_ldap_service, user_with_ssh):
        """Should return hasSsh=True and keys for user with ldapPublicKey."""
        mock_ldap_service.search.return_value = [MockLdapEntry(user_with_ssh)]
        mock_ldap_service.get_by_dn.return_value = user_with_ssh
        
        result = await ssh_service.get_user_ssh_status("testuser")
        
        assert result.uid == "testuser"
        assert result.has_ssh is True
        assert result.key_count == 1
        assert len(result.keys) == 1
        assert result.keys[0].key_type == "ssh-ed25519"
        assert result.keys[0].comment == "user@host"
    
    @pytest.mark.asyncio
    async def test_user_with_multiple_keys(self, ssh_service, mock_ldap_service, user_with_multiple_keys):
        """Should return all keys for user with multiple SSH keys."""
        mock_ldap_service.search.return_value = [MockLdapEntry(user_with_multiple_keys)]
        mock_ldap_service.get_by_dn.return_value = user_with_multiple_keys
        
        result = await ssh_service.get_user_ssh_status("testuser")
        
        assert result.key_count == 2
        key_types = {k.key_type for k in result.keys}
        assert "ssh-ed25519" in key_types
        assert "ssh-rsa" in key_types
    
    @pytest.mark.asyncio
    async def test_user_not_found(self, ssh_service, mock_ldap_service):
        """Should raise error for non-existent user."""
        mock_ldap_service.search.return_value = []
        
        from heracles_api.services.ldap_service import LdapNotFoundError
        
        with pytest.raises(LdapNotFoundError):
            await ssh_service.get_user_ssh_status("nonexistent")


# ============================================================================
# Test Activate SSH
# ============================================================================

class TestActivateSSH:
    """Tests for activate_ssh method."""
    
    @pytest.mark.asyncio
    async def test_activate_ssh_success(self, ssh_service, mock_ldap_service, user_without_ssh):
        """Should add ldapPublicKey objectClass."""
        # First call returns user without SSH
        mock_ldap_service.search.return_value = [MockLdapEntry(user_without_ssh)]
        mock_ldap_service.get_by_dn.return_value = user_without_ssh
        mock_ldap_service.modify.return_value = True
        
        # After activation, return user with SSH
        user_activated = user_without_ssh.copy()
        user_activated["objectClass"] = user_without_ssh["objectClass"] + ["ldapPublicKey"]
        
        # Setup side effect to return different values
        mock_ldap_service.get_by_dn.side_effect = [user_without_ssh, user_activated]
        
        result = await ssh_service.activate_ssh("testuser")
        
        # Verify modify was called with correct parameters
        mock_ldap_service.modify.assert_called_once()
        call_args = mock_ldap_service.modify.call_args
        assert call_args[0][0] == TEST_USER_DN
        # Check that objectClass add was requested
        mods = call_args[0][1]
        assert "objectClass" in mods
        assert mods["objectClass"][0] == "add"
    
    @pytest.mark.asyncio
    async def test_activate_ssh_already_active(self, ssh_service, mock_ldap_service, user_with_ssh):
        """Should not modify if SSH already active."""
        mock_ldap_service.search.return_value = [MockLdapEntry(user_with_ssh)]
        mock_ldap_service.get_by_dn.return_value = user_with_ssh
        
        result = await ssh_service.activate_ssh("testuser")
        
        # modify should not be called
        mock_ldap_service.modify.assert_not_called()
        assert result.has_ssh is True
    
    @pytest.mark.asyncio
    async def test_activate_ssh_with_initial_key(self, ssh_service, mock_ldap_service, user_without_ssh):
        """Should add initial key when activating."""
        mock_ldap_service.search.return_value = [MockLdapEntry(user_without_ssh)]
        mock_ldap_service.get_by_dn.return_value = user_without_ssh
        mock_ldap_service.modify.return_value = True
        
        user_activated = user_without_ssh.copy()
        user_activated["objectClass"] = user_without_ssh["objectClass"] + ["ldapPublicKey"]
        user_activated["sshPublicKey"] = [VALID_ED25519_KEY]
        mock_ldap_service.get_by_dn.side_effect = [user_without_ssh, user_activated]
        
        data = UserSSHActivate(initial_key=VALID_ED25519_KEY)
        result = await ssh_service.activate_ssh("testuser", data)
        
        # Verify modify was called with key
        mock_ldap_service.modify.assert_called_once()
        call_args = mock_ldap_service.modify.call_args
        mods = call_args[0][1]
        assert "sshPublicKey" in mods


# ============================================================================
# Test Deactivate SSH
# ============================================================================

class TestDeactivateSSH:
    """Tests for deactivate_ssh method."""
    
    @pytest.mark.asyncio
    async def test_deactivate_ssh_success(self, ssh_service, mock_ldap_service, user_with_ssh):
        """Should remove ldapPublicKey objectClass and keys."""
        mock_ldap_service.search.return_value = [MockLdapEntry(user_with_ssh)]
        mock_ldap_service.get_by_dn.return_value = user_with_ssh
        mock_ldap_service.modify.return_value = True
        
        user_deactivated = user_with_ssh.copy()
        user_deactivated["objectClass"] = ["inetOrgPerson", "organizationalPerson", "person"]
        del user_deactivated["sshPublicKey"]
        mock_ldap_service.get_by_dn.side_effect = [user_with_ssh, user_deactivated]
        
        result = await ssh_service.deactivate_ssh("testuser")
        
        # Verify modify was called
        mock_ldap_service.modify.assert_called_once()
        call_args = mock_ldap_service.modify.call_args
        mods = call_args[0][1]
        assert "objectClass" in mods
        assert mods["objectClass"][0] == "delete"
    
    @pytest.mark.asyncio
    async def test_deactivate_ssh_already_inactive(self, ssh_service, mock_ldap_service, user_without_ssh):
        """Should not modify if SSH already inactive."""
        mock_ldap_service.search.return_value = [MockLdapEntry(user_without_ssh)]
        mock_ldap_service.get_by_dn.return_value = user_without_ssh
        
        result = await ssh_service.deactivate_ssh("testuser")
        
        mock_ldap_service.modify.assert_not_called()
        assert result.has_ssh is False


# ============================================================================
# Test Add Key
# ============================================================================

class TestAddKey:
    """Tests for add_key method."""
    
    @pytest.mark.asyncio
    async def test_add_key_success(self, ssh_service, mock_ldap_service, user_with_ssh):
        """Should add new SSH key."""
        mock_ldap_service.search.return_value = [MockLdapEntry(user_with_ssh)]
        mock_ldap_service.get_by_dn.return_value = user_with_ssh
        mock_ldap_service.modify.return_value = True
        
        user_updated = user_with_ssh.copy()
        user_updated["sshPublicKey"] = [VALID_ED25519_KEY, VALID_RSA_KEY]
        mock_ldap_service.get_by_dn.side_effect = [user_with_ssh, user_updated]
        
        data = SSHKeyCreate(key=VALID_RSA_KEY)
        result = await ssh_service.add_key("testuser", data)
        
        mock_ldap_service.modify.assert_called_once()
        call_args = mock_ldap_service.modify.call_args
        mods = call_args[0][1]
        assert "sshPublicKey" in mods
        assert mods["sshPublicKey"][0] == "add"
    
    @pytest.mark.asyncio
    async def test_add_key_ssh_not_enabled(self, ssh_service, mock_ldap_service, user_without_ssh):
        """Should activate SSH first if not enabled."""
        mock_ldap_service.search.return_value = [MockLdapEntry(user_without_ssh)]
        mock_ldap_service.get_by_dn.return_value = user_without_ssh
        mock_ldap_service.modify.return_value = True
        
        # After activation
        user_activated = user_without_ssh.copy()
        user_activated["objectClass"] = user_without_ssh["objectClass"] + ["ldapPublicKey"]
        user_activated["sshPublicKey"] = [VALID_ED25519_KEY]
        mock_ldap_service.get_by_dn.side_effect = [user_without_ssh, user_activated, user_activated]
        
        data = SSHKeyCreate(key=VALID_ED25519_KEY)
        result = await ssh_service.add_key("testuser", data)
        
        # Should have called modify at least once (for activation)
        assert mock_ldap_service.modify.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_add_duplicate_key(self, ssh_service, mock_ldap_service, user_with_ssh):
        """Should raise error for duplicate key."""
        mock_ldap_service.search.return_value = [MockLdapEntry(user_with_ssh)]
        mock_ldap_service.get_by_dn.return_value = user_with_ssh
        
        # Try to add the same key that already exists
        data = SSHKeyCreate(key=VALID_ED25519_KEY)
        
        with pytest.raises(ValueError, match="already exists"):
            await ssh_service.add_key("testuser", data)
    
    @pytest.mark.asyncio
    async def test_add_invalid_key(self, ssh_service, mock_ldap_service, user_with_ssh):
        """Should raise error for invalid key format."""
        mock_ldap_service.search.return_value = [MockLdapEntry(user_with_ssh)]
        mock_ldap_service.get_by_dn.return_value = user_with_ssh
        
        # SSHKeyCreate validates key format, so we expect validation error
        with pytest.raises(Exception):  # Pydantic ValidationError
            data = SSHKeyCreate(key="invalid-key-format")
            await ssh_service.add_key("testuser", data)


# ============================================================================
# Test Remove Key
# ============================================================================

class TestRemoveKey:
    """Tests for remove_key method."""
    
    @pytest.mark.asyncio
    async def test_remove_key_success(self, ssh_service, mock_ldap_service, user_with_ssh):
        """Should remove SSH key by fingerprint."""
        mock_ldap_service.search.return_value = [MockLdapEntry(user_with_ssh)]
        mock_ldap_service.get_by_dn.return_value = user_with_ssh
        mock_ldap_service.modify.return_value = True
        
        user_updated = user_with_ssh.copy()
        user_updated["sshPublicKey"] = []
        mock_ldap_service.get_by_dn.side_effect = [user_with_ssh, user_updated]
        
        # Get fingerprint of existing key
        from heracles_plugins.ssh.schemas import parse_ssh_key
        key_info = parse_ssh_key(VALID_ED25519_KEY)
        fingerprint = key_info["fingerprint"]
        
        result = await ssh_service.remove_key("testuser", fingerprint)
        
        mock_ldap_service.modify.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_remove_key_not_found(self, ssh_service, mock_ldap_service, user_with_ssh):
        """Should raise error for non-existent fingerprint."""
        mock_ldap_service.search.return_value = [MockLdapEntry(user_with_ssh)]
        mock_ldap_service.get_by_dn.return_value = user_with_ssh
        
        from heracles_api.services.ldap_service import LdapNotFoundError
        
        with pytest.raises(LdapNotFoundError):
            await ssh_service.remove_key("testuser", "SHA256:nonexistent")


# ============================================================================
# Test Update Keys
# ============================================================================

class TestUpdateKeys:
    """Tests for update_keys method."""
    
    @pytest.mark.asyncio
    async def test_update_keys_replace_all(self, ssh_service, mock_ldap_service, user_with_ssh):
        """Should replace all SSH keys."""
        mock_ldap_service.search.return_value = [MockLdapEntry(user_with_ssh)]
        mock_ldap_service.get_by_dn.return_value = user_with_ssh
        mock_ldap_service.modify.return_value = True
        
        new_keys = [VALID_RSA_KEY, VALID_ECDSA_KEY]
        user_updated = user_with_ssh.copy()
        user_updated["sshPublicKey"] = new_keys
        mock_ldap_service.get_by_dn.side_effect = [user_with_ssh, user_updated]
        
        data = UserSSHKeysUpdate(keys=new_keys)
        result = await ssh_service.update_keys("testuser", data)
        
        mock_ldap_service.modify.assert_called_once()
        call_args = mock_ldap_service.modify.call_args
        mods = call_args[0][1]
        assert "sshPublicKey" in mods
        assert mods["sshPublicKey"][0] == "replace"
    
    @pytest.mark.asyncio
    async def test_update_keys_empty_deletes(self, ssh_service, mock_ldap_service, user_with_ssh):
        """Should delete all keys when empty list provided."""
        mock_ldap_service.search.return_value = [MockLdapEntry(user_with_ssh)]
        mock_ldap_service.get_by_dn.return_value = user_with_ssh
        mock_ldap_service.modify.return_value = True
        
        user_updated = user_with_ssh.copy()
        user_updated["sshPublicKey"] = []
        mock_ldap_service.get_by_dn.side_effect = [user_with_ssh, user_updated]
        
        data = UserSSHKeysUpdate(keys=[])
        result = await ssh_service.update_keys("testuser", data)
        
        mock_ldap_service.modify.assert_called_once()
        call_args = mock_ldap_service.modify.call_args
        mods = call_args[0][1]
        assert "sshPublicKey" in mods
        assert mods["sshPublicKey"][0] == "delete"


# ============================================================================
# Test TabService Interface Methods
# ============================================================================

class TestTabServiceInterface:
    """Tests for TabService abstract methods."""
    
    @pytest.fixture
    def user_dn(self):
        """User DN for TabService interface tests."""
        return "uid=testuser,ou=users,dc=example,dc=com"
    
    @pytest.mark.asyncio
    async def test_is_active(self, ssh_service, mock_ldap_service, user_with_ssh, user_without_ssh, user_dn):
        """Test is_active returns correct status."""
        mock_ldap_service.search.return_value = [MockLdapEntry(user_with_ssh)]
        mock_ldap_service.get_by_dn.return_value = user_with_ssh
        
        result = await ssh_service.is_active(user_dn)
        assert result is True
        
        mock_ldap_service.search.return_value = [MockLdapEntry(user_without_ssh)]
        mock_ldap_service.get_by_dn.return_value = user_without_ssh
        
        result = await ssh_service.is_active(user_dn)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_read(self, ssh_service, mock_ldap_service, user_with_ssh, user_dn):
        """Test read returns user status dict."""
        mock_ldap_service.search.return_value = [MockLdapEntry(user_with_ssh)]
        mock_ldap_service.get_by_dn.return_value = user_with_ssh
        
        result = await ssh_service.read(user_dn)
        
        assert result is not None
        assert result.uid == "testuser"
        assert result.has_ssh is True
    
    @pytest.mark.asyncio
    async def test_activate(self, ssh_service, mock_ldap_service, user_without_ssh, user_dn):
        """Test activate enables SSH."""
        mock_ldap_service.search.return_value = [MockLdapEntry(user_without_ssh)]
        mock_ldap_service.get_by_dn.return_value = user_without_ssh
        mock_ldap_service.modify.return_value = True
        
        user_activated = user_without_ssh.copy()
        user_activated["objectClass"] = user_without_ssh["objectClass"] + ["ldapPublicKey"]
        mock_ldap_service.get_by_dn.side_effect = [user_without_ssh, user_activated]
        
        result = await ssh_service.activate(user_dn)
        
        assert result is not None
        assert result.has_ssh is True
    
    @pytest.mark.asyncio
    async def test_deactivate(self, ssh_service, mock_ldap_service, user_with_ssh, user_dn):
        """Test deactivate disables SSH."""
        mock_ldap_service.search.return_value = [MockLdapEntry(user_with_ssh)]
        mock_ldap_service.get_by_dn.return_value = user_with_ssh
        mock_ldap_service.modify.return_value = True
        
        user_deactivated = user_with_ssh.copy()
        user_deactivated["objectClass"] = ["inetOrgPerson", "organizationalPerson", "person"]
        mock_ldap_service.get_by_dn.side_effect = [user_with_ssh, user_deactivated]
        
        result = await ssh_service.deactivate(user_dn)
        
        assert result is True
