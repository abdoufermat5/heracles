"""
Unit Test Configuration
=======================

Fixtures specific to unit tests.
All dependencies are mocked - no external services required.
"""

import pytest
from typing import Generator
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from heracles_api.main import app
from heracles_api.core.dependencies import (
    get_ldap,
    get_auth,
    get_user_repository,
    get_group_repository,
    get_role_repository,
    get_department_repository,
    get_redis,
    get_acl_guard,
)
from heracles_api.acl import AclGuard


@pytest.fixture
def mock_acl_guard():
    """Create a mock ACL guard that permits all access."""
    guard = MagicMock()
    # By default, all permission checks pass (no exception raised)
    guard.require.return_value = None
    guard.require_any.return_value = None
    guard.check.return_value = True
    guard.check_any.return_value = True
    guard.filter_read.side_effect = lambda dn, ot, attrs, perm=None: attrs
    guard.filter_write.side_effect = lambda dn, ot, attrs, perm=None: attrs
    guard.is_self.return_value = False
    guard.user_dn = "uid=testuser,ou=people,dc=heracles,dc=local"
    return guard


@pytest.fixture
def test_client(
    mock_ldap_service,
    mock_auth_service,
    mock_user_repository,
    mock_group_repository,
    mock_role_repository,
    mock_department_repository,
    mock_redis,
    mock_acl_guard,
) -> Generator[TestClient, None, None]:
    """
    FastAPI test client with all dependencies mocked.

    This fixture overrides all external dependencies with mocks,
    allowing for isolated unit testing of API endpoints.
    """
    # Override dependencies
    app.dependency_overrides[get_ldap] = lambda: mock_ldap_service
    app.dependency_overrides[get_auth] = lambda: mock_auth_service
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repository
    app.dependency_overrides[get_group_repository] = lambda: mock_group_repository
    app.dependency_overrides[get_role_repository] = lambda: mock_role_repository
    app.dependency_overrides[get_department_repository] = lambda: mock_department_repository
    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_acl_guard] = lambda: mock_acl_guard

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
