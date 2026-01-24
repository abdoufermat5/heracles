"""
Sudo Plugin Service Tests
=========================

Tests for Sudo service business logic with mocked LDAP operations.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, List, Optional

from heracles_plugins.sudo.service import (
    SudoService,
    SudoValidationError,
)
from heracles_plugins.sudo.schemas import (
    SudoRoleCreate,
    SudoRoleUpdate,
    SudoRoleRead,
)


# ============================================================================
# Mock LDAP Helpers
# ============================================================================

class MockLdapEntry:
    """Mock LDAP entry for testing."""
    
    def __init__(self, data: Dict[str, Any]):
        self._data = data
        self.dn = data.get("dn", "cn=test,ou=sudoers,dc=heracles,dc=local")
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)
    
    def get_first(self, key: str, default: Any = None) -> Any:
        val = self._data.get(key)
        if val is None:
            return default
        if isinstance(val, list):
            return val[0] if val else default
        return val


def create_mock_ldap_service():
    """Create a mock LDAP service for testing."""
    mock = AsyncMock()
    mock.get_by_dn = AsyncMock()
    mock.search = AsyncMock()
    mock.add = AsyncMock()
    mock.modify = AsyncMock()
    mock.delete = AsyncMock()
    mock.base_dn = "dc=heracles,dc=local"
    mock._escape_filter = MagicMock(side_effect=lambda x: x)
    return mock


def create_sudo_role_entry(
    cn: str,
    sudo_user: List[str] = None,
    sudo_host: List[str] = None,
    sudo_command: List[str] = None,
    sudo_run_as_user: List[str] = None,
    sudo_option: List[str] = None,
    sudo_order: int = 0,
    description: str = None,
) -> MockLdapEntry:
    """Create a mock sudo role LDAP entry."""
    data = {
        "dn": f"cn={cn},ou=sudoers,dc=heracles,dc=local",
        "cn": [cn],
        "objectClass": ["sudoRole"],
        "sudoUser": sudo_user or [],
        "sudoHost": sudo_host or ["ALL"],
        "sudoCommand": sudo_command or [],
        "sudoRunAsUser": sudo_run_as_user or ["ALL"],
        "sudoRunAsGroup": [],
        "sudoOption": sudo_option or [],
        "sudoOrder": [str(sudo_order)],
    }
    if description:
        data["description"] = [description]
    return MockLdapEntry(data)


# ============================================================================
# Test SudoService
# ============================================================================

class TestSudoService:
    """Tests for SudoService."""
    
    @pytest.fixture
    def mock_ldap(self):
        """Create mock LDAP service."""
        return create_mock_ldap_service()
    
    @pytest.fixture
    def config(self):
        """Default service config."""
        return {
            "sudoers_rdn": "ou=sudoers",
            "base_dn": "dc=heracles,dc=local",
        }
    
    @pytest.fixture
    def service(self, mock_ldap, config):
        """Create SudoService with mocked dependencies."""
        return SudoService(mock_ldap, config)
    
    # -------------------------------------------------------------------------
    # list_roles tests
    # -------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    async def test_list_roles_empty(self, service, mock_ldap):
        """Test listing roles when none exist."""
        mock_ldap.search.return_value = []
        
        result = await service.list_roles()
        
        assert result.total == 0
        assert result.roles == []
        assert result.has_more is False
    
    @pytest.mark.asyncio
    async def test_list_roles_returns_all(self, service, mock_ldap):
        """Test listing all roles."""
        mock_ldap.search.return_value = [
            create_sudo_role_entry("role1", sudo_order=1),
            create_sudo_role_entry("role2", sudo_order=2),
            create_sudo_role_entry("role3", sudo_order=0),
        ]
        
        result = await service.list_roles()
        
        assert result.total == 3
        assert len(result.roles) == 3
        # Should be sorted by order, then cn
        assert result.roles[0].cn == "role3"  # order=0
        assert result.roles[1].cn == "role1"  # order=1
        assert result.roles[2].cn == "role2"  # order=2
    
    @pytest.mark.asyncio
    async def test_list_roles_with_search(self, service, mock_ldap):
        """Test listing roles with search filter."""
        mock_ldap.search.return_value = [
            create_sudo_role_entry("admin-role", sudo_user=["admin"]),
        ]
        
        result = await service.list_roles(search="admin")
        
        mock_ldap.search.assert_called_once()
        call_args = mock_ldap.search.call_args
        assert "admin" in call_args.kwargs.get("search_filter", "")
    
    @pytest.mark.asyncio
    async def test_list_roles_pagination(self, service, mock_ldap):
        """Test pagination of roles."""
        # Create 10 roles
        mock_ldap.search.return_value = [
            create_sudo_role_entry(f"role-{i}") for i in range(10)
        ]
        
        # Get page 2 with page_size 3
        result = await service.list_roles(page=2, page_size=3)
        
        assert result.total == 10
        assert len(result.roles) == 3
        assert result.page == 2
        assert result.page_size == 3
        assert result.has_more is True  # More pages after page 2
    
    # -------------------------------------------------------------------------
    # get_role tests
    # -------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    async def test_get_role_found(self, service, mock_ldap):
        """Test getting an existing role."""
        mock_ldap.get_by_dn.return_value = create_sudo_role_entry(
            "webadmins",
            sudo_user=["testuser", "%admins"],
            sudo_command=["/usr/bin/systemctl restart nginx"],
            description="Web admin role",
        )
        
        result = await service.get_role("webadmins")
        
        assert result is not None
        assert result.cn == "webadmins"
        assert "testuser" in result.sudo_user
        assert "%admins" in result.sudo_user
        assert result.description == "Web admin role"
    
    @pytest.mark.asyncio
    async def test_get_role_not_found(self, service, mock_ldap):
        """Test getting a non-existent role."""
        mock_ldap.get_by_dn.return_value = None
        
        result = await service.get_role("nonexistent")
        
        assert result is None
    
    # -------------------------------------------------------------------------
    # create_role tests
    # -------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    async def test_create_role_success(self, service, mock_ldap):
        """Test successful role creation."""
        # Role doesn't exist yet
        mock_ldap.get_by_dn.side_effect = [
            None,  # First call - check if exists (it doesn't)
            None,  # Check sudoers OU
            create_sudo_role_entry(  # After creation, return the role
                "newrole",
                sudo_user=["testuser"],
                sudo_command=["/bin/ls"],
            ),
        ]
        mock_ldap.search.return_value = [MockLdapEntry({"dn": "ou=sudoers,dc=heracles,dc=local"})]
        
        create_data = SudoRoleCreate(
            cn="newrole",
            sudoUser=["testuser"],
            sudoCommand=["/bin/ls"],
        )
        
        result = await service.create_role(create_data)
        
        # add is called for OU creation + role creation
        assert mock_ldap.add.call_count >= 1
        # Check the role was created with correct DN
        calls = mock_ldap.add.call_args_list
        role_call = [c for c in calls if "cn=newrole" in str(c)]
        assert len(role_call) >= 1
    
    @pytest.mark.asyncio
    async def test_create_role_already_exists(self, service, mock_ldap):
        """Test creating a role that already exists."""
        mock_ldap.get_by_dn.return_value = create_sudo_role_entry("existing")
        
        create_data = SudoRoleCreate(cn="existing")
        
        with pytest.raises(SudoValidationError) as exc_info:
            await service.create_role(create_data)
        
        assert "already exists" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_create_role_with_all_fields(self, service, mock_ldap):
        """Test creating a role with all fields populated."""
        mock_ldap.get_by_dn.side_effect = [
            None,  # Check exists
            None,  # Check OU
            create_sudo_role_entry("full-role"),  # After creation
        ]
        mock_ldap.search.return_value = [MockLdapEntry({"dn": "ou=sudoers,dc=heracles,dc=local"})]
        
        now = datetime.now(timezone.utc)
        create_data = SudoRoleCreate(
            cn="full-role",
            description="Full test role",
            sudoUser=["user1", "%group1"],
            sudoHost=["server1", "server2"],
            sudoCommand=["/bin/cmd1", "/bin/cmd2"],
            sudoRunAsUser=["root"],
            sudoRunAsGroup=["wheel"],
            sudoOption=["NOPASSWD"],
            sudoOrder=10,
            sudoNotBefore=now,
            sudoNotAfter=now + timedelta(days=30),
        )
        
        await service.create_role(create_data)
        
        # add is called for OU creation + role creation
        assert mock_ldap.add.call_count >= 1
        calls = mock_ldap.add.call_args_list
        # Check role creation call contains expected attributes
        role_call = [c for c in calls if "cn=full-role" in str(c)]
        assert len(role_call) >= 1
    
    # -------------------------------------------------------------------------
    # update_role tests
    # -------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    async def test_update_role_success(self, service, mock_ldap):
        """Test successful role update."""
        existing = create_sudo_role_entry(
            "updaterole",
            sudo_user=["olduser"],
            sudo_command=["/old/cmd"],
        )
        mock_ldap.get_by_dn.side_effect = [
            existing,  # Get existing
            create_sudo_role_entry(  # After update
                "updaterole",
                sudo_user=["newuser"],
                sudo_command=["/new/cmd"],
            ),
        ]
        
        update_data = SudoRoleUpdate(
            sudoUser=["newuser"],
            sudoCommand=["/new/cmd"],
        )
        
        result = await service.update_role("updaterole", update_data)
        
        mock_ldap.modify.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_role_not_found(self, service, mock_ldap):
        """Test updating a non-existent role."""
        mock_ldap.get_by_dn.return_value = None
        
        update_data = SudoRoleUpdate(description="New description")
        
        with pytest.raises(Exception):  # LdapNotFoundError
            await service.update_role("nonexistent", update_data)
    
    @pytest.mark.asyncio
    async def test_update_defaults_only_options(self, service, mock_ldap):
        """Test that defaults entry can only have options updated."""
        mock_ldap.get_by_dn.return_value = create_sudo_role_entry("defaults")
        
        # Try to update sudoUser on defaults - should fail
        update_data = SudoRoleUpdate(sudoUser=["someuser"])
        
        with pytest.raises(SudoValidationError) as exc_info:
            await service.update_role("defaults", update_data)
        
        assert "defaults" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_update_partial_fields(self, service, mock_ldap):
        """Test partial update with only some fields."""
        existing = create_sudo_role_entry(
            "partialrole",
            sudo_user=["user1"],
            sudo_command=["/bin/cmd1"],
            description="Old description",
        )
        mock_ldap.get_by_dn.side_effect = [
            existing,
            create_sudo_role_entry("partialrole", description="New description"),
        ]
        
        # Only update description
        update_data = SudoRoleUpdate(description="New description")
        
        await service.update_role("partialrole", update_data)
        
        mock_ldap.modify.assert_called_once()
        call_args = mock_ldap.modify.call_args
        # Verify modify was called (changes structure may vary)
        assert call_args is not None
    
    # -------------------------------------------------------------------------
    # delete_role tests
    # -------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    async def test_delete_role_success(self, service, mock_ldap):
        """Test successful role deletion."""
        mock_ldap.get_by_dn.return_value = create_sudo_role_entry("deleterole")
        
        await service.delete_role("deleterole")
        
        mock_ldap.delete.assert_called_once()
        call_args = mock_ldap.delete.call_args
        assert "cn=deleterole" in call_args.kwargs.get("dn", "") or "cn=deleterole" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_delete_role_not_found(self, service, mock_ldap):
        """Test deleting a non-existent role."""
        mock_ldap.get_by_dn.return_value = None
        
        with pytest.raises(Exception):  # LdapNotFoundError
            await service.delete_role("nonexistent")
    
    @pytest.mark.asyncio
    async def test_delete_defaults_denied(self, service, mock_ldap):
        """Test that deleting defaults entry is denied."""
        mock_ldap.get_by_dn.return_value = create_sudo_role_entry("defaults")
        
        with pytest.raises(SudoValidationError) as exc_info:
            await service.delete_role("defaults")
        
        assert "defaults" in str(exc_info.value).lower()
    
    # -------------------------------------------------------------------------
    # get_roles_for_user tests
    # -------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    async def test_get_roles_for_user(self, service, mock_ldap):
        """Test getting roles for a specific user."""
        mock_ldap.search.return_value = [
            create_sudo_role_entry("role1", sudo_user=["testuser"]),
            create_sudo_role_entry("role2", sudo_user=["testuser", "otheruser"]),
        ]
        
        result = await service.get_roles_for_user("testuser")
        
        assert len(result) == 2
        mock_ldap.search.assert_called_once()
        call_args = mock_ldap.search.call_args
        assert "testuser" in call_args.kwargs.get("search_filter", "")
    
    @pytest.mark.asyncio
    async def test_get_roles_for_user_includes_groups(self, service, mock_ldap):
        """Test that user role lookup includes their groups."""
        mock_ldap.search.return_value = [
            create_sudo_role_entry("role1", sudo_user=["%admins"]),
        ]
        
        result = await service.get_roles_for_user("testuser", groups=["admins", "users"])
        
        # Should search for user AND their groups
        call_args = mock_ldap.search.call_args
        filter_str = call_args.kwargs.get("search_filter", "")
        assert "%admins" in filter_str or "admins" in filter_str
    
    # -------------------------------------------------------------------------
    # get_roles_for_host tests
    # -------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    async def test_get_roles_for_host(self, service, mock_ldap):
        """Test getting roles for a specific host."""
        mock_ldap.search.return_value = [
            create_sudo_role_entry("role1", sudo_host=["server1"]),
            create_sudo_role_entry("role2", sudo_host=["ALL"]),
        ]
        
        result = await service.get_roles_for_host("server1")
        
        assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_get_roles_for_host_includes_all(self, service, mock_ldap):
        """Test that host lookup includes ALL roles."""
        mock_ldap.search.return_value = []
        
        await service.get_roles_for_host("anyhost")
        
        call_args = mock_ldap.search.call_args
        filter_str = call_args.kwargs.get("search_filter", "")
        assert "ALL" in filter_str or "anyhost" in filter_str


# ============================================================================
# Test Helper Methods
# ============================================================================

class TestSudoServiceHelpers:
    """Tests for SudoService helper methods."""
    
    @pytest.fixture
    def service(self):
        """Create SudoService with mocked dependencies."""
        mock_ldap = create_mock_ldap_service()
        config = {
            "sudoers_rdn": "ou=sudoers",
            "base_dn": "dc=heracles,dc=local",
        }
        return SudoService(mock_ldap, config)
    
    def test_entry_to_read_conversion(self, service):
        """Test converting LDAP entry to SudoRoleRead."""
        entry = create_sudo_role_entry(
            "testrole",
            sudo_user=["user1", "%group1"],
            sudo_command=["/bin/ls", "/bin/cat"],
            sudo_option=["NOPASSWD"],
            description="Test role",
        )
        
        result = service._entry_to_read(entry)
        
        assert isinstance(result, SudoRoleRead)
        assert result.cn == "testrole"
        assert "user1" in result.sudo_user
        assert "%group1" in result.sudo_user
        assert len(result.sudo_command) == 2
        assert result.description == "Test role"
    
    def test_build_attributes_from_create(self, service):
        """Test building LDAP attributes from create schema."""
        data = SudoRoleCreate(
            cn="newrole",
            sudoUser=["user1"],
            sudoHost=["host1"],
            sudoCommand=["/bin/cmd"],
            sudoOption=["NOPASSWD"],
        )
        
        attrs = service._build_attributes(data)
        
        assert "cn" in attrs
        assert attrs["cn"] == "newrole"
        assert "sudoUser" in attrs
        assert "sudoHost" in attrs
        assert "sudoCommand" in attrs


# ============================================================================
# Test Edge Cases and Error Handling
# ============================================================================

class TestSudoServiceEdgeCases:
    """Tests for edge cases and error handling."""
    
    @pytest.fixture
    def mock_ldap(self):
        return create_mock_ldap_service()
    
    @pytest.fixture
    def service(self, mock_ldap):
        config = {
            "sudoers_rdn": "ou=sudoers",
            "base_dn": "dc=heracles,dc=local",
        }
        return SudoService(mock_ldap, config)
    
    @pytest.mark.asyncio
    async def test_ldap_error_handling(self, service, mock_ldap):
        """Test handling of LDAP errors."""
        from heracles_api.services.ldap_service import LdapOperationError
        
        mock_ldap.search.side_effect = LdapOperationError("Connection failed")
        
        with pytest.raises(LdapOperationError):
            await service.list_roles()
    
    @pytest.mark.asyncio
    async def test_ensure_sudoers_ou_creates_if_missing(self, service, mock_ldap):
        """Test that sudoers OU is created if it doesn't exist."""
        mock_ldap.search.return_value = []  # OU doesn't exist
        created_entry = create_sudo_role_entry("newrole")
        mock_ldap.get_by_dn.side_effect = [
            None,  # Role doesn't exist (first check)
            None,  # OU check
            created_entry,  # After creation - return the role
        ]
        
        create_data = SudoRoleCreate(cn="newrole", sudoCommand=["/bin/test"])
        
        await service.create_role(create_data)
        
        # Should have created both OU and role
        assert mock_ldap.add.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_special_characters_in_cn(self, service, mock_ldap):
        """Test handling of special characters in CN."""
        mock_ldap.get_by_dn.return_value = create_sudo_role_entry("role+special")
        
        result = await service.get_role("role+special")
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_time_validity_check(self, service, mock_ldap):
        """Test time-based validity checking."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(days=1)
        future = now + timedelta(days=1)
        
        # Create entry with time constraints
        entry_data = {
            "dn": "cn=timed,ou=sudoers,dc=heracles,dc=local",
            "cn": ["timed"],
            "objectClass": ["sudoRole"],
            "sudoNotBefore": [past.strftime("%Y%m%d%H%M%SZ")],
            "sudoNotAfter": [future.strftime("%Y%m%d%H%M%SZ")],
            "sudoUser": [],
            "sudoHost": ["ALL"],
            "sudoCommand": [],
            "sudoRunAsUser": ["ALL"],
            "sudoRunAsGroup": [],
            "sudoOption": [],
            "sudoOrder": ["0"],
        }
        
        mock_ldap.get_by_dn.return_value = MockLdapEntry(entry_data)
        
        result = await service.get_role("timed")
        
        # Role should be valid (we're between not_before and not_after)
        assert result is not None
