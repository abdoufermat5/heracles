"""
POSIX Plugin Schema Tests
=========================

Tests for Pydantic models validation in the POSIX plugin.
"""

import pytest
from pydantic import ValidationError

from heracles_plugins.posix.schemas import (
    # Enums
    TrustMode,
    AccountStatus,
    PrimaryGroupMode,
    # User POSIX
    PosixAccountCreate,
    PosixAccountRead,
    PosixAccountUpdate,
    # POSIX Group
    PosixGroupCreate,
    PosixGroupFullCreate,
    PosixGroupRead,
    PosixGroupUpdate,
    # MixedGroup
    MixedGroupCreate,
    MixedGroupRead,
    MixedGroupUpdate,
    # Response schemas
    PosixStatusResponse,
    AvailableShellsResponse,
    IdAllocationResponse,
)


# ============================================================================
# Test Enums
# ============================================================================

class TestEnums:
    """Tests for POSIX-related enums."""
    
    def test_trust_mode_values(self):
        """Test TrustMode enum values."""
        assert TrustMode.FULL_ACCESS.value == "fullaccess"
        assert TrustMode.BY_HOST.value == "byhost"
    
    def test_account_status_values(self):
        """Test AccountStatus enum values."""
        assert AccountStatus.ACTIVE.value == "active"
        assert AccountStatus.EXPIRED.value == "expired"
        assert AccountStatus.PASSWORD_EXPIRED.value == "password_expired"
        assert AccountStatus.GRACE_TIME.value == "grace_time"
        assert AccountStatus.LOCKED.value == "locked"
    
    def test_primary_group_mode_values(self):
        """Test PrimaryGroupMode enum values."""
        assert PrimaryGroupMode.SELECT_EXISTING.value == "select_existing"
        assert PrimaryGroupMode.CREATE_PERSONAL.value == "create_personal"


# ============================================================================
# Test PosixAccountCreate
# ============================================================================

class TestPosixAccountCreate:
    """Tests for PosixAccountCreate schema."""
    
    def test_minimal_create_with_existing_group(self):
        """Test minimal valid create with existing group."""
        data = PosixAccountCreate(
            primaryGroupMode=PrimaryGroupMode.SELECT_EXISTING,
            gidNumber=10000,
        )
        assert data.primary_group_mode == PrimaryGroupMode.SELECT_EXISTING
        assert data.gid_number == 10000
        assert data.uid_number is None  # Auto-allocate
        assert data.force_uid is False
        assert data.login_shell == "/bin/bash"
    
    def test_create_personal_group_mode(self):
        """Test create with personal group mode (no gidNumber required)."""
        data = PosixAccountCreate(
            primaryGroupMode=PrimaryGroupMode.CREATE_PERSONAL,
        )
        assert data.primary_group_mode == PrimaryGroupMode.CREATE_PERSONAL
        assert data.gid_number is None
    
    def test_select_existing_requires_gid(self):
        """Test that select_existing mode requires gidNumber."""
        with pytest.raises(ValidationError) as exc_info:
            PosixAccountCreate(
                primaryGroupMode=PrimaryGroupMode.SELECT_EXISTING,
                # Missing gidNumber
            )
        assert "gidNumber is required" in str(exc_info.value)
    
    def test_home_directory_validation(self):
        """Test home directory path validation."""
        # Valid path
        data = PosixAccountCreate(
            primaryGroupMode=PrimaryGroupMode.SELECT_EXISTING,
            gidNumber=10000,
            homeDirectory="/home/testuser",
        )
        assert data.home_directory == "/home/testuser"
        
        # Invalid: not absolute path
        with pytest.raises(ValidationError):
            PosixAccountCreate(
                primaryGroupMode=PrimaryGroupMode.SELECT_EXISTING,
                gidNumber=10000,
                homeDirectory="home/testuser",
            )
    
    def test_trust_mode_byhost_requires_hosts(self):
        """Test that byhost trust mode requires host list."""
        with pytest.raises(ValidationError) as exc_info:
            PosixAccountCreate(
                primaryGroupMode=PrimaryGroupMode.SELECT_EXISTING,
                gidNumber=10000,
                trustMode=TrustMode.BY_HOST,
                # Missing host list
            )
        assert "host list is required" in str(exc_info.value)
    
    def test_trust_mode_fullaccess_no_hosts_needed(self):
        """Test that fullaccess trust mode doesn't require hosts."""
        data = PosixAccountCreate(
            primaryGroupMode=PrimaryGroupMode.SELECT_EXISTING,
            gidNumber=10000,
            trustMode=TrustMode.FULL_ACCESS,
        )
        assert data.trust_mode == TrustMode.FULL_ACCESS
        assert data.host is None
    
    def test_trust_mode_byhost_with_hosts(self):
        """Test byhost trust mode with hosts."""
        data = PosixAccountCreate(
            primaryGroupMode=PrimaryGroupMode.SELECT_EXISTING,
            gidNumber=10000,
            trustMode=TrustMode.BY_HOST,
            host=["server1.example.com", "server2.example.com"],
        )
        assert data.trust_mode == TrustMode.BY_HOST
        assert data.host == ["server1.example.com", "server2.example.com"]
    
    def test_uid_gid_ranges(self):
        """Test UID/GID number range validation."""
        # Valid
        data = PosixAccountCreate(
            primaryGroupMode=PrimaryGroupMode.SELECT_EXISTING,
            gidNumber=10000,
            uidNumber=10001,
        )
        assert data.uid_number == 10001
        
        # Too low
        with pytest.raises(ValidationError):
            PosixAccountCreate(
                primaryGroupMode=PrimaryGroupMode.SELECT_EXISTING,
                gidNumber=10000,
                uidNumber=999,  # Below minimum
            )
        
        # Too high
        with pytest.raises(ValidationError):
            PosixAccountCreate(
                primaryGroupMode=PrimaryGroupMode.SELECT_EXISTING,
                gidNumber=10000,
                uidNumber=70000,  # Above maximum
            )


# ============================================================================
# Test PosixAccountRead
# ============================================================================

class TestPosixAccountRead:
    """Tests for PosixAccountRead schema."""
    
    def test_read_full_data(self):
        """Test reading full POSIX account data."""
        data = PosixAccountRead(
            uidNumber=10001,
            gidNumber=10000,
            homeDirectory="/home/testuser",
            loginShell="/bin/zsh",
            gecos="Test User",
            shadowLastChange=19500,
            shadowMin=0,
            shadowMax=99999,
            shadowWarning=7,
            shadowInactive=-1,
            shadowExpire=None,
            trustMode=TrustMode.BY_HOST,
            host=["server1"],
            primaryGroupCn="users",
            groupMemberships=["developers", "admins"],
            accountStatus=AccountStatus.ACTIVE,
        )
        
        assert data.uid_number == 10001
        assert data.gid_number == 10000
        assert data.login_shell == "/bin/zsh"
        assert data.trust_mode == TrustMode.BY_HOST
        assert data.host == ["server1"]
        assert data.primary_group_cn == "users"
        assert data.group_memberships == ["developers", "admins"]
        assert data.account_status == AccountStatus.ACTIVE
        assert data.is_active is True
    
    def test_read_minimal_data(self):
        """Test reading minimal POSIX account data."""
        data = PosixAccountRead(
            uidNumber=10001,
            gidNumber=10000,
            homeDirectory="/home/testuser",
        )
        
        assert data.login_shell == "/bin/bash"  # Default
        assert data.gecos is None
        assert data.trust_mode is None
        assert data.account_status == AccountStatus.ACTIVE


# ============================================================================
# Test PosixAccountUpdate
# ============================================================================

class TestPosixAccountUpdate:
    """Tests for PosixAccountUpdate schema."""
    
    def test_update_single_field(self):
        """Test updating single field."""
        data = PosixAccountUpdate(loginShell="/bin/zsh")
        assert data.login_shell == "/bin/zsh"
        assert data.gid_number is None
        assert data.home_directory is None
    
    def test_update_shadow_settings(self):
        """Test updating shadow settings."""
        data = PosixAccountUpdate(
            shadowMin=1,
            shadowMax=90,
            shadowWarning=14,
        )
        assert data.shadow_min == 1
        assert data.shadow_max == 90
        assert data.shadow_warning == 14
    
    def test_shadow_min_max_validation(self):
        """Test that shadowMin cannot be greater than shadowMax."""
        with pytest.raises(ValidationError):
            PosixAccountUpdate(
                shadowMin=100,
                shadowMax=50,  # Less than min
            )
    
    def test_update_must_change_password(self):
        """Test must change password flag."""
        data = PosixAccountUpdate(mustChangePassword=True)
        assert data.must_change_password is True
    
    def test_update_trust_mode(self):
        """Test updating trust mode."""
        data = PosixAccountUpdate(
            trustMode=TrustMode.BY_HOST,
            host=["newserver.example.com"],
        )
        assert data.trust_mode == TrustMode.BY_HOST
        assert data.host == ["newserver.example.com"]


# ============================================================================
# Test PosixGroupFullCreate
# ============================================================================

class TestPosixGroupFullCreate:
    """Tests for PosixGroupFullCreate schema."""
    
    def test_minimal_create(self):
        """Test minimal valid group create."""
        data = PosixGroupFullCreate(cn="developers")
        assert data.cn == "developers"
        assert data.gid_number is None  # Auto-allocate
        assert data.force_gid is False
        assert data.description is None
        assert data.member_uid is None
        assert data.trust_mode is None
    
    def test_full_create(self):
        """Test full group create."""
        data = PosixGroupFullCreate(
            cn="developers",
            gidNumber=20000,
            forceGid=True,
            description="Development team",
            memberUid=["user1", "user2"],
            trustMode=TrustMode.BY_HOST,
            host=["devserver.example.com"],
        )
        assert data.cn == "developers"
        assert data.gid_number == 20000
        assert data.force_gid is True
        assert data.description == "Development team"
        assert data.member_uid == ["user1", "user2"]
        assert data.trust_mode == TrustMode.BY_HOST
        assert data.host == ["devserver.example.com"]
    
    def test_cn_validation(self):
        """Test group name (cn) validation."""
        # Valid names
        for cn in ["developers", "dev-team", "dev_team", "Team1"]:
            data = PosixGroupFullCreate(cn=cn)
            assert data.cn == cn
        
        # Invalid: starts with number
        with pytest.raises(ValidationError):
            PosixGroupFullCreate(cn="1developers")
        
        # Invalid: contains space
        with pytest.raises(ValidationError):
            PosixGroupFullCreate(cn="dev team")
        
        # Invalid: special characters
        with pytest.raises(ValidationError):
            PosixGroupFullCreate(cn="dev@team")
    
    def test_trust_mode_byhost_requires_hosts(self):
        """Test that byhost trust mode requires host list."""
        with pytest.raises(ValidationError) as exc_info:
            PosixGroupFullCreate(
                cn="testgroup",
                trustMode=TrustMode.BY_HOST,
                # Missing host list
            )
        assert "host list is required" in str(exc_info.value)


# ============================================================================
# Test PosixGroupRead
# ============================================================================

class TestPosixGroupRead:
    """Tests for PosixGroupRead schema."""
    
    def test_read_full_data(self):
        """Test reading full POSIX group data."""
        data = PosixGroupRead(
            cn="developers",
            gidNumber=20000,
            description="Development team",
            memberUid=["user1", "user2"],
            trustMode=TrustMode.BY_HOST,
            host=["devserver"],
        )
        
        assert data.cn == "developers"
        assert data.gid_number == 20000
        assert data.description == "Development team"
        assert data.member_uid == ["user1", "user2"]
        assert data.trust_mode == TrustMode.BY_HOST
        assert data.host == ["devserver"]
        assert data.is_active is True
    
    def test_read_minimal_data(self):
        """Test reading minimal POSIX group data."""
        data = PosixGroupRead(
            cn="testgroup",
            gidNumber=20000,
        )
        
        assert data.member_uid == []  # Default empty list
        assert data.trust_mode is None
        assert data.host is None


# ============================================================================
# Test PosixGroupUpdate
# ============================================================================

class TestPosixGroupUpdate:
    """Tests for PosixGroupUpdate schema."""
    
    def test_update_description(self):
        """Test updating group description."""
        data = PosixGroupUpdate(description="Updated description")
        assert data.description == "Updated description"
    
    def test_update_members(self):
        """Test updating group members."""
        data = PosixGroupUpdate(memberUid=["user1", "user2", "user3"])
        assert data.member_uid == ["user1", "user2", "user3"]
    
    def test_update_trust_mode(self):
        """Test updating group trust mode."""
        data = PosixGroupUpdate(
            trustMode=TrustMode.FULL_ACCESS,
        )
        assert data.trust_mode == TrustMode.FULL_ACCESS


# ============================================================================
# Test MixedGroupCreate
# ============================================================================

class TestMixedGroupCreate:
    """Tests for MixedGroupCreate schema."""
    
    def test_minimal_create(self):
        """Test minimal mixed group create."""
        data = MixedGroupCreate(cn="mixedgroup")
        assert data.cn == "mixedgroup"
        assert data.gid_number is None
        assert data.force_gid is False
        assert data.member is None
        assert data.member_uid is None
    
    def test_full_create(self):
        """Test full mixed group create."""
        data = MixedGroupCreate(
            cn="mixedgroup",
            gidNumber=30000,
            forceGid=True,
            description="Mixed group for team",
            member=["uid=user1,ou=people,dc=example,dc=com"],
            memberUid=["user1"],
            trustMode=TrustMode.FULL_ACCESS,
        )
        assert data.cn == "mixedgroup"
        assert data.gid_number == 30000
        assert data.force_gid is True
        assert len(data.member) == 1
        assert data.member_uid == ["user1"]
        assert data.trust_mode == TrustMode.FULL_ACCESS


# ============================================================================
# Test MixedGroupRead
# ============================================================================

class TestMixedGroupRead:
    """Tests for MixedGroupRead schema."""
    
    def test_read_full_data(self):
        """Test reading full mixed group data."""
        data = MixedGroupRead(
            cn="mixedgroup",
            gidNumber=30000,
            description="Mixed group",
            member=["uid=user1,dc=example,dc=com"],
            memberUid=["user1"],
            trustMode=TrustMode.BY_HOST,
            host=["server1"],
        )
        
        assert data.cn == "mixedgroup"
        assert data.gid_number == 30000
        assert data.member == ["uid=user1,dc=example,dc=com"]
        assert data.member_uid == ["user1"]
        assert data.trust_mode == TrustMode.BY_HOST
        assert data.host == ["server1"]
        assert data.is_mixed_group is True


# ============================================================================
# Test Response Schemas
# ============================================================================

class TestResponseSchemas:
    """Tests for API response schemas."""
    
    def test_posix_status_response_active(self):
        """Test POSIX status response when active."""
        account_data = PosixAccountRead(
            uidNumber=10001,
            gidNumber=10000,
            homeDirectory="/home/test",
        )
        response = PosixStatusResponse(active=True, data=account_data)
        assert response.active is True
        assert response.data is not None
        assert response.data.uid_number == 10001
    
    def test_posix_status_response_inactive(self):
        """Test POSIX status response when inactive."""
        response = PosixStatusResponse(active=False, data=None)
        assert response.active is False
        assert response.data is None
    
    def test_available_shells_response(self):
        """Test available shells response."""
        response = AvailableShellsResponse(
            shells=[
                {"value": "/bin/bash", "label": "Bash"},
                {"value": "/bin/zsh", "label": "Zsh"},
            ],
            default="/bin/bash",
        )
        assert len(response.shells) == 2
        assert response.default == "/bin/bash"
    
    def test_id_allocation_response(self):
        """Test ID allocation response."""
        response = IdAllocationResponse(
            next_uid=10001,
            next_gid=20001,
            uid_range={"min": 10000, "max": 60000},
            gid_range={"min": 10000, "max": 60000},
        )
        assert response.next_uid == 10001
        assert response.next_gid == 20001
        assert response.uid_range["min"] == 10000
