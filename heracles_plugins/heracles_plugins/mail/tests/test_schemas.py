"""
Mail Plugin Schema Tests
========================

Unit tests for mail account Pydantic schemas.
"""

import pytest
from pydantic import ValidationError

from heracles_plugins.mail.schemas import (
    MailAccountCreate,
    MailAccountRead,
    MailAccountUpdate,
    MailGroupCreate,
    MailGroupRead,
    MailGroupUpdate,
    UserMailStatus,
    GroupMailStatus,
    DeliveryMode,
)


# ============================================================================
# MailAccountCreate Tests
# ============================================================================


class TestMailAccountCreate:
    """Tests for MailAccountCreate schema."""

    def test_valid_minimal(self):
        """Test creation with minimal required fields."""
        data = MailAccountCreate(mail="user@example.com")
        assert data.mail == "user@example.com"
        assert data.mail_server is None
        assert data.quota_mb is None
        assert data.alternate_addresses == []
        assert data.forwarding_addresses == []

    def test_valid_full(self):
        """Test creation with all fields."""
        data = MailAccountCreate(
            mail="user@example.com",
            mailServer="mail.example.com",
            quotaMb=1024,
            alternateAddresses=["alias@example.com"],
            forwardingAddresses=["forward@external.com"],
        )
        assert data.mail == "user@example.com"
        assert data.mail_server == "mail.example.com"
        assert data.quota_mb == 1024
        assert data.alternate_addresses == ["alias@example.com"]
        assert data.forwarding_addresses == ["forward@external.com"]

    def test_invalid_email(self):
        """Test with invalid email address."""
        with pytest.raises(ValidationError) as exc_info:
            MailAccountCreate(mail="not-an-email")
        assert "mail" in str(exc_info.value)

    def test_invalid_mail_server(self):
        """Test with invalid mail server hostname."""
        with pytest.raises(ValidationError) as exc_info:
            MailAccountCreate(mail="user@example.com", mailServer="not a hostname!")
        assert "mail_server" in str(exc_info.value).lower() or "mailServer" in str(
            exc_info.value
        )

    def test_invalid_quota_negative(self):
        """Test with negative quota."""
        with pytest.raises(ValidationError) as exc_info:
            MailAccountCreate(mail="user@example.com", quotaMb=-1)
        assert "quota" in str(exc_info.value).lower()

    def test_mail_server_normalized(self):
        """Test mail server is normalized to lowercase."""
        data = MailAccountCreate(mail="user@example.com", mailServer="MAIL.EXAMPLE.COM")
        assert data.mail_server == "mail.example.com"


# ============================================================================
# MailAccountUpdate Tests
# ============================================================================


class TestMailAccountUpdate:
    """Tests for MailAccountUpdate schema."""

    def test_all_optional(self):
        """Test that all fields are optional."""
        data = MailAccountUpdate()
        assert data.mail is None
        assert data.mail_server is None
        assert data.quota_mb is None

    def test_vacation_dates_valid(self):
        """Test valid vacation dates."""
        data = MailAccountUpdate(
            vacationStart="20260101",
            vacationEnd="20260115",
        )
        assert data.vacation_start == "20260101"
        assert data.vacation_end == "20260115"

    def test_vacation_dates_invalid_format(self):
        """Test invalid vacation date format."""
        with pytest.raises(ValidationError) as exc_info:
            MailAccountUpdate(vacationStart="2026-01-01")
        assert "date" in str(exc_info.value).lower()

    def test_vacation_dates_invalid_date(self):
        """Test invalid vacation date (Feb 30)."""
        with pytest.raises(ValidationError) as exc_info:
            MailAccountUpdate(vacationStart="20260230")
        assert "date" in str(exc_info.value).lower()

    def test_vacation_dates_start_after_end(self):
        """Test vacation start after end."""
        with pytest.raises(ValidationError) as exc_info:
            MailAccountUpdate(
                vacationStart="20260115",
                vacationEnd="20260101",
            )
        assert "start" in str(exc_info.value).lower() or "end" in str(exc_info.value).lower()

    def test_delivery_mode_values(self):
        """Test delivery mode enum values."""
        for mode in ["normal", "forward_only", "local_only"]:
            data = MailAccountUpdate(deliveryMode=mode)
            assert data.delivery_mode == mode


# ============================================================================
# MailAccountRead Tests
# ============================================================================


class TestMailAccountRead:
    """Tests for MailAccountRead schema."""

    def test_serialization(self):
        """Test JSON serialization with aliases."""
        data = MailAccountRead(
            mail="user@example.com",
            mailServer="mail.example.com",
            quotaMb=1024,
            quotaUsedMb=512,
            alternateAddresses=["alias@example.com"],
            forwardingAddresses=[],
            deliveryMode=DeliveryMode.NORMAL,
            vacationEnabled=False,
        )

        json_dict = data.model_dump(by_alias=True)
        assert json_dict["mail"] == "user@example.com"
        assert json_dict["mailServer"] == "mail.example.com"
        assert json_dict["quotaMb"] == 1024
        assert json_dict["quotaUsedMb"] == 512
        assert json_dict["alternateAddresses"] == ["alias@example.com"]
        assert json_dict["deliveryMode"] == "normal"
        assert json_dict["vacationEnabled"] is False


# ============================================================================
# MailGroupCreate Tests
# ============================================================================


class TestMailGroupCreate:
    """Tests for MailGroupCreate schema."""

    def test_valid_minimal(self):
        """Test creation with minimal fields."""
        data = MailGroupCreate(mail="group@example.com")
        assert data.mail == "group@example.com"
        assert data.local_only is False
        assert data.max_message_size_kb is None

    def test_valid_full(self):
        """Test creation with all fields."""
        data = MailGroupCreate(
            mail="team@example.com",
            mailServer="mail.example.com",
            alternateAddresses=["team-alias@example.com"],
            forwardingAddresses=["external@other.com"],
            localOnly=True,
            maxMessageSizeKb=10240,
        )
        assert data.mail == "team@example.com"
        assert data.local_only is True
        assert data.max_message_size_kb == 10240

    def test_invalid_max_size_too_large(self):
        """Test max message size exceeds limit."""
        with pytest.raises(ValidationError) as exc_info:
            MailGroupCreate(mail="group@example.com", maxMessageSizeKb=200000)
        assert "max" in str(exc_info.value).lower()


# ============================================================================
# MailGroupRead Tests
# ============================================================================


class TestMailGroupRead:
    """Tests for MailGroupRead schema."""

    def test_with_members(self):
        """Test with member emails."""
        data = MailGroupRead(
            mail="team@example.com",
            alternateAddresses=[],
            forwardingAddresses=[],
            localOnly=False,
            memberEmails=["user1@example.com", "user2@example.com"],
        )
        assert len(data.member_emails) == 2
        assert "user1@example.com" in data.member_emails

    def test_serialization(self):
        """Test JSON serialization."""
        data = MailGroupRead(
            mail="team@example.com",
            mailServer="mail.example.com",
            alternateAddresses=["alias@example.com"],
            forwardingAddresses=[],
            localOnly=True,
            maxMessageSizeKb=5120,
            memberEmails=["member@example.com"],
        )

        json_dict = data.model_dump(by_alias=True)
        assert json_dict["mail"] == "team@example.com"
        assert json_dict["localOnly"] is True
        assert json_dict["maxMessageSizeKb"] == 5120
        assert json_dict["memberEmails"] == ["member@example.com"]


# ============================================================================
# MailGroupUpdate Tests
# ============================================================================


class TestMailGroupUpdate:
    """Tests for MailGroupUpdate schema."""

    def test_all_optional(self):
        """Test all fields are optional."""
        data = MailGroupUpdate()
        assert data.mail is None
        assert data.local_only is None
        assert data.max_message_size_kb is None

    def test_partial_update(self):
        """Test partial update."""
        data = MailGroupUpdate(localOnly=True)
        assert data.local_only is True
        assert data.mail is None

# ============================================================================
# UserMailStatus Tests
# ============================================================================


class TestUserMailStatus:
    """Tests for UserMailStatus schema."""

    def test_inactive_status(self):
        """Test user mail status when inactive."""
        status = UserMailStatus(
            uid="testuser",
            dn="uid=testuser,ou=people,dc=example,dc=com",
            active=False,
            data=None,
        )
        assert status.uid == "testuser"
        assert status.active is False
        assert status.data is None

    def test_active_status(self):
        """Test user mail status when active."""
        data = MailAccountRead(
            mail="user@example.com",
            alternateAddresses=[],
            forwardingAddresses=[],
            deliveryMode=DeliveryMode.NORMAL,
            vacationEnabled=False,
        )
        status = UserMailStatus(
            uid="testuser",
            dn="uid=testuser,ou=people,dc=example,dc=com",
            active=True,
            data=data,
        )
        assert status.active is True
        assert status.data is not None
        assert status.data.mail == "user@example.com"

    def test_serialization_with_aliases(self):
        """Test JSON serialization uses camelCase aliases."""
        data = MailAccountRead(
            mail="user@example.com",
            mailServer="mail.example.com",
            quotaMb=1024,
            alternateAddresses=["alias@example.com"],
            forwardingAddresses=[],
            deliveryMode=DeliveryMode.FORWARD_ONLY,
            vacationEnabled=True,
            vacationMessage="Away",
        )
        status = UserMailStatus(
            uid="testuser",
            dn="uid=testuser,ou=people,dc=example,dc=com",
            active=True,
            data=data,
        )
        json_dict = status.model_dump(by_alias=True)
        assert json_dict["data"]["mailServer"] == "mail.example.com"
        assert json_dict["data"]["deliveryMode"] == "forward_only"
        assert json_dict["data"]["vacationEnabled"] is True


# ============================================================================
# GroupMailStatus Tests
# ============================================================================


class TestGroupMailStatus:
    """Tests for GroupMailStatus schema."""

    def test_inactive_status(self):
        """Test group mail status when inactive."""
        status = GroupMailStatus(
            cn="testgroup",
            dn="cn=testgroup,ou=groups,dc=example,dc=com",
            active=False,
            data=None,
        )
        assert status.cn == "testgroup"
        assert status.active is False
        assert status.data is None

    def test_active_status_with_members(self):
        """Test group mail status when active with member emails."""
        data = MailGroupRead(
            mail="team@example.com",
            alternateAddresses=["team-alias@example.com"],
            forwardingAddresses=[],
            localOnly=True,
            memberEmails=["user1@example.com", "user2@example.com"],
        )
        status = GroupMailStatus(
            cn="testgroup",
            dn="cn=testgroup,ou=groups,dc=example,dc=com",
            active=True,
            data=data,
        )
        assert status.active is True
        assert len(status.data.member_emails) == 2
        assert "user1@example.com" in status.data.member_emails

    def test_serialization(self):
        """Test JSON serialization."""
        data = MailGroupRead(
            mail="team@example.com",
            alternateAddresses=[],
            forwardingAddresses=["external@other.com"],
            localOnly=False,
            maxMessageSizeKb=5120,
            memberEmails=[],
        )
        status = GroupMailStatus(
            cn="testgroup",
            dn="cn=testgroup,ou=groups,dc=example,dc=com",
            active=True,
            data=data,
        )
        json_dict = status.model_dump(by_alias=True)
        assert json_dict["cn"] == "testgroup"
        assert json_dict["data"]["maxMessageSizeKb"] == 5120
        assert json_dict["data"]["forwardingAddresses"] == ["external@other.com"]


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_quota_zero(self):
        """Test quota can be zero (unlimited)."""
        data = MailAccountCreate(mail="user@example.com", quotaMb=0)
        assert data.quota_mb == 0

    def test_quota_max_value(self):
        """Test maximum quota value."""
        data = MailAccountCreate(mail="user@example.com", quotaMb=1048576)
        assert data.quota_mb == 1048576

    def test_quota_over_max(self):
        """Test quota exceeding maximum is rejected."""
        with pytest.raises(ValidationError):
            MailAccountCreate(mail="user@example.com", quotaMb=1048577)

    def test_empty_alternate_addresses(self):
        """Test empty alternate addresses list."""
        data = MailAccountCreate(
            mail="user@example.com",
            alternateAddresses=[],
        )
        assert data.alternate_addresses == []

    def test_multiple_alternate_addresses(self):
        """Test multiple alternate addresses."""
        data = MailAccountCreate(
            mail="user@example.com",
            alternateAddresses=[
                "alias1@example.com",
                "alias2@example.com",
                "alias3@example.com",
            ],
        )
        assert len(data.alternate_addresses) == 3

    def test_empty_mail_server(self):
        """Test empty mail server is converted to None."""
        data = MailAccountCreate(mail="user@example.com", mailServer="")
        assert data.mail_server is None

    def test_mail_server_with_subdomain(self):
        """Test mail server with subdomain."""
        data = MailAccountCreate(mail="user@example.com", mailServer="smtp.mail.example.com")
        assert data.mail_server == "smtp.mail.example.com"

    def test_delivery_mode_enum_values(self):
        """Test all delivery mode enum values."""
        assert DeliveryMode.NORMAL.value == "normal"
        assert DeliveryMode.FORWARD_ONLY.value == "forward_only"
        assert DeliveryMode.LOCAL_ONLY.value == "local_only"

    def test_vacation_dates_same_day(self):
        """Test vacation start and end on same day."""
        data = MailAccountUpdate(
            vacationStart="20260115",
            vacationEnd="20260115",
        )
        assert data.vacation_start == "20260115"
        assert data.vacation_end == "20260115"