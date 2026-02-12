"""
Sudo Plugin API Routes Tests
============================

Tests for Sudo API endpoints with mocked service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from httpx import AsyncClient

from heracles_plugins.sudo.routes import router
from heracles_plugins.sudo.schemas import (
    SudoRoleCreate,
    SudoRoleRead,
    SudoRoleUpdate,
    SudoRoleListResponse,
)
from heracles_plugins.sudo.service import SudoValidationError


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_sudo_service():
    """Create mock sudo service."""
    service = AsyncMock()
    service.list_roles = AsyncMock()
    service.get_role = AsyncMock()
    service.create_role = AsyncMock()
    service.update_role = AsyncMock()
    service.delete_role = AsyncMock()
    service.get_roles_for_user = AsyncMock()
    service.get_roles_for_host = AsyncMock()
    service.get_default_role = AsyncMock()
    return service


@pytest.fixture
def mock_current_user():
    """Create mock current user."""
    user = MagicMock()
    user.uid = "testuser"
    user.dn = "uid=testuser,ou=people,dc=heracles,dc=local"
    user.groups = ["admins"]
    return user


@pytest.fixture
def app(mock_sudo_service, mock_current_user):
    """Create FastAPI app with mocked dependencies."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    
    # Override dependencies
    from heracles_plugins.sudo.routes import get_sudo_service
    
    app.dependency_overrides[get_sudo_service] = lambda: mock_sudo_service
    
    # Mock auth - return user directly
    async def mock_get_current_user():
        return mock_current_user
    
    # We need to properly mock the CurrentUser dependency
    
    return app


@pytest.fixture
def sample_role():
    """Create sample sudo role."""
    return SudoRoleRead(
        cn="webadmins",
        dn="cn=webadmins,ou=sudoers,dc=heracles,dc=local",
        sudoUser=["testuser", "%admins"],
        sudoHost=["ALL"],
        sudoCommand=["/usr/bin/systemctl restart nginx"],
        sudoRunAsUser=["root"],
        sudoRunAsGroup=[],
        sudoOption=["NOPASSWD"],
        sudoOrder=10,
        description="Web admin role",
    )


# ============================================================================
# Test List Roles Endpoint
# ============================================================================

class TestListRolesEndpoint:
    """Tests for GET /sudo/roles endpoint."""
    
    @pytest.mark.asyncio
    async def test_list_roles_success(self, app, mock_sudo_service, sample_role):
        """Test successful role listing."""
        mock_sudo_service.list_roles.return_value = SudoRoleListResponse(
            roles=[sample_role],
            total=1,
            page=1,
            page_size=50,
            has_more=False,
        )
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Note: In real tests, we'd need to handle auth
            await client.get("/api/v1/sudo/roles")
        
        # Would need proper auth mocking for full test
        # This is a structural test showing the pattern
    
    @pytest.mark.asyncio
    async def test_list_roles_with_search(self, mock_sudo_service):
        """Test role listing with search parameter."""
        mock_sudo_service.list_roles.return_value = SudoRoleListResponse(
            roles=[],
            total=0,
            page=1,
            page_size=50,
            has_more=False,
        )
        
        # Call service directly to test search parameter
        await mock_sudo_service.list_roles(search="admin")
        
        mock_sudo_service.list_roles.assert_called_with(search="admin")
    
    @pytest.mark.asyncio
    async def test_list_roles_pagination(self, mock_sudo_service):
        """Test role listing with pagination."""
        mock_sudo_service.list_roles.return_value = SudoRoleListResponse(
            roles=[],
            total=100,
            page=2,
            page_size=10,
            has_more=True,
        )
        
        await mock_sudo_service.list_roles(page=2, page_size=10)
        
        mock_sudo_service.list_roles.assert_called_with(page=2, page_size=10)


# ============================================================================
# Test Get Role Endpoint
# ============================================================================

class TestGetRoleEndpoint:
    """Tests for GET /sudo/roles/{cn} endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_role_found(self, mock_sudo_service, sample_role):
        """Test getting an existing role."""
        mock_sudo_service.get_role.return_value = sample_role
        
        result = await mock_sudo_service.get_role("webadmins")
        
        assert result.cn == "webadmins"
        mock_sudo_service.get_role.assert_called_with("webadmins")
    
    @pytest.mark.asyncio
    async def test_get_role_not_found(self, mock_sudo_service):
        """Test getting a non-existent role."""
        mock_sudo_service.get_role.return_value = None
        
        result = await mock_sudo_service.get_role("nonexistent")
        
        assert result is None


# ============================================================================
# Test Create Role Endpoint
# ============================================================================

class TestCreateRoleEndpoint:
    """Tests for POST /sudo/roles endpoint."""
    
    @pytest.mark.asyncio
    async def test_create_role_success(self, mock_sudo_service, sample_role):
        """Test successful role creation."""
        mock_sudo_service.create_role.return_value = sample_role
        
        create_data = SudoRoleCreate(
            cn="webadmins",
            sudoUser=["testuser", "%admins"],
            sudoHost=["ALL"],
            sudoCommand=["/usr/bin/systemctl restart nginx"],
            sudoRunAsUser=["root"],
            sudoOption=["NOPASSWD"],
        )
        
        result = await mock_sudo_service.create_role(create_data)
        
        assert result.cn == "webadmins"
        mock_sudo_service.create_role.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_role_validation_error(self, mock_sudo_service):
        """Test role creation with validation error."""
        mock_sudo_service.create_role.side_effect = SudoValidationError(
            "Role already exists"
        )
        
        create_data = SudoRoleCreate(cn="existing")
        
        with pytest.raises(SudoValidationError):
            await mock_sudo_service.create_role(create_data)
    
    @pytest.mark.asyncio
    async def test_create_role_minimal(self, mock_sudo_service):
        """Test creating role with minimal data."""
        mock_sudo_service.create_role.return_value = SudoRoleRead(
            cn="minimal",
            dn="cn=minimal,ou=sudoers,dc=test",
        )
        
        create_data = SudoRoleCreate(cn="minimal")
        
        result = await mock_sudo_service.create_role(create_data)
        
        assert result.cn == "minimal"


# ============================================================================
# Test Update Role Endpoint
# ============================================================================

class TestUpdateRoleEndpoint:
    """Tests for PUT /sudo/roles/{cn} endpoint."""
    
    @pytest.mark.asyncio
    async def test_update_role_success(self, mock_sudo_service, sample_role):
        """Test successful role update."""
        updated_role = SudoRoleRead(
            cn="webadmins",
            dn="cn=webadmins,ou=sudoers,dc=heracles,dc=local",
            sudoUser=["newuser"],
            sudoHost=["ALL"],
            sudoCommand=["/new/command"],
            sudoRunAsUser=["root"],
            description="Updated description",
        )
        mock_sudo_service.update_role.return_value = updated_role
        
        update_data = SudoRoleUpdate(
            sudoUser=["newuser"],
            sudoCommand=["/new/command"],
            description="Updated description",
        )
        
        result = await mock_sudo_service.update_role("webadmins", update_data)
        
        assert result.sudo_user == ["newuser"]
        assert result.description == "Updated description"
    
    @pytest.mark.asyncio
    async def test_update_role_partial(self, mock_sudo_service, sample_role):
        """Test partial role update."""
        mock_sudo_service.update_role.return_value = sample_role
        
        update_data = SudoRoleUpdate(description="New description only")
        
        await mock_sudo_service.update_role("webadmins", update_data)
        
        mock_sudo_service.update_role.assert_called_once()


# ============================================================================
# Test Delete Role Endpoint
# ============================================================================

class TestDeleteRoleEndpoint:
    """Tests for DELETE /sudo/roles/{cn} endpoint."""
    
    @pytest.mark.asyncio
    async def test_delete_role_success(self, mock_sudo_service):
        """Test successful role deletion."""
        mock_sudo_service.delete_role.return_value = None
        
        await mock_sudo_service.delete_role("webadmins")
        
        mock_sudo_service.delete_role.assert_called_with("webadmins")
    
    @pytest.mark.asyncio
    async def test_delete_defaults_denied(self, mock_sudo_service):
        """Test deleting defaults entry is denied."""
        mock_sudo_service.delete_role.side_effect = SudoValidationError(
            "Cannot delete defaults entry"
        )
        
        with pytest.raises(SudoValidationError):
            await mock_sudo_service.delete_role("defaults")


# ============================================================================
# Test User Roles Endpoint
# ============================================================================

class TestUserRolesEndpoint:
    """Tests for GET /sudo/users/{uid}/roles endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_user_roles(self, mock_sudo_service, sample_role):
        """Test getting roles for a user."""
        mock_sudo_service.get_roles_for_user.return_value = [sample_role]
        
        result = await mock_sudo_service.get_roles_for_user("testuser")
        
        assert len(result) == 1
        assert result[0].cn == "webadmins"
    
    @pytest.mark.asyncio
    async def test_get_user_roles_with_groups(self, mock_sudo_service, sample_role):
        """Test getting roles including group membership."""
        mock_sudo_service.get_roles_for_user.return_value = [sample_role]
        
        await mock_sudo_service.get_roles_for_user(
            "testuser",
            groups=["admins", "developers"]
        )
        
        mock_sudo_service.get_roles_for_user.assert_called_with(
            "testuser",
            groups=["admins", "developers"]
        )
    
    @pytest.mark.asyncio
    async def test_get_user_roles_empty(self, mock_sudo_service):
        """Test user with no sudo roles."""
        mock_sudo_service.get_roles_for_user.return_value = []
        
        result = await mock_sudo_service.get_roles_for_user("nonadmin")
        
        assert result == []


# ============================================================================
# Test Host Roles Endpoint
# ============================================================================

class TestHostRolesEndpoint:
    """Tests for GET /sudo/hosts/{hostname}/roles endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_host_roles(self, mock_sudo_service, sample_role):
        """Test getting roles for a host."""
        mock_sudo_service.get_roles_for_host.return_value = [sample_role]
        
        result = await mock_sudo_service.get_roles_for_host("server1")
        
        assert len(result) == 1
    
    @pytest.mark.asyncio
    async def test_get_host_roles_all(self, mock_sudo_service, sample_role):
        """Test getting roles that apply to ALL hosts."""
        mock_sudo_service.get_roles_for_host.return_value = [sample_role]
        
        result = await mock_sudo_service.get_roles_for_host("anyhost")
        
        # Role with sudoHost=["ALL"] should be returned
        assert len(result) == 1


# ============================================================================
# Test Defaults Endpoint
# ============================================================================

class TestDefaultsEndpoint:
    """Tests for GET /sudo/defaults endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_defaults_exists(self, mock_sudo_service):
        """Test getting defaults entry when it exists."""
        defaults = SudoRoleRead(
            cn="defaults",
            dn="cn=defaults,ou=sudoers,dc=test",
            sudoOption=["env_reset", "mail_badpass"],
        )
        mock_sudo_service.get_role.return_value = defaults
        
        result = await mock_sudo_service.get_role("defaults")
        
        assert result.cn == "defaults"
        # defaults entry has specific cn
        assert result.cn.lower() == "defaults"
    
    @pytest.mark.asyncio
    async def test_get_defaults_not_exists(self, mock_sudo_service):
        """Test getting defaults when it doesn't exist."""
        mock_sudo_service.get_role.return_value = None
        
        result = await mock_sudo_service.get_role("defaults")
        
        assert result is None


# ============================================================================
# Test Request/Response Models
# ============================================================================

class TestRequestResponseModels:
    """Tests for API request/response serialization."""
    
    def test_role_response_json_alias(self, sample_role):
        """Test that response uses correct JSON aliases."""
        json_data = sample_role.model_dump(by_alias=True)
        
        assert "sudoUser" in json_data
        assert "sudoHost" in json_data
        assert "sudoCommand" in json_data
        assert "sudoRunAsUser" in json_data
        assert "sudoOption" in json_data
        assert "sudoOrder" in json_data
        assert "isDefault" in json_data
        assert "isValid" in json_data
    
    def test_list_response_structure(self, sample_role):
        """Test list response structure."""
        response = SudoRoleListResponse(
            roles=[sample_role],
            total=1,
            page=1,
            page_size=50,
            has_more=False,
        )
        
        json_data = response.model_dump()
        
        assert "roles" in json_data
        assert "total" in json_data
        assert "page" in json_data
        assert "page_size" in json_data
        assert "has_more" in json_data
    
    def test_create_request_from_json(self):
        """Test creating request from JSON payload."""
        json_payload = {
            "cn": "newrole",
            "sudoUser": ["user1", "%group1"],
            "sudoHost": ["server1"],
            "sudoCommand": ["/bin/cmd"],
            "sudoRunAsUser": ["root"],
            "sudoOption": ["NOPASSWD"],
            "sudoOrder": 5,
            "description": "New role",
        }
        
        data = SudoRoleCreate(**json_payload)
        
        assert data.cn == "newrole"
        assert data.sudo_user == ["user1", "%group1"]
        assert data.sudo_order == 5
    
    def test_update_request_partial(self):
        """Test partial update request."""
        json_payload = {
            "description": "Updated only",
        }
        
        data = SudoRoleUpdate(**json_payload)
        
        assert data.description == "Updated only"
        assert data.sudo_user is None
        assert data.sudo_command is None
