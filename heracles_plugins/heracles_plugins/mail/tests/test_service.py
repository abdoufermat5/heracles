"""
Mail Plugin Service Tests
=========================

Integration tests for mail account services.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from heracles_plugins.mail.service.mail_user_service import MailUserService
from heracles_plugins.mail.service.mail_group_service import MailGroupService
from heracles_plugins.mail.service.base import (
    MailValidationError,
    MailAlreadyExistsError,
)
from heracles_plugins.mail.schemas import (
    MailAccountCreate,
    MailAccountUpdate,
    MailGroupCreate,
    MailGroupUpdate,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_ldap_service():
    """Create a mock LDAP service."""
    ldap = AsyncMock()
    return ldap


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.LDAP_BASE_DN = "dc=example,dc=com"
    return settings


@pytest.fixture
def mail_user_service(mock_ldap_service):
    """Create a MailUserService with mock LDAP."""
    config = {
        "default_mail_server": "mail.example.com",
        "default_quota_mb": 1024,
        "mail_domain": "example.com",
    }
    return MailUserService(mock_ldap_service, config)


@pytest.fixture
def mail_group_service(mock_ldap_service):
    """Create a MailGroupService with mock LDAP."""
    config = {
        "default_mail_server": "mail.example.com",
    }
    return MailGroupService(mock_ldap_service, config)


# ============================================================================
# MailUserService Tests
# ============================================================================


class TestMailUserService:
    """Tests for MailUserService."""

    @pytest.mark.asyncio
    async def test_get_status_inactive(self, mail_user_service, mock_ldap_service, mock_settings):
        """Test getting status for user without mail."""
        user_dn = "uid=testuser,ou=people,dc=example,dc=com"
        mock_ldap_service.search.return_value = [MagicMock(dn=user_dn)]
        mock_ldap_service.get_by_dn.return_value = {
            "objectClass": ["inetOrgPerson", "posixAccount"],
            "uid": ["testuser"],
        }

        with patch("heracles_api.config.settings", mock_settings):
            status = await mail_user_service.get_user_mail_status("testuser")

        assert status.uid == "testuser"
        assert status.active is False
        assert status.data is None

    @pytest.mark.asyncio
    async def test_get_status_active(self, mail_user_service, mock_ldap_service, mock_settings):
        """Test getting status for user with mail."""
        user_dn = "uid=testuser,ou=people,dc=example,dc=com"
        mock_ldap_service.search.return_value = [MagicMock(dn=user_dn)]
        mock_ldap_service.get_by_dn.return_value = {
            "objectClass": ["inetOrgPerson", "hrcMailAccount"],
            "mail": ["user@example.com"],
            "hrcMailServer": ["mail.example.com"],
            "hrcMailQuota": ["1024"],
            "hrcMailDeliveryMode": [""],
        }

        with patch("heracles_api.config.settings", mock_settings):
            status = await mail_user_service.get_user_mail_status("testuser")

        assert status.active is True
        assert status.data is not None
        assert status.data.mail == "user@example.com"
        assert status.data.quota_mb == 1024

    @pytest.mark.asyncio
    async def test_activate_success(self, mail_user_service, mock_ldap_service, mock_settings):
        """Test successful mail activation."""
        user_dn = "uid=testuser,ou=people,dc=example,dc=com"
        
        # Mock search: returns user for _find_user_dn calls, empty for email uniqueness
        def search_side_effect(*args, **kwargs):
            filter_str = kwargs.get("search_filter", "")
            if "uid=" in filter_str:
                return [MagicMock(dn=user_dn)]
            # Email uniqueness check - no duplicates
            return []
        
        mock_ldap_service.search.side_effect = search_side_effect
        
        # Mock get_by_dn: first inactive, then active after modify
        call_count = [0]
        def get_by_dn_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: check status - not active
                return {"objectClass": ["inetOrgPerson"]}
            else:
                # After activate: now active
                return {
                    "objectClass": ["inetOrgPerson", "hrcMailAccount"],
                    "mail": ["newuser@example.com"],
                    "hrcMailServer": ["mail.example.com"],
                    "hrcMailQuota": ["1024"],
                }
        
        mock_ldap_service.get_by_dn.side_effect = get_by_dn_side_effect

        data = MailAccountCreate(mail="newuser@example.com")

        with patch("heracles_api.config.settings", mock_settings):
            status = await mail_user_service.activate_mail("testuser", data)

        assert status.active is True
        mock_ldap_service.modify.assert_called_once()

    @pytest.mark.asyncio
    async def test_activate_already_active(self, mail_user_service, mock_ldap_service, mock_settings):
        """Test activation when already active."""
        user_dn = "uid=testuser,ou=people,dc=example,dc=com"
        mock_ldap_service.search.return_value = [MagicMock(dn=user_dn)]
        mock_ldap_service.get_by_dn.return_value = {
            "objectClass": ["inetOrgPerson", "hrcMailAccount"],
            "mail": ["existing@example.com"],
        }

        data = MailAccountCreate(mail="new@example.com")

        with patch("heracles_api.config.settings", mock_settings):
            with pytest.raises(MailValidationError) as exc_info:
                await mail_user_service.activate_mail("testuser", data)

        assert "already active" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_activate_email_in_use(self, mail_user_service, mock_ldap_service, mock_settings):
        """Test activation with email already in use."""
        user_dn = "uid=testuser,ou=people,dc=example,dc=com"
        other_user_dn = "uid=otheruser,ou=people,dc=example,dc=com"
        
        def search_side_effect(*args, **kwargs):
            filter_str = kwargs.get("search_filter", "")
            if "uid=" in filter_str:
                return [MagicMock(dn=user_dn)]
            # Email check - found another user
            return [MagicMock(dn=other_user_dn)]
        
        mock_ldap_service.search.side_effect = search_side_effect
        mock_ldap_service.get_by_dn.return_value = {"objectClass": ["inetOrgPerson"]}

        data = MailAccountCreate(mail="taken@example.com")

        with patch("heracles_api.config.settings", mock_settings):
            with pytest.raises(MailAlreadyExistsError) as exc_info:
                await mail_user_service.activate_mail("testuser", data)

        assert "taken@example.com" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_deactivate_success(self, mail_user_service, mock_ldap_service, mock_settings):
        """Test successful mail deactivation."""
        user_dn = "uid=testuser,ou=people,dc=example,dc=com"
        mock_ldap_service.search.return_value = [MagicMock(dn=user_dn)]
        
        call_count = [0]
        def get_by_dn_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 2:
                # First two calls: active
                return {
                    "objectClass": ["inetOrgPerson", "hrcMailAccount"],
                    "mail": ["user@example.com"],
                }
            else:
                # After deactivate
                return {"objectClass": ["inetOrgPerson"]}
        
        mock_ldap_service.get_by_dn.side_effect = get_by_dn_side_effect

        with patch("heracles_api.config.settings", mock_settings):
            status = await mail_user_service.deactivate_mail("testuser")

        assert status.active is False
        mock_ldap_service.modify.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_vacation(self, mail_user_service, mock_ldap_service, mock_settings):
        """Test updating vacation settings."""
        user_dn = "uid=testuser,ou=people,dc=example,dc=com"
        mock_ldap_service.search.return_value = [MagicMock(dn=user_dn)]
        mock_ldap_service.get_by_dn.return_value = {
            "objectClass": ["inetOrgPerson", "hrcMailAccount"],
            "mail": ["user@example.com"],
            "hrcMailDeliveryMode": [""],
        }

        data = MailAccountUpdate(
            vacationEnabled=True,
            vacationMessage="I'm on vacation",
        )

        with patch("heracles_api.config.settings", mock_settings):
            await mail_user_service.update_mail("testuser", data)

        mock_ldap_service.modify.assert_called_once()
        call_args = mock_ldap_service.modify.call_args
        mods = call_args[0][1]
        assert "hrcMailDeliveryMode" in mods
        assert "hrcVacationMessage" in mods


# ============================================================================
# MailGroupService Tests
# ============================================================================


class TestMailGroupService:
    """Tests for MailGroupService."""

    @pytest.mark.asyncio
    async def test_get_status_inactive(self, mail_group_service, mock_ldap_service, mock_settings):
        """Test getting status for group without mailing list."""
        group_dn = "cn=testgroup,ou=groups,dc=example,dc=com"
        mock_ldap_service.search.return_value = [MagicMock(dn=group_dn)]
        mock_ldap_service.get_by_dn.return_value = {
            "objectClass": ["groupOfNames"],
            "cn": ["testgroup"],
        }

        with patch("heracles_api.config.settings", mock_settings):
            status = await mail_group_service.get_group_mail_status("testgroup")

        assert status.cn == "testgroup"
        assert status.active is False
        assert status.data is None

    @pytest.mark.asyncio
    async def test_get_status_active_with_members(
        self, mail_group_service, mock_ldap_service, mock_settings
    ):
        """Test getting status for group with mailing list and members."""
        group_dn = "cn=testgroup,ou=groups,dc=example,dc=com"
        member_dn = "uid=member1,ou=people,dc=example,dc=com"

        mock_ldap_service.search.return_value = [MagicMock(dn=group_dn)]
        
        def get_by_dn_side_effect(dn, *args, **kwargs):
            if dn == group_dn:
                return {
                    "objectClass": ["groupOfNames", "hrcGroupMail"],
                    "cn": ["testgroup"],
                    "mail": ["team@example.com"],
                    "member": [member_dn],
                    "hrcGroupMailLocalOnly": ["FALSE"],
                }
            elif dn == member_dn:
                return {"mail": ["member1@example.com"]}
            return {}
        
        mock_ldap_service.get_by_dn.side_effect = get_by_dn_side_effect

        with patch("heracles_api.config.settings", mock_settings):
            status = await mail_group_service.get_group_mail_status("testgroup")

        assert status.active is True
        assert status.data.mail == "team@example.com"
        assert "member1@example.com" in status.data.member_emails

    @pytest.mark.asyncio
    async def test_activate_group_mail(self, mail_group_service, mock_ldap_service, mock_settings):
        """Test activating group mailing list."""
        group_dn = "cn=testgroup,ou=groups,dc=example,dc=com"
        
        def search_side_effect(*args, **kwargs):
            filter_str = kwargs.get("search_filter", "")
            if "cn=" in filter_str:
                return [MagicMock(dn=group_dn)]
            return []
        
        mock_ldap_service.search.side_effect = search_side_effect
        
        call_count = [0]
        def get_by_dn_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return {"objectClass": ["groupOfNames"]}
            return {
                "objectClass": ["groupOfNames", "hrcGroupMail"],
                "mail": ["team@example.com"],
                "hrcGroupMailLocalOnly": ["FALSE"],
            }
        
        mock_ldap_service.get_by_dn.side_effect = get_by_dn_side_effect

        data = MailGroupCreate(mail="team@example.com")

        with patch("heracles_api.config.settings", mock_settings):
            status = await mail_group_service.activate_mail("testgroup", data)

        assert status.active is True
        mock_ldap_service.modify.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_local_only(self, mail_group_service, mock_ldap_service, mock_settings):
        """Test updating local-only restriction."""
        group_dn = "cn=testgroup,ou=groups,dc=example,dc=com"
        mock_ldap_service.search.return_value = [MagicMock(dn=group_dn)]
        mock_ldap_service.get_by_dn.return_value = {
            "objectClass": ["groupOfNames", "hrcGroupMail"],
            "mail": ["team@example.com"],
            "hrcGroupMailLocalOnly": ["FALSE"],
        }

        data = MailGroupUpdate(localOnly=True)

        with patch("heracles_api.config.settings", mock_settings):
            await mail_group_service.update_mail("testgroup", data)

        mock_ldap_service.modify.assert_called_once()
        call_args = mock_ldap_service.modify.call_args
        mods = call_args[0][1]
        assert "hrcGroupMailLocalOnly" in mods


# ============================================================================
# TabService Interface Tests
# ============================================================================


class TestTabServiceInterface:
    """Tests for TabService interface methods."""

    @pytest.mark.asyncio
    async def test_is_active_valid_dn(self, mail_user_service, mock_ldap_service):
        """Test is_active with valid DN."""
        user_dn = "uid=testuser,ou=people,dc=example,dc=com"
        
        # Mock search to find user (called by _find_user_dn)
        mock_ldap_service.search.return_value = [MagicMock(dn=user_dn)]
        
        # Mock get_by_dn to return user with mail objectClass
        mock_ldap_service.get_by_dn.return_value = {
            "objectClass": ["inetOrgPerson", "hrcMailAccount"],
            "mail": ["testuser@example.com"],
        }

        result = await mail_user_service.is_active(user_dn)

        assert result is True

    @pytest.mark.asyncio
    async def test_is_active_invalid_dn(self, mail_user_service):
        """Test is_active with invalid DN."""
        result = await mail_user_service.is_active("invalid-dn-format")
        assert result is False

    @pytest.mark.asyncio
    async def test_read_returns_data(self, mail_user_service, mock_ldap_service):
        """Test read method returns MailAccountRead."""
        user_dn = "uid=testuser,ou=people,dc=example,dc=com"
        mock_ldap_service.search.return_value = [MagicMock(dn=user_dn)]
        mock_ldap_service.get_by_dn.return_value = {
            "objectClass": ["inetOrgPerson", "hrcMailAccount"],
            "mail": ["user@example.com"],
            "hrcMailQuota": ["1024"],
        }

        data = await mail_user_service.read(user_dn)

        assert data is not None
        assert data.mail == "user@example.com"
