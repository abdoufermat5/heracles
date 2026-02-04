"""
Repository Fixtures
===================

Fixtures for repository and service mocks.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_ldap_service():
    """
    Mock the LDAP service.

    Provides async mocks for all LDAP operations.
    """
    service = AsyncMock()
    service.search = AsyncMock(return_value=[])
    service.get_by_dn = AsyncMock(return_value=None)
    service.add = AsyncMock()
    service.modify = AsyncMock()
    service.delete = AsyncMock()
    service.authenticate = AsyncMock(return_value=True)
    service.bind = AsyncMock(return_value=True)
    service.unbind = AsyncMock()
    return service


@pytest.fixture
def mock_user_repository():
    """
    Mock the User repository.

    Provides async mocks for all user operations.
    """
    repo = AsyncMock()

    # Search/Find operations
    repo.authenticate = AsyncMock(return_value=None)
    repo.find_by_uid = AsyncMock(return_value=None)
    repo.find_by_dn = AsyncMock(return_value=None)
    repo.find_by_mail = AsyncMock(return_value=None)
    repo.search = AsyncMock(return_value=MagicMock(users=[], total=0))
    repo.exists = AsyncMock(return_value=False)

    # Group operations
    repo.get_groups = AsyncMock(return_value=[])

    # CRUD operations
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()

    # Password operations
    repo.set_password = AsyncMock()
    repo.check_password = AsyncMock(return_value=True)
    repo.lock = AsyncMock()
    repo.unlock = AsyncMock()
    repo.is_locked = AsyncMock(return_value=False)

    return repo


@pytest.fixture
def mock_group_repository():
    """
    Mock the Group repository.

    Provides async mocks for all group operations.
    """
    repo = AsyncMock()

    # Search/Find operations
    repo.find_by_cn = AsyncMock(return_value=None)
    repo.find_by_dn = AsyncMock(return_value=None)
    repo.search = AsyncMock(return_value=MagicMock(groups=[], total=0))
    repo.exists = AsyncMock(return_value=False)

    # Member operations
    repo.get_members = AsyncMock(return_value=[])
    repo.add_member = AsyncMock()
    repo.remove_member = AsyncMock()
    repo.remove_user_from_all_groups = AsyncMock()

    # CRUD operations
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()

    return repo


@pytest.fixture
def mock_department_repository():
    """
    Mock the Department repository.

    Provides async mocks for all department operations.
    """
    repo = AsyncMock()

    # Search/Find operations
    repo.find_by_dn = AsyncMock(return_value=None)
    repo.search = AsyncMock(return_value=MagicMock(departments=[], total=0))
    repo.get_tree = AsyncMock(return_value=[])
    repo.get_root_containers = AsyncMock(return_value=["people", "groups", "sudoers"])
    repo.get_children_count = AsyncMock(return_value=0)
    repo.has_children = AsyncMock(return_value=False)

    # CRUD operations
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock(return_value=True)

    # Helper methods
    repo._entry_to_response = MagicMock()
    repo._dn_to_path = MagicMock(return_value="/Test")

    return repo


# ============================================================================
# Plugin Repository Fixtures
# ============================================================================

@pytest.fixture
def mock_posix_service():
    """Mock the POSIX plugin service."""
    service = AsyncMock()

    # User POSIX operations
    service.get_posix_account = AsyncMock(return_value=None)
    service.create_posix_account = AsyncMock()
    service.delete_posix_account = AsyncMock()
    service.get_next_uid = AsyncMock(return_value=10000)

    # Group POSIX operations
    service.get_posix_group = AsyncMock(return_value=None)
    service.create_posix_group = AsyncMock()
    service.create_mixed_group = AsyncMock()
    service.get_next_gid = AsyncMock(return_value=10000)

    return service


@pytest.fixture
def mock_sudo_service():
    """Mock the Sudo plugin service."""
    service = AsyncMock()

    service.list_rules = AsyncMock(return_value=[])
    service.get_rule = AsyncMock(return_value=None)
    service.create_rule = AsyncMock()
    service.update_rule = AsyncMock()
    service.delete_rule = AsyncMock()
    service.get_user_rules = AsyncMock(return_value=[])

    return service


@pytest.fixture
def mock_ssh_service():
    """Mock the SSH plugin service."""
    service = AsyncMock()

    service.get_keys = AsyncMock(return_value=[])
    service.add_key = AsyncMock()
    service.remove_key = AsyncMock()
    service.validate_key = AsyncMock(return_value=True)

    return service


@pytest.fixture
def mock_dns_service():
    """Mock the DNS plugin service."""
    service = AsyncMock()

    service.list_zones = AsyncMock(return_value=[])
    service.get_zone = AsyncMock(return_value=None)
    service.create_zone = AsyncMock()
    service.delete_zone = AsyncMock()
    service.list_records = AsyncMock(return_value=[])
    service.create_record = AsyncMock()
    service.delete_record = AsyncMock()

    return service


@pytest.fixture
def mock_dhcp_service():
    """Mock the DHCP plugin service."""
    service = AsyncMock()

    service.list_subnets = AsyncMock(return_value=[])
    service.get_subnet = AsyncMock(return_value=None)
    service.create_subnet = AsyncMock()
    service.delete_subnet = AsyncMock()
    service.list_hosts = AsyncMock(return_value=[])
    service.create_host = AsyncMock()
    service.delete_host = AsyncMock()

    return service


@pytest.fixture
def mock_role_repository():
    """
    Mock the Role repository.

    Provides async mocks for all role operations.
    """
    repo = AsyncMock()

    # Search/Find operations
    repo.find_by_cn = AsyncMock(return_value=None)
    repo.find_by_dn = AsyncMock(return_value=None)
    repo.search = AsyncMock(return_value=MagicMock(roles=[], total=0))
    repo.exists = AsyncMock(return_value=False)

    # Member operations
    repo.get_members = AsyncMock(return_value=[])
    repo.add_member = AsyncMock(return_value=True)
    repo.remove_member = AsyncMock(return_value=True)
    repo.is_member = AsyncMock(return_value=False)
    repo.get_user_roles = AsyncMock(return_value=[])
    repo.remove_user_from_all_roles = AsyncMock(return_value=0)

    # CRUD operations
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock(return_value=True)

    return repo
