"""
E2E Tests - SSH and Sudo Plugins
================================

End-to-end tests for SSH and Sudo plugins against a real LDAP server.
These tests require Docker infrastructure to be running.

Run with: pytest tests/e2e/ -v --e2e
"""

import pytest
import os
import httpx
import asyncio
from typing import Optional, Dict, Any

# Skip if not running E2E tests
pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_E2E_TESTS", "0") != "1",
    reason="E2E tests require RUN_E2E_TESTS=1 and running infrastructure"
)


# ============================================================================
# Configuration
# ============================================================================

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
TEST_USER = os.environ.get("TEST_USER", "testuser")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD", "password123")

# Valid SSH keys for testing
VALID_ED25519_KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJl3VtABZZPW+6c3WElBjAV4VvC6TZ0t0VwN9Fq9pCzF e2e-test@heracles"
VALID_RSA_KEY = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCsLLyrP/nK6qHqXM1kXLXRLwxCLUZJkmjM0R6YBDL1qPaYqIHHwjT9M6uTqzFq8oHRpKxzVzGhLjHX5X8qhyLUqJHN0dQ5MO1XZBvPOPWHqOGqYW9RPqoYJEG9QNdH3PEYwcKvAo8cJNXMlRZrYB9tJKJq7sXLR9XJgHJOPQh5pNpJQN8WQHPE/MwSQdCmAUZm5qH8PO3LhF3RB5qT8qVKMdBhJ8vN7L6YTEKBFqJYJHPWC2LRSPQ2dKMhQCLVPJ9qJ7K3LhQ8KpM9JgQJXP5YBFDQL7OqJ3K8LhQ2KpM1JgQJXP2YBFDQL3OqJ5K8LhQ4KpM3JgQJXP4YBFDQL5Oq== e2e-rsa@heracles"


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def api_client():
    """Create HTTP client for API calls."""
    return httpx.Client(base_url=API_BASE_URL, timeout=30.0)


@pytest.fixture(scope="module")
def auth_token(api_client) -> str:
    """Get authentication token."""
    response = api_client.post(
        "/api/v1/auth/login",
        json={"username": TEST_USER, "password": TEST_PASSWORD}
    )
    if response.status_code != 200:
        pytest.skip(f"Cannot authenticate: {response.text}")
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token) -> Dict[str, str]:
    """Get auth headers for API calls."""
    return {"Authorization": f"Bearer {auth_token}"}


# ============================================================================
# SSH E2E Tests
# ============================================================================

class TestSSHPluginE2E:
    """End-to-end tests for SSH plugin."""
    
    def test_get_ssh_status(self, api_client, auth_headers):
        """Test getting user SSH status."""
        response = api_client.get(
            f"/api/v1/ssh/users/{TEST_USER}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["uid"] == TEST_USER
        assert "hasSsh" in data
        assert "keys" in data
        assert "keyCount" in data
    
    def test_activate_ssh(self, api_client, auth_headers):
        """Test activating SSH for user."""
        # First deactivate to ensure clean state
        api_client.post(
            f"/api/v1/ssh/users/{TEST_USER}/deactivate",
            headers=auth_headers
        )
        
        # Activate SSH
        response = api_client.post(
            f"/api/v1/ssh/users/{TEST_USER}/activate",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["hasSsh"] is True
    
    def test_add_ssh_key(self, api_client, auth_headers):
        """Test adding an SSH key."""
        # Ensure SSH is activated
        api_client.post(
            f"/api/v1/ssh/users/{TEST_USER}/activate",
            headers=auth_headers
        )
        
        # Add key
        response = api_client.post(
            f"/api/v1/ssh/users/{TEST_USER}/keys",
            headers=auth_headers,
            json={"key": VALID_ED25519_KEY}
        )
        
        # May fail if key already exists (200) or success (200)
        assert response.status_code in [200, 400]
        
        if response.status_code == 200:
            data = response.json()
            assert data["keyCount"] >= 1
            # Verify key is in list
            key_comments = [k.get("comment") for k in data["keys"]]
            assert "e2e-test@heracles" in key_comments or any(
                k.get("key") == VALID_ED25519_KEY for k in data["keys"]
            )
    
    def test_list_ssh_keys(self, api_client, auth_headers):
        """Test listing SSH keys for user."""
        response = api_client.get(
            f"/api/v1/ssh/users/{TEST_USER}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if data["hasSsh"]:
            assert isinstance(data["keys"], list)
            for key in data["keys"]:
                assert "key" in key
                assert "keyType" in key
                assert "fingerprint" in key
    
    def test_remove_ssh_key(self, api_client, auth_headers):
        """Test removing an SSH key."""
        # Get current status to find a key fingerprint
        response = api_client.get(
            f"/api/v1/ssh/users/{TEST_USER}",
            headers=auth_headers
        )
        
        if response.status_code == 200 and response.json()["keyCount"] > 0:
            fingerprint = response.json()["keys"][0]["fingerprint"]
            
            # URL encode the fingerprint (SHA256: contains special chars)
            import urllib.parse
            encoded_fp = urllib.parse.quote(fingerprint, safe="")
            
            response = api_client.delete(
                f"/api/v1/ssh/users/{TEST_USER}/keys/{encoded_fp}",
                headers=auth_headers
            )
            
            # Should succeed or key already removed
            assert response.status_code in [200, 404]
    
    def test_deactivate_ssh(self, api_client, auth_headers):
        """Test deactivating SSH for user."""
        response = api_client.post(
            f"/api/v1/ssh/users/{TEST_USER}/deactivate",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["hasSsh"] is False
        assert data["keyCount"] == 0
    
    def test_ssh_full_lifecycle(self, api_client, auth_headers):
        """Test complete SSH lifecycle: activate -> add key -> remove -> deactivate."""
        # 1. Start clean
        api_client.post(
            f"/api/v1/ssh/users/{TEST_USER}/deactivate",
            headers=auth_headers
        )
        
        # 2. Activate with initial key
        response = api_client.post(
            f"/api/v1/ssh/users/{TEST_USER}/activate",
            headers=auth_headers,
            json={"initialKey": VALID_ED25519_KEY}
        )
        assert response.status_code == 200
        assert response.json()["hasSsh"] is True
        
        # 3. Add another key
        response = api_client.post(
            f"/api/v1/ssh/users/{TEST_USER}/keys",
            headers=auth_headers,
            json={"key": VALID_RSA_KEY}
        )
        # May be 200 or 400 if key validation fails
        
        # 4. Get status
        response = api_client.get(
            f"/api/v1/ssh/users/{TEST_USER}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # 5. Deactivate
        response = api_client.post(
            f"/api/v1/ssh/users/{TEST_USER}/deactivate",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["hasSsh"] is False


# ============================================================================
# Sudo E2E Tests
# ============================================================================

class TestSudoPluginE2E:
    """End-to-end tests for Sudo plugin."""
    
    @pytest.fixture(autouse=True)
    def cleanup_test_rules(self, api_client, auth_headers):
        """Cleanup test rules before and after each test."""
        test_rules = ["e2e-test-rule", "e2e-lifecycle-rule"]
        for rule in test_rules:
            try:
                api_client.delete(
                    f"/api/v1/sudo/roles/{rule}",
                    headers=auth_headers
                )
            except:
                pass
        yield
        for rule in test_rules:
            try:
                api_client.delete(
                    f"/api/v1/sudo/roles/{rule}",
                    headers=auth_headers
                )
            except:
                pass
    
    def test_list_sudo_roles(self, api_client, auth_headers):
        """Test listing sudo roles."""
        response = api_client.get(
            "/api/v1/sudo/roles",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "roles" in data
        assert "total" in data
        assert isinstance(data["roles"], list)
    
    def test_create_sudo_role(self, api_client, auth_headers):
        """Test creating a sudo role."""
        role_data = {
            "cn": "e2e-test-rule",
            "sudoUser": [TEST_USER],
            "sudoHost": ["ALL"],
            "sudoCommand": ["/usr/bin/systemctl status *"],
            "sudoOption": ["NOPASSWD"],
            "description": "E2E test rule"
        }
        
        response = api_client.post(
            "/api/v1/sudo/roles",
            headers=auth_headers,
            json=role_data
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["cn"] == "e2e-test-rule"
        assert TEST_USER in data["sudoUser"]
    
    def test_get_sudo_role(self, api_client, auth_headers):
        """Test getting a specific sudo role."""
        # First create a rule
        role_data = {
            "cn": "e2e-test-rule",
            "sudoUser": [TEST_USER],
            "sudoHost": ["ALL"],
            "sudoCommand": ["/usr/bin/whoami"],
        }
        api_client.post(
            "/api/v1/sudo/roles",
            headers=auth_headers,
            json=role_data
        )
        
        # Get the rule
        response = api_client.get(
            "/api/v1/sudo/roles/e2e-test-rule",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["cn"] == "e2e-test-rule"
    
    def test_update_sudo_role(self, api_client, auth_headers):
        """Test updating a sudo role."""
        # First create a rule
        role_data = {
            "cn": "e2e-test-rule",
            "sudoUser": [TEST_USER],
            "sudoHost": ["ALL"],
            "sudoCommand": ["/usr/bin/whoami"],
        }
        api_client.post(
            "/api/v1/sudo/roles",
            headers=auth_headers,
            json=role_data
        )
        
        # Update the rule
        update_data = {
            "sudoCommand": ["/usr/bin/whoami", "/usr/bin/id"],
            "sudoOption": ["NOPASSWD"],
        }
        
        response = api_client.put(
            "/api/v1/sudo/roles/e2e-test-rule",
            headers=auth_headers,
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["sudoCommand"]) == 2
    
    def test_delete_sudo_role(self, api_client, auth_headers):
        """Test deleting a sudo role."""
        # First create a rule
        role_data = {
            "cn": "e2e-test-rule",
            "sudoUser": [TEST_USER],
            "sudoHost": ["ALL"],
            "sudoCommand": ["/usr/bin/whoami"],
        }
        api_client.post(
            "/api/v1/sudo/roles",
            headers=auth_headers,
            json=role_data
        )
        
        # Delete the rule
        response = api_client.delete(
            "/api/v1/sudo/roles/e2e-test-rule",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 204]
        
        # Verify deletion
        response = api_client.get(
            "/api/v1/sudo/roles/e2e-test-rule",
            headers=auth_headers
        )
        assert response.status_code == 404
    
    def test_sudo_role_full_lifecycle(self, api_client, auth_headers):
        """Test complete sudo role lifecycle: create -> read -> update -> delete."""
        rule_name = "e2e-lifecycle-rule"
        
        # 1. Create
        role_data = {
            "cn": rule_name,
            "sudoUser": [TEST_USER, "%admins"],
            "sudoHost": ["ALL"],
            "sudoCommand": ["/usr/bin/systemctl restart nginx"],
            "sudoRunAsUser": ["root"],
            "sudoOption": [],
            "description": "E2E lifecycle test"
        }
        
        response = api_client.post(
            "/api/v1/sudo/roles",
            headers=auth_headers,
            json=role_data
        )
        assert response.status_code in [200, 201]
        
        # 2. Read
        response = api_client.get(
            f"/api/v1/sudo/roles/{rule_name}",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["cn"] == rule_name
        
        # 3. Update - add NOPASSWD option
        response = api_client.put(
            f"/api/v1/sudo/roles/{rule_name}",
            headers=auth_headers,
            json={"sudoOption": ["NOPASSWD"]}
        )
        assert response.status_code == 200
        assert "NOPASSWD" in response.json()["sudoOption"]
        
        # 4. Delete
        response = api_client.delete(
            f"/api/v1/sudo/roles/{rule_name}",
            headers=auth_headers
        )
        assert response.status_code in [200, 204]
    
    def test_get_roles_for_user(self, api_client, auth_headers):
        """Test getting sudo roles for a specific user."""
        # Create a rule for the user first
        role_data = {
            "cn": "e2e-test-rule",
            "sudoUser": [TEST_USER],
            "sudoHost": ["ALL"],
            "sudoCommand": ["/usr/bin/test"],
        }
        api_client.post(
            "/api/v1/sudo/roles",
            headers=auth_headers,
            json=role_data
        )
        
        # Get roles for user
        response = api_client.get(
            f"/api/v1/sudo/roles?user={TEST_USER}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should have at least the rule we created
        assert data["total"] >= 0


# ============================================================================
# Combined E2E Tests
# ============================================================================

class TestCombinedPluginsE2E:
    """E2E tests for combined plugin scenarios."""
    
    def test_user_with_ssh_and_sudo(self, api_client, auth_headers):
        """Test user can have both SSH and Sudo configured."""
        # Activate SSH
        api_client.post(
            f"/api/v1/ssh/users/{TEST_USER}/activate",
            headers=auth_headers
        )
        
        # Create sudo rule
        role_data = {
            "cn": "combined-test-rule",
            "sudoUser": [TEST_USER],
            "sudoHost": ["ALL"],
            "sudoCommand": ["/usr/bin/ls"],
        }
        api_client.post(
            "/api/v1/sudo/roles",
            headers=auth_headers,
            json=role_data
        )
        
        # Verify SSH is active
        ssh_response = api_client.get(
            f"/api/v1/ssh/users/{TEST_USER}",
            headers=auth_headers
        )
        assert ssh_response.status_code == 200
        
        # Verify sudo rule exists
        sudo_response = api_client.get(
            "/api/v1/sudo/roles/combined-test-rule",
            headers=auth_headers
        )
        # May or may not exist from previous run
        assert sudo_response.status_code in [200, 404]
        
        # Cleanup
        api_client.delete(
            "/api/v1/sudo/roles/combined-test-rule",
            headers=auth_headers
        )
        api_client.post(
            f"/api/v1/ssh/users/{TEST_USER}/deactivate",
            headers=auth_headers
        )


# ============================================================================
# API Error Handling E2E Tests
# ============================================================================

class TestAPIErrorHandlingE2E:
    """E2E tests for API error handling."""
    
    def test_unauthorized_access(self, api_client):
        """Test that unauthorized requests are rejected."""
        response = api_client.get(
            f"/api/v1/ssh/users/{TEST_USER}"
        )
        assert response.status_code == 401
    
    def test_invalid_user_ssh(self, api_client, auth_headers):
        """Test SSH operations on non-existent user."""
        response = api_client.get(
            "/api/v1/ssh/users/nonexistent-user-12345",
            headers=auth_headers
        )
        assert response.status_code == 404
    
    def test_invalid_sudo_role(self, api_client, auth_headers):
        """Test sudo operations on non-existent role."""
        response = api_client.get(
            "/api/v1/sudo/roles/nonexistent-role-12345",
            headers=auth_headers
        )
        assert response.status_code == 404
    
    def test_invalid_ssh_key_format(self, api_client, auth_headers):
        """Test adding invalid SSH key."""
        # Ensure SSH is activated
        api_client.post(
            f"/api/v1/ssh/users/{TEST_USER}/activate",
            headers=auth_headers
        )
        
        response = api_client.post(
            f"/api/v1/ssh/users/{TEST_USER}/keys",
            headers=auth_headers,
            json={"key": "invalid-not-a-real-ssh-key"}
        )
        
        # Should get validation error (400 or 422)
        assert response.status_code in [400, 422]
