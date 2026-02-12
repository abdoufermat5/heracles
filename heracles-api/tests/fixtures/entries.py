"""
LDAP Entry Fixtures
===================

Mock LDAP entries for testing.
"""

from typing import Any
from unittest.mock import MagicMock

import pytest


def create_mock_entry(
    dn: str,
    attributes: dict[str, Any],
) -> MagicMock:
    """
    Create a mock LDAP entry with the given attributes.

    Args:
        dn: Distinguished name of the entry
        attributes: Dictionary of attribute name -> value(s)

    Returns:
        MagicMock configured to behave like an LdapEntry
    """
    entry = MagicMock()
    entry.dn = dn

    # Store attributes for reference
    entry._attributes = attributes

    def get_first(attr: str, default: str | None = None) -> str | None:
        value = attributes.get(attr)
        if value is None:
            return default
        if isinstance(value, list):
            return value[0] if value else default
        return value

    def get(attr: str, default: list[str] | None = None) -> list[str] | None:
        value = attributes.get(attr)
        if value is None:
            return default
        if isinstance(value, list):
            return value
        return [value]

    entry.get_first = MagicMock(side_effect=get_first)
    entry.get = MagicMock(side_effect=get)

    return entry


# ============================================================================
# User Entry Fixtures
# ============================================================================


@pytest.fixture
def mock_user_entry():
    """Create a standard mock user entry."""
    return create_mock_entry(
        dn="uid=testuser,ou=people,dc=heracles,dc=local",
        attributes={
            "uid": "testuser",
            "cn": "Test User",
            "sn": "User",
            "givenName": "Test",
            "mail": "testuser@example.com",
            "objectClass": ["inetOrgPerson", "organizationalPerson", "person"],
        },
    )


@pytest.fixture
def mock_admin_entry():
    """Create a mock admin user entry."""
    return create_mock_entry(
        dn="uid=admin,ou=people,dc=heracles,dc=local",
        attributes={
            "uid": "admin",
            "cn": "Administrator",
            "sn": "Admin",
            "givenName": "System",
            "mail": "admin@example.com",
            "objectClass": ["inetOrgPerson", "organizationalPerson", "person"],
        },
    )


@pytest.fixture
def mock_posix_user_entry():
    """Create a mock user with POSIX attributes."""
    return create_mock_entry(
        dn="uid=posixuser,ou=people,dc=heracles,dc=local",
        attributes={
            "uid": "posixuser",
            "cn": "POSIX User",
            "sn": "User",
            "givenName": "POSIX",
            "mail": "posixuser@example.com",
            "uidNumber": "10001",
            "gidNumber": "10001",
            "homeDirectory": "/home/posixuser",
            "loginShell": "/bin/bash",
            "objectClass": ["inetOrgPerson", "posixAccount", "shadowAccount"],
        },
    )


# ============================================================================
# Group Entry Fixtures
# ============================================================================


@pytest.fixture
def mock_group_entry():
    """Create a standard mock group entry."""
    return create_mock_entry(
        dn="cn=developers,ou=groups,dc=heracles,dc=local",
        attributes={
            "cn": "developers",
            "description": "Development Team",
            "member": [
                "uid=user1,ou=people,dc=heracles,dc=local",
                "uid=user2,ou=people,dc=heracles,dc=local",
            ],
            "objectClass": ["groupOfNames", "top"],
        },
    )


@pytest.fixture
def mock_posix_group_entry():
    """Create a mock POSIX group entry."""
    return create_mock_entry(
        dn="cn=devs,ou=groups,dc=heracles,dc=local",
        attributes={
            "cn": "devs",
            "description": "Developers POSIX Group",
            "gidNumber": "10001",
            "memberUid": ["user1", "user2"],
            "objectClass": ["posixGroup", "top"],
        },
    )


@pytest.fixture
def mock_mixed_group_entry():
    """Create a mock mixed group entry (groupOfNames + posixGroupAux)."""
    return create_mock_entry(
        dn="cn=mixed,ou=groups,dc=heracles,dc=local",
        attributes={
            "cn": "mixed",
            "description": "Mixed Group",
            "gidNumber": "10002",
            "member": [
                "uid=user1,ou=people,dc=heracles,dc=local",
            ],
            "memberUid": ["user1"],
            "objectClass": ["groupOfNames", "posixGroupAux", "top"],
        },
    )


# ============================================================================
# System Entry Fixtures
# ============================================================================


@pytest.fixture
def mock_system_entry():
    """Create a mock system entry."""
    return create_mock_entry(
        dn="cn=webserver01,ou=systems,dc=heracles,dc=local",
        attributes={
            "cn": "webserver01",
            "description": "Web Server 01",
            "ipHostNumber": "192.168.1.10",
            "objectClass": ["device", "ipHost", "top"],
        },
    )


# ============================================================================
# Sudo Entry Fixtures
# ============================================================================


@pytest.fixture
def mock_sudo_entry():
    """Create a mock sudo rule entry."""
    return create_mock_entry(
        dn="cn=admin-all,ou=sudoers,dc=heracles,dc=local",
        attributes={
            "cn": "admin-all",
            "sudoUser": ["admin", "%admins"],
            "sudoHost": ["ALL"],
            "sudoCommand": ["ALL"],
            "sudoOption": ["!authenticate"],
            "objectClass": ["sudoRole", "top"],
        },
    )


# ============================================================================
# DNS Entry Fixtures
# ============================================================================


@pytest.fixture
def mock_dns_zone_entry():
    """Create a mock DNS zone entry."""
    return create_mock_entry(
        dn="zoneName=example.com,ou=dns,dc=heracles,dc=local",
        attributes={
            "zoneName": "example.com",
            "relativeDomainName": "@",
            "dNSTTL": "3600",
            "dNSClass": "IN",
            "sOARecord": "ns1.example.com. admin.example.com. 2024010101 3600 900 604800 86400",
            "nSRecord": ["ns1.example.com.", "ns2.example.com."],
            "objectClass": ["dNSZone", "top"],
        },
    )


# ============================================================================
# Factory Functions
# ============================================================================


@pytest.fixture
def user_entry_factory():
    """
    Factory fixture for creating custom user entries.

    Usage:
        def test_something(user_entry_factory):
            user = user_entry_factory(uid="custom", cn="Custom User")
    """

    def factory(
        uid: str = "testuser", cn: str = "Test User", sn: str = "User", mail: str = None, **extra_attrs
    ) -> MagicMock:
        attributes = {
            "uid": uid,
            "cn": cn,
            "sn": sn,
            "mail": mail or f"{uid}@example.com",
            "objectClass": ["inetOrgPerson", "organizationalPerson", "person"],
            **extra_attrs,
        }
        return create_mock_entry(dn=f"uid={uid},ou=people,dc=heracles,dc=local", attributes=attributes)

    return factory


@pytest.fixture
def group_entry_factory():
    """
    Factory fixture for creating custom group entries.

    Usage:
        def test_something(group_entry_factory):
            group = group_entry_factory(cn="custom-group", members=["user1", "user2"])
    """

    def factory(
        cn: str = "testgroup", description: str = "Test Group", members: list[str] = None, **extra_attrs
    ) -> MagicMock:
        member_dns = [f"uid={m},ou=people,dc=heracles,dc=local" for m in (members or [])]
        attributes = {
            "cn": cn,
            "description": description,
            "member": member_dns or ["cn=placeholder,dc=heracles,dc=local"],
            "objectClass": ["groupOfNames", "top"],
            **extra_attrs,
        }
        return create_mock_entry(dn=f"cn={cn},ou=groups,dc=heracles,dc=local", attributes=attributes)

    return factory
