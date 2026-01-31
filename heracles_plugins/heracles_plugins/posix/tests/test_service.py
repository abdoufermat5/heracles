"""
POSIX Plugin Service Tests
==========================

Tests for POSIX service business logic with mocked LDAP operations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, List, Optional

from heracles_plugins.posix.service import (
    PosixService,
    PosixGroupService,
    MixedGroupService,
    PosixValidationError,
)
from heracles_plugins.posix.schemas import (
    TrustMode,
    AccountStatus,
    PrimaryGroupMode,
    PosixAccountCreate,
    PosixAccountUpdate,
    PosixGroupFullCreate,
    PosixGroupUpdate,
    MixedGroupCreate,
    MixedGroupUpdate,
)


# ============================================================================
# Mock LDAP Helpers
# ============================================================================

class MockLdapEntry:
    """Mock LDAP entry for testing."""
    
    def __init__(self, data: Dict[str, Any]):
        self._data = data
    
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
    return mock


# ============================================================================
# Test PosixService
# ============================================================================

class TestPosixService:
    """Tests for PosixService (user POSIX accounts)."""
    
    @pytest.fixture
    def mock_ldap(self):
        """Create mock LDAP service."""
        return create_mock_ldap_service()
    
    @pytest.fixture
    def config(self):
        """Default service config."""
        return {
            "uid_min": 10000,
            "uid_max": 60000,
            "gid_min": 10000,
            "gid_max": 60000,
            "default_shell": "/bin/bash",
            "default_home_base": "/home",
        }
    
    @pytest.fixture
    def service(self, mock_ldap, config):
        """Create PosixService with mocked dependencies."""
        return PosixService(mock_ldap, config)
    
    # -------------------------------------------------------------------------
    # is_active tests
    # -------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    async def test_is_active_returns_true_when_posix_present(self, service, mock_ldap):
        """Test is_active returns True when posixAccount objectClass exists."""
        mock_ldap.get_by_dn.return_value = MockLdapEntry({
            "objectClass": ["inetOrgPerson", "posixAccount", "shadowAccount"]
        })
        
        result = await service.is_active("uid=testuser,ou=people,dc=example,dc=com")
        
        assert result is True
        mock_ldap.get_by_dn.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_is_active_returns_false_when_no_posix(self, service, mock_ldap):
        """Test is_active returns False when posixAccount not present."""
        mock_ldap.get_by_dn.return_value = MockLdapEntry({
            "objectClass": ["inetOrgPerson"]
        })
        
        result = await service.is_active("uid=testuser,ou=people,dc=example,dc=com")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_is_active_returns_false_when_entry_not_found(self, service, mock_ldap):
        """Test is_active returns False when entry doesn't exist."""
        mock_ldap.get_by_dn.return_value = None
        
        result = await service.is_active("uid=nonexistent,ou=people,dc=example,dc=com")
        
        assert result is False
    
    # -------------------------------------------------------------------------
    # read tests
    # -------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    async def test_read_returns_none_when_not_active(self, service, mock_ldap):
        """Test read returns None when POSIX not active."""
        mock_ldap.get_by_dn.return_value = MockLdapEntry({
            "objectClass": ["inetOrgPerson"]  # No posixAccount
        })
        
        result = await service.read("uid=testuser,ou=people,dc=example,dc=com")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_read_returns_full_posix_data(self, service, mock_ldap):
        """Test read returns all POSIX attributes."""
        # First call for is_active check
        # Second call for read
        mock_ldap.get_by_dn.side_effect = [
            MockLdapEntry({"objectClass": ["inetOrgPerson", "posixAccount"]}),
            MockLdapEntry({
                "uid": "testuser",
                "uidNumber": "10001",
                "gidNumber": "10000",
                "homeDirectory": "/home/testuser",
                "loginShell": "/bin/zsh",
                "gecos": "Test User",
                "shadowLastChange": "19500",
                "shadowMin": "0",
                "shadowMax": "99999",
                "shadowWarning": "7",
                "shadowInactive": "-1",
            }),
        ]
        
        # Mock group lookups
        mock_ldap.search.side_effect = [
            [MockLdapEntry({"cn": "users"})],  # Primary group lookup
            [],  # Group memberships lookup (no additional groups)
        ]
        
        result = await service.read("uid=testuser,ou=people,dc=example,dc=com")
        
        assert result is not None
        assert result.uid_number == 10001
        assert result.gid_number == 10000
        assert result.home_directory == "/home/testuser"
        assert result.login_shell == "/bin/zsh"
        assert result.gecos == "Test User"
        assert result.shadow_last_change == 19500
        assert result.shadow_max == 99999
        assert result.primary_group_cn == "users"
    
    @pytest.mark.asyncio
    async def test_read_parses_trust_mode_fullaccess(self, service, mock_ldap):
        """Test read correctly parses fullaccess trust mode."""
        mock_ldap.get_by_dn.side_effect = [
            MockLdapEntry({"objectClass": ["inetOrgPerson", "posixAccount"]}),
            MockLdapEntry({
                "uid": "testuser",
                "uidNumber": "10001",
                "gidNumber": "10000",
                "homeDirectory": "/home/testuser",
                "host": ["*"],  # Full access marker
            }),
        ]
        mock_ldap.search.side_effect = [
            [MockLdapEntry({"cn": "users"})],
            [],
        ]
        
        result = await service.read("uid=testuser,ou=people,dc=example,dc=com")
        
        assert result.trust_mode == TrustMode.FULL_ACCESS
    
    @pytest.mark.asyncio
    async def test_read_parses_trust_mode_byhost(self, service, mock_ldap):
        """Test read correctly parses byhost trust mode."""
        mock_ldap.get_by_dn.side_effect = [
            MockLdapEntry({"objectClass": ["inetOrgPerson", "posixAccount"]}),
            MockLdapEntry({
                "uid": "testuser",
                "uidNumber": "10001",
                "gidNumber": "10000",
                "homeDirectory": "/home/testuser",
                "host": ["server1.example.com", "server2.example.com"],
            }),
        ]
        mock_ldap.search.side_effect = [
            [MockLdapEntry({"cn": "users"})],
            [],
        ]
        
        result = await service.read("uid=testuser,ou=people,dc=example,dc=com")
        
        assert result.trust_mode == TrustMode.BY_HOST
        assert result.host == ["server1.example.com", "server2.example.com"]
    
    # -------------------------------------------------------------------------
    # Account status computation tests
    # -------------------------------------------------------------------------
    
    def test_compute_account_status_active(self, service):
        """Test active account status computation."""
        status = service._compute_account_status(
            shadow_last_change=19500,
            shadow_max=99999,
            shadow_inactive=None,
            shadow_expire=None,
        )
        assert status == AccountStatus.ACTIVE
    
    def test_compute_account_status_expired(self, service):
        """Test expired account status computation."""
        # shadowExpire in the past
        status = service._compute_account_status(
            shadow_last_change=19500,
            shadow_max=99999,
            shadow_inactive=None,
            shadow_expire=10000,  # Way in the past
        )
        assert status == AccountStatus.EXPIRED
    
    def test_compute_account_status_password_expired(self, service):
        """Test password expired status computation."""
        # shadowLastChange = 0 forces password change
        status = service._compute_account_status(
            shadow_last_change=0,
            shadow_max=99999,
            shadow_inactive=None,
            shadow_expire=None,
        )
        assert status == AccountStatus.PASSWORD_EXPIRED
    
    # -------------------------------------------------------------------------
    # UID allocation tests
    # -------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    async def test_allocate_next_uid_finds_first_available(self, service, mock_ldap):
        """Test UID allocation finds first available in range."""
        mock_ldap.search.return_value = [
            MockLdapEntry({"uidNumber": "10000"}),
            MockLdapEntry({"uidNumber": "10001"}),
            MockLdapEntry({"uidNumber": "10003"}),  # 10002 is skipped
        ]
        
        uid = await service._allocate_next_uid()
        
        assert uid == 10002  # First available
    
    @pytest.mark.asyncio
    async def test_allocate_next_uid_starts_at_minimum(self, service, mock_ldap):
        """Test UID allocation starts at configured minimum."""
        mock_ldap.search.return_value = []  # No UIDs in use
        
        uid = await service._allocate_next_uid()
        
        assert uid == 10000  # Starts at uid_min
    
    @pytest.mark.asyncio
    async def test_allocate_next_uid_raises_when_exhausted(self, service, mock_ldap, config):
        """Test UID allocation raises error when range exhausted."""
        # Configure a tiny range
        service._uid_min = 10000
        service._uid_max = 10002
        
        # All UIDs in range are used
        mock_ldap.search.return_value = [
            MockLdapEntry({"uidNumber": "10000"}),
            MockLdapEntry({"uidNumber": "10001"}),
            MockLdapEntry({"uidNumber": "10002"}),
        ]
        
        with pytest.raises(PosixValidationError) as exc_info:
            await service._allocate_next_uid()
        
        assert "No available UIDs" in str(exc_info.value)
    
    # -------------------------------------------------------------------------
    # Shell helpers tests
    # -------------------------------------------------------------------------
    
    def test_get_shells(self, service):
        """Test get_shells returns configured shells."""
        shells = service.get_shells()
        
        assert len(shells) > 0
        assert any(s["value"] == "/bin/bash" for s in shells)
    
    def test_get_default_shell(self, service):
        """Test get_default_shell returns configured default."""
        default = service.get_default_shell()
        
        assert default == "/bin/bash"
    
    def test_get_id_ranges(self, service):
        """Test get_id_ranges returns configured ranges."""
        ranges = service.get_id_ranges()
        
        assert ranges["uid"]["min"] == 10000
        assert ranges["uid"]["max"] == 60000
        assert ranges["gid"]["min"] == 10000
        assert ranges["gid"]["max"] == 60000


# ============================================================================
# Test PosixGroupService
# ============================================================================

class TestPosixGroupService:
    """Tests for PosixGroupService (standalone POSIX groups)."""
    
    @pytest.fixture
    def mock_ldap(self):
        """Create mock LDAP service."""
        return create_mock_ldap_service()
    
    @pytest.fixture
    def config(self):
        """Default service config."""
        return {
            "gid_min": 10000,
            "gid_max": 60000,
            "posix_groups_ou": "ou=groups",
        }
    
    @pytest.fixture
    def service(self, mock_ldap, config):
        """Create PosixGroupService with mocked dependencies."""
        with patch("heracles_api.config.settings") as mock_settings:
            mock_settings.LDAP_BASE_DN = "dc=example,dc=com"
            return PosixGroupService(mock_ldap, config)
    
    # -------------------------------------------------------------------------
    # get tests
    # -------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    async def test_get_returns_group_with_trust_mode(self, service, mock_ldap):
        """Test get returns group with parsed trust mode."""
        mock_ldap.get_by_dn.return_value = MockLdapEntry({
            "cn": "developers",
            "gidNumber": "20000",
            "description": "Dev team",
            "memberUid": ["user1", "user2"],
            "host": ["devserver.example.com"],
            "objectClass": ["posixGroup", "hostObject"],
        })
        
        result = await service.get("developers")
        
        assert result is not None
        assert result.cn == "developers"
        assert result.gid_number == 20000
        assert result.trust_mode == TrustMode.BY_HOST
        assert result.host == ["devserver.example.com"]
    
    @pytest.mark.asyncio
    async def test_get_returns_none_for_nonexistent(self, service, mock_ldap):
        """Test get returns None for nonexistent group."""
        mock_ldap.get_by_dn.return_value = None
        
        result = await service.get("nonexistent")
        
        assert result is None
    
    # -------------------------------------------------------------------------
    # create tests
    # -------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    async def test_create_with_auto_gid(self, service, mock_ldap):
        """Test creating group with auto-allocated GID."""
        mock_ldap.get_by_dn.side_effect = [
            None,  # Group doesn't exist
            MockLdapEntry({  # After creation
                "cn": "newgroup",
                "gidNumber": "10000",
                "objectClass": ["posixGroup"],
            }),
        ]
        mock_ldap.search.return_value = []  # No GIDs in use
        
        data = PosixGroupFullCreate(cn="newgroup")
        result = await service.create(data)
        
        mock_ldap.add.assert_called_once()
        call_args = mock_ldap.add.call_args
        assert call_args[0][1] == ["posixGroup"]  # Object classes
    
    @pytest.mark.asyncio
    async def test_create_with_trust_mode(self, service, mock_ldap):
        """Test creating group with system trust."""
        mock_ldap.get_by_dn.side_effect = [
            None,  # Group doesn't exist
            MockLdapEntry({
                "cn": "securegroup",
                "gidNumber": "20000",
                "host": ["secureserver"],
                "objectClass": ["posixGroup", "hostObject"],
            }),
        ]
        mock_ldap.search.return_value = []
        
        data = PosixGroupFullCreate(
            cn="securegroup",
            gidNumber=20000,
            trustMode=TrustMode.BY_HOST,
            host=["secureserver"],
        )
        result = await service.create(data)
        
        # Verify hostObject was added to objectClasses
        call_args = mock_ldap.add.call_args
        assert "hostObject" in call_args[0][1]
    
    @pytest.mark.asyncio
    async def test_create_with_force_gid(self, service, mock_ldap):
        """Test creating group with forced GID."""
        mock_ldap.get_by_dn.side_effect = [
            None,  # Group doesn't exist
            MockLdapEntry({
                "cn": "forcegroup",
                "gidNumber": "50000",
                "objectClass": ["posixGroup"],
            }),
        ]
        # GID exists but we're forcing it
        mock_ldap.search.return_value = [MockLdapEntry({"gidNumber": "50000"})]
        
        data = PosixGroupFullCreate(
            cn="forcegroup",
            gidNumber=50000,
            forceGid=True,  # Force even though GID exists
        )
        result = await service.create(data)
        
        mock_ldap.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_fails_when_gid_exists_without_force(self, service, mock_ldap):
        """Test create fails when GID exists and force not set."""
        mock_ldap.get_by_dn.return_value = None  # Group doesn't exist
        mock_ldap.search.return_value = [MockLdapEntry({"gidNumber": "20000"})]  # GID exists
        
        data = PosixGroupFullCreate(
            cn="conflictgroup",
            gidNumber=20000,
            forceGid=False,
        )
        
        with pytest.raises(PosixValidationError) as exc_info:
            await service.create(data)
        
        assert "already in use" in str(exc_info.value)
    
    # -------------------------------------------------------------------------
    # update tests
    # -------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    async def test_update_adds_trust_mode(self, service, mock_ldap):
        """Test update can add trust mode to existing group."""
        mock_ldap.get_by_dn.side_effect = [
            MockLdapEntry({  # Initial read for get()
                "cn": "existinggroup",
                "gidNumber": "20000",
                "objectClass": ["posixGroup"],  # No hostObject yet
            }),
            MockLdapEntry({  # Read for checking objectClasses
                "objectClass": ["posixGroup"],
                "host": None,
            }),
            MockLdapEntry({  # Final read after update
                "cn": "existinggroup",
                "gidNumber": "20000",
                "host": ["newserver"],
                "objectClass": ["posixGroup", "hostObject"],
            }),
        ]
        
        data = PosixGroupUpdate(
            trustMode=TrustMode.BY_HOST,
            host=["newserver"],
        )
        result = await service.update_group("existinggroup", data)
        
        # Verify modify was called with hostObject addition
        mock_ldap.modify.assert_called_once()
    
    # -------------------------------------------------------------------------
    # member management tests
    # -------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    async def test_add_member_by_cn(self, service, mock_ldap):
        """Test adding member to group by cn."""
        mock_ldap.get_by_dn.side_effect = [
            MockLdapEntry({
                "cn": "testgroup",
                "gidNumber": "20000",
                "memberUid": ["user1"],
                "objectClass": ["posixGroup"],
            }),
            MockLdapEntry({
                "cn": "testgroup",
                "gidNumber": "20000",
                "memberUid": ["user1", "user2"],
                "objectClass": ["posixGroup"],
            }),
        ]
        
        result = await service.add_member_by_cn("testgroup", "user2")
        
        mock_ldap.modify.assert_called_once()
        assert result.member_uid == ["user1", "user2"]
    
    @pytest.mark.asyncio
    async def test_add_member_idempotent(self, service, mock_ldap):
        """Test adding existing member is idempotent."""
        mock_ldap.get_by_dn.return_value = MockLdapEntry({
            "cn": "testgroup",
            "gidNumber": "20000",
            "memberUid": ["user1", "user2"],  # user2 already member
            "objectClass": ["posixGroup"],
        })
        
        result = await service.add_member_by_cn("testgroup", "user2")
        
        # Should not call modify since user is already a member
        mock_ldap.modify.assert_not_called()


# ============================================================================
# Test MixedGroupService
# ============================================================================

class TestMixedGroupService:
    """Tests for MixedGroupService (groupOfNames + posixGroup hybrid)."""
    
    @pytest.fixture
    def mock_ldap(self):
        """Create mock LDAP service."""
        return create_mock_ldap_service()
    
    @pytest.fixture
    def config(self):
        """Default service config."""
        return {
            "gid_min": 10000,
            "gid_max": 60000,
            "mixed_groups_ou": "ou=groups",
        }
    
    @pytest.fixture
    def service(self, mock_ldap, config):
        """Create MixedGroupService with mocked dependencies."""
        with patch("heracles_api.config.settings") as mock_settings:
            mock_settings.LDAP_BASE_DN = "dc=example,dc=com"
            return MixedGroupService(mock_ldap, config)
    
    # -------------------------------------------------------------------------
    # get tests
    # -------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    async def test_get_returns_mixed_group(self, service, mock_ldap):
        """Test get returns mixed group with both member types."""
        mock_ldap.get_by_dn.return_value = MockLdapEntry({
            "cn": "mixedgroup",
            "gidNumber": "30000",
            "member": ["uid=user1,ou=people,dc=example,dc=com"],
            "memberUid": ["user1"],
            "host": ["*"],
            "objectClass": ["groupOfNames", "posixGroupAux", "hostObject"],
        })
        
        result = await service.get("mixedgroup")
        
        assert result is not None
        assert result.cn == "mixedgroup"
        assert len(result.member) == 1
        assert result.member_uid == ["user1"]
        assert result.trust_mode == TrustMode.FULL_ACCESS
        assert result.is_mixed_group is True
    
    @pytest.mark.asyncio
    async def test_get_returns_none_for_non_mixed(self, service, mock_ldap):
        """Test get returns None if not both groupOfNames and posixGroup."""
        mock_ldap.get_by_dn.return_value = MockLdapEntry({
            "cn": "pureposix",
            "gidNumber": "30000",
            "objectClass": ["posixGroup"],  # Missing groupOfNames and posixGroupAux
        })
        
        result = await service.get("pureposix")
        
        assert result is None
    
    # -------------------------------------------------------------------------
    # create tests
    # -------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    async def test_create_with_trust_mode(self, service, mock_ldap):
        """Test creating mixed group with trust mode."""
        mock_ldap.get_by_dn.side_effect = [
            None,  # Group doesn't exist
            MockLdapEntry({
                "cn": "securemixed",
                "gidNumber": "30000",
                "member": ["cn=securemixed,ou=groups,dc=example,dc=com"],
                "host": ["secureserver"],
                "objectClass": ["groupOfNames", "posixGroupAux", "hostObject"],
            }),
        ]
        mock_ldap.search.return_value = []
        
        data = MixedGroupCreate(
            cn="securemixed",
            trustMode=TrustMode.BY_HOST,
            host=["secureserver"],
        )
        result = await service.create(data)
        
        call_args = mock_ldap.add.call_args
        # Should have all three objectClasses
        assert "groupOfNames" in call_args[0][1]
        assert "posixGroupAux" in call_args[0][1]
        assert "hostObject" in call_args[0][1]
    
    @pytest.mark.asyncio
    async def test_create_adds_self_as_member(self, service, mock_ldap):
        """Test create adds group DN as member when no members provided."""
        mock_ldap.get_by_dn.side_effect = [
            None,
            MockLdapEntry({
                "cn": "emptygroup",
                "gidNumber": "30000",
                "member": ["cn=emptygroup,ou=groups,dc=example,dc=com"],
                "objectClass": ["groupOfNames", "posixGroupAux"],
            }),
        ]
        mock_ldap.search.return_value = []
        
        data = MixedGroupCreate(cn="emptygroup")  # No members
        result = await service.create(data)
        
        call_args = mock_ldap.add.call_args
        attrs = call_args[0][2]
        # Should have self-reference as member
        assert "member" in attrs
        assert len(attrs["member"]) == 1
    
    # -------------------------------------------------------------------------
    # member management tests
    # -------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    async def test_add_member_uid(self, service, mock_ldap):
        """Test adding memberUid to mixed group."""
        mock_ldap.get_by_dn.side_effect = [
            MockLdapEntry({
                "cn": "mixedgroup",
                "gidNumber": "30000",
                "member": ["cn=mixedgroup,ou=groups,dc=example,dc=com"],
                "memberUid": [],
                "objectClass": ["groupOfNames", "posixGroupAux"],
            }),
            MockLdapEntry({
                "cn": "mixedgroup",
                "gidNumber": "30000",
                "member": ["cn=mixedgroup,ou=groups,dc=example,dc=com"],
                "memberUid": ["newuser"],
                "objectClass": ["groupOfNames", "posixGroupAux"],
            }),
        ]
        
        result = await service.add_member_uid("mixedgroup", "newuser")
        
        mock_ldap.modify.assert_called_once()
        assert "newuser" in result.member_uid
    
    @pytest.mark.asyncio
    async def test_cannot_remove_last_member(self, service, mock_ldap):
        """Test removing last member raises error."""
        mock_ldap.get_by_dn.return_value = MockLdapEntry({
            "cn": "mixedgroup",
            "gidNumber": "30000",
            "member": ["uid=lastuser,ou=people,dc=example,dc=com"],  # Only one
            "memberUid": ["lastuser"],
            "objectClass": ["groupOfNames", "posixGroupAux"],
        })
        
        with pytest.raises(PosixValidationError) as exc_info:
            await service.remove_member("mixedgroup", "uid=lastuser,ou=people,dc=example,dc=com")
        
        assert "last member" in str(exc_info.value)
