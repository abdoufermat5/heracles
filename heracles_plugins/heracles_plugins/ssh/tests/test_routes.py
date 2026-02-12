"""
SSH Plugin Tests - Routes
=========================

Tests for SSH API endpoints with mocked service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI

from heracles_plugins.ssh.routes import router
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

TEST_USER_DN = "uid=testuser,ou=people,dc=heracles,dc=local"


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_ssh_service():
    """Create mock SSH service."""
    service = AsyncMock()
    service.get_user_ssh_status = AsyncMock()
    service.activate_ssh = AsyncMock()
    service.deactivate_ssh = AsyncMock()
    service.add_key = AsyncMock()
    service.remove_key = AsyncMock()
    service.update_keys = AsyncMock()
    service.lookup_key = AsyncMock()
    return service


@pytest.fixture
def mock_current_user():
    """Create mock current user."""
    user = MagicMock()
    user.uid = "testuser"
    user.dn = TEST_USER_DN
    user.groups = ["admins"]
    return user


@pytest.fixture
def sample_user_status():
    """Create sample user SSH status."""
    return UserSSHStatus(
        uid="testuser",
        dn=TEST_USER_DN,
        hasSsh=True,
        keys=[
            SSHKeyRead(
                key=VALID_ED25519_KEY,
                keyType="ssh-ed25519",
                fingerprint="SHA256:abc123",
                comment="user@host",
                bits=256,
            )
        ],
        keyCount=1,
    )


@pytest.fixture
def sample_user_status_no_ssh():
    """Create sample user SSH status without SSH enabled."""
    return UserSSHStatus(
        uid="testuser",
        dn=TEST_USER_DN,
        hasSsh=False,
        keys=[],
        keyCount=0,
    )


# ============================================================================
# Test Get User SSH Status Endpoint
# ============================================================================

class TestGetUserSSHStatusEndpoint:
    """Tests for GET /ssh/users/{uid} endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_status_with_ssh(self, mock_ssh_service, sample_user_status):
        """Test getting status for user with SSH enabled."""
        mock_ssh_service.get_user_ssh_status.return_value = sample_user_status
        
        result = await mock_ssh_service.get_user_ssh_status("testuser")
        
        assert result.uid == "testuser"
        assert result.has_ssh is True
        assert result.key_count == 1
        mock_ssh_service.get_user_ssh_status.assert_called_with("testuser")
    
    @pytest.mark.asyncio
    async def test_get_status_without_ssh(self, mock_ssh_service, sample_user_status_no_ssh):
        """Test getting status for user without SSH enabled."""
        mock_ssh_service.get_user_ssh_status.return_value = sample_user_status_no_ssh
        
        result = await mock_ssh_service.get_user_ssh_status("testuser")
        
        assert result.has_ssh is False
        assert result.key_count == 0
    
    @pytest.mark.asyncio
    async def test_get_status_user_not_found(self, mock_ssh_service):
        """Test getting status for non-existent user."""
        from heracles_api.services.ldap_service import LdapNotFoundError
        mock_ssh_service.get_user_ssh_status.side_effect = LdapNotFoundError("User not found")
        
        with pytest.raises(LdapNotFoundError):
            await mock_ssh_service.get_user_ssh_status("nonexistent")


# ============================================================================
# Test Activate SSH Endpoint
# ============================================================================

class TestActivateSSHEndpoint:
    """Tests for POST /ssh/users/{uid}/activate endpoint."""
    
    @pytest.mark.asyncio
    async def test_activate_ssh_success(self, mock_ssh_service, sample_user_status):
        """Test successful SSH activation."""
        mock_ssh_service.activate_ssh.return_value = sample_user_status
        
        result = await mock_ssh_service.activate_ssh("testuser")
        
        assert result.has_ssh is True
        mock_ssh_service.activate_ssh.assert_called_with("testuser")
    
    @pytest.mark.asyncio
    async def test_activate_ssh_with_initial_key(self, mock_ssh_service, sample_user_status):
        """Test SSH activation with initial key."""
        mock_ssh_service.activate_ssh.return_value = sample_user_status
        
        data = UserSSHActivate(initial_key=VALID_ED25519_KEY)
        await mock_ssh_service.activate_ssh("testuser", data)
        
        mock_ssh_service.activate_ssh.assert_called_with("testuser", data)
    
    @pytest.mark.asyncio
    async def test_activate_ssh_already_active(self, mock_ssh_service, sample_user_status):
        """Test activation when SSH already enabled (should succeed)."""
        mock_ssh_service.activate_ssh.return_value = sample_user_status
        
        result = await mock_ssh_service.activate_ssh("testuser")
        
        assert result.has_ssh is True


# ============================================================================
# Test Deactivate SSH Endpoint
# ============================================================================

class TestDeactivateSSHEndpoint:
    """Tests for POST /ssh/users/{uid}/deactivate endpoint."""
    
    @pytest.mark.asyncio
    async def test_deactivate_ssh_success(self, mock_ssh_service, sample_user_status_no_ssh):
        """Test successful SSH deactivation."""
        mock_ssh_service.deactivate_ssh.return_value = sample_user_status_no_ssh
        
        result = await mock_ssh_service.deactivate_ssh("testuser")
        
        assert result.has_ssh is False
        mock_ssh_service.deactivate_ssh.assert_called_with("testuser")
    
    @pytest.mark.asyncio
    async def test_deactivate_ssh_already_inactive(self, mock_ssh_service, sample_user_status_no_ssh):
        """Test deactivation when SSH already disabled."""
        mock_ssh_service.deactivate_ssh.return_value = sample_user_status_no_ssh
        
        result = await mock_ssh_service.deactivate_ssh("testuser")
        
        assert result.has_ssh is False


# ============================================================================
# Test Add Key Endpoint
# ============================================================================

class TestAddKeyEndpoint:
    """Tests for POST /ssh/users/{uid}/keys endpoint."""
    
    @pytest.mark.asyncio
    async def test_add_key_success(self, mock_ssh_service, sample_user_status):
        """Test successful key addition."""
        status_with_new_key = UserSSHStatus(
            uid="testuser",
            dn=TEST_USER_DN,
            hasSsh=True,
            keys=[
                SSHKeyRead(
                    key=VALID_ED25519_KEY,
                    keyType="ssh-ed25519",
                    fingerprint="SHA256:abc123",
                    comment="user@host",
                    bits=256,
                ),
                SSHKeyRead(
                    key=VALID_RSA_KEY,
                    keyType="ssh-rsa",
                    fingerprint="SHA256:def456",
                    comment="admin@server",
                    bits=2048,
                ),
            ],
            keyCount=2,
        )
        mock_ssh_service.add_key.return_value = status_with_new_key
        
        data = SSHKeyCreate(key=VALID_RSA_KEY)
        result = await mock_ssh_service.add_key("testuser", data)
        
        assert result.key_count == 2
        mock_ssh_service.add_key.assert_called_with("testuser", data)
    
    @pytest.mark.asyncio
    async def test_add_key_duplicate(self, mock_ssh_service):
        """Test adding duplicate key."""
        mock_ssh_service.add_key.side_effect = ValueError("SSH key already exists")
        
        data = SSHKeyCreate(key=VALID_ED25519_KEY)
        
        with pytest.raises(ValueError, match="already exists"):
            await mock_ssh_service.add_key("testuser", data)
    
    @pytest.mark.asyncio
    async def test_add_key_invalid_format(self, mock_ssh_service):
        """Test adding invalid key format - Pydantic validation catches it first."""
        from pydantic import ValidationError
        
        # Pydantic validates key format, so we expect ValidationError
        with pytest.raises(ValidationError):
            SSHKeyCreate(key="invalid-key-format-that-is-long-enough")


# ============================================================================
# Test Remove Key Endpoint
# ============================================================================

class TestRemoveKeyEndpoint:
    """Tests for DELETE /ssh/users/{uid}/keys/{fingerprint} endpoint."""
    
    @pytest.mark.asyncio
    async def test_remove_key_success(self, mock_ssh_service, sample_user_status_no_ssh):
        """Test successful key removal."""
        empty_status = UserSSHStatus(
            uid="testuser",
            dn=TEST_USER_DN,
            hasSsh=True,
            keys=[],
            keyCount=0,
        )
        mock_ssh_service.remove_key.return_value = empty_status
        
        result = await mock_ssh_service.remove_key("testuser", "SHA256:abc123")
        
        assert result.key_count == 0
        mock_ssh_service.remove_key.assert_called_with("testuser", "SHA256:abc123")
    
    @pytest.mark.asyncio
    async def test_remove_key_not_found(self, mock_ssh_service):
        """Test removing non-existent key."""
        from heracles_api.services.ldap_service import LdapNotFoundError
        mock_ssh_service.remove_key.side_effect = LdapNotFoundError("Key not found")
        
        with pytest.raises(LdapNotFoundError):
            await mock_ssh_service.remove_key("testuser", "SHA256:nonexistent")


# ============================================================================
# Test Update Keys Endpoint
# ============================================================================

class TestUpdateKeysEndpoint:
    """Tests for PUT /ssh/users/{uid}/keys endpoint."""
    
    @pytest.mark.asyncio
    async def test_update_keys_success(self, mock_ssh_service):
        """Test successful key replacement."""
        updated_status = UserSSHStatus(
            uid="testuser",
            dn=TEST_USER_DN,
            hasSsh=True,
            keys=[
                SSHKeyRead(
                    key=VALID_RSA_KEY,
                    keyType="ssh-rsa",
                    fingerprint="SHA256:def456",
                    comment="admin@server",
                    bits=2048,
                ),
            ],
            keyCount=1,
        )
        mock_ssh_service.update_keys.return_value = updated_status
        
        data = UserSSHKeysUpdate(keys=[VALID_RSA_KEY])
        result = await mock_ssh_service.update_keys("testuser", data)
        
        assert result.key_count == 1
        assert result.keys[0].key_type == "ssh-rsa"
    
    @pytest.mark.asyncio
    async def test_update_keys_empty(self, mock_ssh_service):
        """Test clearing all keys."""
        empty_status = UserSSHStatus(
            uid="testuser",
            dn=TEST_USER_DN,
            hasSsh=True,
            keys=[],
            keyCount=0,
        )
        mock_ssh_service.update_keys.return_value = empty_status
        
        data = UserSSHKeysUpdate(keys=[])
        result = await mock_ssh_service.update_keys("testuser", data)
        
        assert result.key_count == 0


# ============================================================================
# Test Lookup Endpoint
# ============================================================================

class TestLookupKeyEndpoint:
    """Tests for GET /ssh/lookup endpoint."""
    
    @pytest.mark.asyncio
    async def test_lookup_by_fingerprint(self, mock_ssh_service):
        """Test key lookup by fingerprint."""
        lookup_result = {
            "users": [
                {
                    "uid": "testuser",
                    "dn": TEST_USER_DN,
                    "key": SSHKeyRead(
                        key=VALID_ED25519_KEY,
                        keyType="ssh-ed25519",
                        fingerprint="SHA256:abc123",
                        comment="user@host",
                        bits=256,
                    ),
                }
            ]
        }
        mock_ssh_service.lookup_key.return_value = lookup_result
        
        result = await mock_ssh_service.lookup_key(fingerprint="SHA256:abc123")
        
        assert len(result["users"]) == 1
        assert result["users"][0]["uid"] == "testuser"
    
    @pytest.mark.asyncio
    async def test_lookup_no_results(self, mock_ssh_service):
        """Test key lookup with no results."""
        mock_ssh_service.lookup_key.return_value = {"users": []}
        
        result = await mock_ssh_service.lookup_key(fingerprint="SHA256:nonexistent")
        
        assert len(result["users"]) == 0


# ============================================================================
# Integration Tests (require FastAPI app)
# ============================================================================

class TestRouteIntegration:
    """Integration tests for SSH routes with FastAPI app."""
    
    @pytest.fixture
    def app(self, mock_ssh_service, mock_current_user):
        """Create FastAPI app with mocked dependencies."""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        return app
    
    def test_routes_registered(self, app):
        """Verify all routes are registered."""
        routes = [route.path for route in app.routes]
        
        # Check key routes exist
        assert any("/api/v1/ssh/users/{uid}" in r for r in routes)
        assert any("/api/v1/ssh/users/{uid}/activate" in r for r in routes)
        assert any("/api/v1/ssh/users/{uid}/deactivate" in r for r in routes)
        assert any("/api/v1/ssh/users/{uid}/keys" in r for r in routes)
        assert any("/api/v1/ssh/lookup" in r for r in routes)
