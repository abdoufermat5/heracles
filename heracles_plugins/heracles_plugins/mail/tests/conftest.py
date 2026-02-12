"""
Mail Plugin Test Configuration
==============================

Shared fixtures and configuration for mail plugin tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from heracles_plugins.mail.service.mail_user_service import MailUserService
from heracles_plugins.mail.service.mail_group_service import MailGroupService


@pytest.fixture
def mock_ldap_service():
    """Create a mock LDAP service."""
    ldap = AsyncMock()
    ldap.search = AsyncMock(return_value=[])
    ldap.get_by_dn = AsyncMock(return_value={})
    ldap.modify = AsyncMock()
    ldap.add = AsyncMock()
    ldap.delete = AsyncMock()
    return ldap


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.LDAP_BASE_DN = "dc=example,dc=com"
    settings.DEBUG = True
    settings.ALLOW_TEST_EMAIL_DOMAINS = True
    settings.TEST_EMAIL_DOMAINS = ["example.com", "test.local", "local"]
    return settings


@pytest.fixture
def mail_config():
    """Default mail service configuration."""
    return {
        "default_mail_server": "mail.example.com",
        "default_quota_mb": 1024,
        "mail_domain": "example.com",
    }


@pytest.fixture
def mail_user_service(mock_ldap_service, mail_config):
    """Create a MailUserService with mock LDAP."""
    return MailUserService(mock_ldap_service, mail_config)


@pytest.fixture
def mail_group_service(mock_ldap_service, mail_config):
    """Create a MailGroupService with mock LDAP."""
    return MailGroupService(mock_ldap_service, mail_config)


@pytest.fixture
def sample_user_entry():
    """Sample LDAP user entry."""
    return {
        "objectClass": ["inetOrgPerson", "organizationalPerson", "person", "top"],
        "uid": ["testuser"],
        "cn": ["Test User"],
        "sn": ["User"],
        "givenName": ["Test"],
    }


@pytest.fixture
def sample_user_with_mail_entry():
    """Sample LDAP user entry with mail enabled."""
    return {
        "objectClass": [
            "inetOrgPerson",
            "organizationalPerson",
            "person",
            "top",
            "hrcMailAccount",
        ],
        "uid": ["testuser"],
        "cn": ["Test User"],
        "sn": ["User"],
        "givenName": ["Test"],
        "mail": ["testuser@example.com"],
        "hrcMailServer": ["mail.example.com"],
        "hrcMailQuota": ["1024"],
        "hrcMailAlternateAddress": ["alias@example.com"],
        "hrcMailForwardingAddress": ["forward@external.com"],
        "hrcMailDeliveryMode": [""],
        "hrcVacationMessage": [],
        "hrcVacationStart": [],
        "hrcVacationStop": [],
    }


@pytest.fixture
def sample_group_entry():
    """Sample LDAP group entry."""
    return {
        "objectClass": ["groupOfNames", "top"],
        "cn": ["testgroup"],
        "member": [
            "uid=user1,ou=people,dc=example,dc=com",
            "uid=user2,ou=people,dc=example,dc=com",
        ],
    }


@pytest.fixture
def sample_group_with_mail_entry():
    """Sample LDAP group entry with mailing list enabled."""
    return {
        "objectClass": ["groupOfNames", "top", "hrcGroupMail"],
        "cn": ["testgroup"],
        "mail": ["team@example.com"],
        "hrcMailServer": ["mail.example.com"],
        "hrcMailAlternateAddress": ["team-alias@example.com"],
        "hrcMailForwardingAddress": [],
        "hrcGroupMailLocalOnly": ["FALSE"],
        "hrcMailMaxSize": ["10240"],
        "member": [
            "uid=user1,ou=people,dc=example,dc=com",
            "uid=user2,ou=people,dc=example,dc=com",
        ],
    }


@pytest.fixture
def mock_current_user():
    """Create mock current user for route tests."""
    user = MagicMock()
    user.uid = "admin"
    user.dn = "uid=admin,ou=people,dc=example,dc=com"
    user.groups = ["cn=admins,ou=groups,dc=example,dc=com"]
    return user


# Auto-use the settings mock for all tests
@pytest.fixture(autouse=True)
def auto_mock_settings(mock_settings):
    """Automatically mock settings for all tests."""
    with patch("heracles_api.config.settings", mock_settings):
        yield

