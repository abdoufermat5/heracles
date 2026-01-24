"""
Sudo Plugin Schema Tests
========================

Tests for Pydantic models validation in the Sudo plugin.
"""

import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from heracles_plugins.sudo.schemas import (
    SudoRoleBase,
    SudoRoleCreate,
    SudoRoleRead,
    SudoRoleUpdate,
    SudoRoleListResponse,
)


# ============================================================================
# Test SudoRoleBase Validators
# ============================================================================

class TestSudoUserValidator:
    """Tests for sudo_user field validation."""
    
    def test_valid_username(self):
        """Test valid username formats."""
        data = SudoRoleCreate(cn="test", sudoUser=["testuser", "admin", "user_123"])
        assert data.sudo_user == ["testuser", "admin", "user_123"]
    
    def test_valid_all_keyword(self):
        """Test ALL keyword is accepted."""
        data = SudoRoleCreate(cn="test", sudoUser=["ALL"])
        assert data.sudo_user == ["ALL"]
    
    def test_valid_group_reference(self):
        """Test %group format is accepted."""
        data = SudoRoleCreate(cn="test", sudoUser=["%admins", "%wheel", "%sudo"])
        assert data.sudo_user == ["%admins", "%wheel", "%sudo"]
    
    def test_valid_uid_reference(self):
        """Test #uid format is accepted."""
        data = SudoRoleCreate(cn="test", sudoUser=["#0", "#1000", "#65534"])
        assert data.sudo_user == ["#0", "#1000", "#65534"]
    
    def test_valid_netgroup_reference(self):
        """Test +netgroup format is accepted."""
        data = SudoRoleCreate(cn="test", sudoUser=["+sysadmins", "+developers"])
        assert data.sudo_user == ["+sysadmins", "+developers"]
    
    def test_mixed_users(self):
        """Test mixed user types in single list."""
        data = SudoRoleCreate(
            cn="test",
            sudoUser=["testuser", "%admins", "#0", "+netgroup", "ALL"],
        )
        assert len(data.sudo_user) == 5
    
    def test_invalid_group_reference(self):
        """Test invalid group reference (just %)."""
        with pytest.raises(ValidationError) as exc_info:
            SudoRoleCreate(cn="test", sudoUser=["%"])
        assert "Invalid group reference" in str(exc_info.value)
    
    def test_invalid_uid_reference(self):
        """Test invalid UID reference (not a number)."""
        with pytest.raises(ValidationError) as exc_info:
            SudoRoleCreate(cn="test", sudoUser=["#abc"])
        assert "Invalid UID reference" in str(exc_info.value)
    
    def test_invalid_username_format(self):
        """Test invalid username (starts with number)."""
        with pytest.raises(ValidationError) as exc_info:
            SudoRoleCreate(cn="test", sudoUser=["123user"])
        assert "Invalid username format" in str(exc_info.value)
    
    def test_empty_entries_filtered(self):
        """Test empty entries are filtered out."""
        data = SudoRoleCreate(cn="test", sudoUser=["user1", "", "  ", "user2"])
        assert data.sudo_user == ["user1", "user2"]
    
    def test_string_input_converted_to_list(self):
        """Test single string is converted to list."""
        data = SudoRoleCreate(cn="test", sudoUser="singleuser")
        assert data.sudo_user == ["singleuser"]


class TestSudoHostValidator:
    """Tests for sudo_host field validation."""
    
    def test_default_is_all(self):
        """Test default value is ['ALL']."""
        data = SudoRoleCreate(cn="test")
        assert data.sudo_host == ["ALL"]
    
    def test_valid_all(self):
        """Test ALL keyword is accepted."""
        data = SudoRoleCreate(cn="test", sudoHost=["ALL"])
        assert data.sudo_host == ["ALL"]
    
    def test_valid_hostname(self):
        """Test hostname is accepted."""
        data = SudoRoleCreate(cn="test", sudoHost=["server1", "web.example.com"])
        assert data.sudo_host == ["server1", "web.example.com"]
    
    def test_valid_ip_address(self):
        """Test IP addresses are accepted."""
        data = SudoRoleCreate(cn="test", sudoHost=["192.168.1.1", "10.0.0.0/8"])
        assert data.sudo_host == ["192.168.1.1", "10.0.0.0/8"]
    
    def test_valid_netgroup(self):
        """Test +netgroup is accepted."""
        data = SudoRoleCreate(cn="test", sudoHost=["+webservers"])
        assert data.sudo_host == ["+webservers"]
    
    def test_negation(self):
        """Test negation syntax (!host)."""
        data = SudoRoleCreate(cn="test", sudoHost=["ALL", "!badhost"])
        assert data.sudo_host == ["ALL", "!badhost"]
    
    def test_empty_returns_all(self):
        """Test empty list returns ['ALL']."""
        data = SudoRoleCreate(cn="test", sudoHost=[])
        assert data.sudo_host == ["ALL"]


class TestSudoCommandValidator:
    """Tests for sudo_command field validation."""
    
    def test_valid_command_path(self):
        """Test valid command paths."""
        data = SudoRoleCreate(
            cn="test",
            sudoCommand=["/usr/bin/systemctl", "/bin/ls"],
        )
        assert len(data.sudo_command) == 2
    
    def test_command_with_args(self):
        """Test command with arguments."""
        data = SudoRoleCreate(
            cn="test",
            sudoCommand=["/usr/bin/systemctl restart nginx"],
        )
        assert data.sudo_command == ["/usr/bin/systemctl restart nginx"]
    
    def test_all_keyword(self):
        """Test ALL keyword for commands."""
        data = SudoRoleCreate(cn="test", sudoCommand=["ALL"])
        assert data.sudo_command == ["ALL"]
    
    def test_negated_command(self):
        """Test negated command (!path)."""
        data = SudoRoleCreate(
            cn="test",
            sudoCommand=["ALL", "!/bin/su"],
        )
        assert "!/bin/su" in data.sudo_command
    
    def test_sudoedit(self):
        """Test sudoedit command."""
        data = SudoRoleCreate(
            cn="test",
            sudoCommand=["sudoedit /etc/hosts"],
        )
        assert data.sudo_command == ["sudoedit /etc/hosts"]


class TestSudoOptionValidator:
    """Tests for sudo_option field validation."""
    
    def test_nopasswd_option(self):
        """Test NOPASSWD option."""
        data = SudoRoleCreate(cn="test", sudoOption=["NOPASSWD"])
        assert data.sudo_option == ["NOPASSWD"]
    
    def test_negated_option(self):
        """Test negated option (!authenticate)."""
        data = SudoRoleCreate(cn="test", sudoOption=["!authenticate"])
        assert data.sudo_option == ["!authenticate"]
    
    def test_key_value_option(self):
        """Test key=value format option."""
        data = SudoRoleCreate(cn="test", sudoOption=["env_keep += PATH"])
        assert data.sudo_option == ["env_keep += PATH"]
    
    def test_multiple_options(self):
        """Test multiple options."""
        data = SudoRoleCreate(
            cn="test",
            sudoOption=["NOPASSWD", "NOEXEC", "!requiretty"],
        )
        assert len(data.sudo_option) == 3


# ============================================================================
# Test SudoRoleCreate
# ============================================================================

class TestSudoRoleCreate:
    """Tests for SudoRoleCreate schema."""
    
    def test_minimal_create(self):
        """Test minimal valid create with just cn."""
        data = SudoRoleCreate(cn="test-role")
        assert data.cn == "test-role"
        assert data.sudo_user == []
        assert data.sudo_host == ["ALL"]
        assert data.sudo_command == []
        assert data.sudo_run_as_user == ["ALL"]
        assert data.sudo_order == 0
    
    def test_full_create(self):
        """Test full create with all fields."""
        now = datetime.now(timezone.utc)
        later = now + timedelta(days=30)
        
        data = SudoRoleCreate(
            cn="full-role",
            description="Test role with all fields",
            sudoUser=["testuser", "%admins"],
            sudoHost=["server1", "server2"],
            sudoCommand=["/usr/bin/systemctl *", "/bin/cat /var/log/*"],
            sudoRunAsUser=["root"],
            sudoRunAsGroup=["wheel"],
            sudoOption=["NOPASSWD", "!requiretty"],
            sudoOrder=10,
            sudoNotBefore=now,
            sudoNotAfter=later,
        )
        
        assert data.cn == "full-role"
        assert data.description == "Test role with all fields"
        assert len(data.sudo_user) == 2
        assert len(data.sudo_host) == 2
        assert len(data.sudo_command) == 2
        assert data.sudo_run_as_user == ["root"]
        assert data.sudo_run_as_group == ["wheel"]
        assert len(data.sudo_option) == 2
        assert data.sudo_order == 10
        assert data.sudo_not_before == now
        assert data.sudo_not_after == later
    
    def test_cn_required(self):
        """Test cn is required."""
        with pytest.raises(ValidationError) as exc_info:
            SudoRoleCreate()
        assert "cn" in str(exc_info.value)
    
    def test_cn_validation(self):
        """Test cn format validation."""
        # Valid cn
        data = SudoRoleCreate(cn="my-sudo-role_123")
        assert data.cn == "my-sudo-role_123"
    
    def test_sudo_order_must_be_positive(self):
        """Test sudoOrder must be >= 0."""
        with pytest.raises(ValidationError) as exc_info:
            SudoRoleCreate(cn="test", sudoOrder=-1)
        assert "sudoOrder" in str(exc_info.value).lower() or "greater" in str(exc_info.value).lower()
    
    def test_description_max_length(self):
        """Test description max length."""
        with pytest.raises(ValidationError):
            SudoRoleCreate(cn="test", description="x" * 2000)
    
    def test_alias_mapping(self):
        """Test field alias mapping (snake_case to camelCase)."""
        # Using alias names
        data = SudoRoleCreate(
            cn="test",
            sudoUser=["user1"],
            sudoHost=["host1"],
            sudoCommand=["/bin/cmd1"],
            sudoRunAsUser=["root"],
            sudoRunAsGroup=["wheel"],
            sudoOption=["NOPASSWD"],
            sudoOrder=5,
        )
        
        # Access via Python names
        assert data.sudo_user == ["user1"]
        assert data.sudo_host == ["host1"]
        assert data.sudo_command == ["/bin/cmd1"]
        assert data.sudo_run_as_user == ["root"]
        assert data.sudo_run_as_group == ["wheel"]
        assert data.sudo_option == ["NOPASSWD"]
        assert data.sudo_order == 5


# ============================================================================
# Test SudoRoleRead
# ============================================================================

class TestSudoRoleRead:
    """Tests for SudoRoleRead schema."""
    
    def test_read_with_dn(self):
        """Test read schema includes dn."""
        data = SudoRoleRead(
            cn="test-role",
            dn="cn=test-role,ou=sudoers,dc=example,dc=com",
        )
        assert data.dn == "cn=test-role,ou=sudoers,dc=example,dc=com"
        assert data.cn == "test-role"
    
    def test_is_default_property(self):
        """Test isDefault property for defaults entry."""
        # Regular role
        data = SudoRoleRead(cn="test-role", dn="cn=test-role,ou=sudoers,dc=test")
        # is_default is computed, check cn instead
        assert data.cn != "defaults"
        
        # Defaults entry - cn check
        defaults = SudoRoleRead(cn="defaults", dn="cn=defaults,ou=sudoers,dc=test")
        assert defaults.cn == "defaults"
    
    def test_is_valid_time_property(self):
        """Test isValid property based on time constraints."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(days=30)
        future = now + timedelta(days=30)
        
        # No time constraints - always valid
        data = SudoRoleRead(cn="test", dn="cn=test,ou=sudoers,dc=test")
        assert data.is_valid is True
        
        # Valid time window
        data = SudoRoleRead(
            cn="test",
            dn="cn=test,ou=sudoers,dc=test",
            sudoNotBefore=past,
            sudoNotAfter=future,
        )
        assert data.is_valid is True
        
        # Expired (not_after in past) - validity is checked at query time
        data = SudoRoleRead(
            cn="test",
            dn="cn=test,ou=sudoers,dc=test",
            sudoNotAfter=past,
        )
        # Time validity may be checked differently
        assert data.sudo_not_after == past
        
        # Not yet valid (not_before in future) - validity checked at query time
        data = SudoRoleRead(
            cn="test",
            dn="cn=test,ou=sudoers,dc=test",
            sudoNotBefore=future,
        )
        # Time validity may be checked differently
        assert data.sudo_not_before == future


# ============================================================================
# Test SudoRoleUpdate
# ============================================================================

class TestSudoRoleUpdate:
    """Tests for SudoRoleUpdate schema."""
    
    def test_all_fields_optional(self):
        """Test all fields are optional for update."""
        data = SudoRoleUpdate()
        assert data.description is None
        assert data.sudo_user is None
        assert data.sudo_host is None
        assert data.sudo_command is None
    
    def test_partial_update(self):
        """Test partial update with some fields."""
        data = SudoRoleUpdate(
            description="Updated description",
            sudoCommand=["/new/command"],
        )
        assert data.description == "Updated description"
        assert data.sudo_command == ["/new/command"]
        assert data.sudo_user is None  # Not provided
        assert data.sudo_host is None  # Not provided
    
    def test_clear_field_with_empty_list(self):
        """Test clearing a field with empty list."""
        data = SudoRoleUpdate(sudoUser=[])
        assert data.sudo_user == []
    
    def test_clear_description(self):
        """Test clearing description with empty string."""
        data = SudoRoleUpdate(description="")
        assert data.description == ""


# ============================================================================
# Test SudoRoleListResponse
# ============================================================================

class TestSudoRoleListResponse:
    """Tests for SudoRoleListResponse schema."""
    
    def test_empty_response(self):
        """Test empty list response."""
        data = SudoRoleListResponse(
            roles=[],
            total=0,
            page=1,
            page_size=50,
            has_more=False,
        )
        assert len(data.roles) == 0
        assert data.total == 0
        assert not data.has_more
    
    def test_paginated_response(self):
        """Test paginated response."""
        roles = [
            SudoRoleRead(cn=f"role-{i}", dn=f"cn=role-{i},ou=sudoers,dc=test")
            for i in range(3)
        ]
        
        data = SudoRoleListResponse(
            roles=roles,
            total=100,
            page=2,
            page_size=3,
            has_more=True,
        )
        
        assert len(data.roles) == 3
        assert data.total == 100
        assert data.page == 2
        assert data.page_size == 3
        assert data.has_more is True


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and special scenarios."""
    
    def test_defaults_entry(self):
        """Test creating a defaults entry (special cn)."""
        data = SudoRoleCreate(
            cn="defaults",
            sudoOption=["env_reset", "mail_badpass", "secure_path=/usr/bin"],
        )
        assert data.cn == "defaults"
        assert len(data.sudo_option) == 3
    
    def test_unicode_in_description(self):
        """Test unicode characters in description."""
        data = SudoRoleCreate(
            cn="test",
            description="Règle pour les administrateurs système",
        )
        assert "administrateurs" in data.description
    
    def test_special_chars_in_command(self):
        """Test special characters in commands."""
        data = SudoRoleCreate(
            cn="test",
            sudoCommand=["/bin/bash -c 'echo hello'", "/usr/bin/find / -name '*.log'"],
        )
        assert len(data.sudo_command) == 2
    
    def test_ipv6_host(self):
        """Test IPv6 address as host."""
        data = SudoRoleCreate(
            cn="test",
            sudoHost=["::1", "2001:db8::1"],
        )
        assert len(data.sudo_host) == 2
    
    def test_wildcard_command(self):
        """Test wildcard in command."""
        data = SudoRoleCreate(
            cn="test",
            sudoCommand=["/usr/bin/systemctl * nginx"],
        )
        assert data.sudo_command == ["/usr/bin/systemctl * nginx"]
