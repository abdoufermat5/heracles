"""
Unit Test Configuration
=======================

Fixtures specific to unit tests.
All dependencies are mocked - no external services required.
"""

import pytest
from typing import Generator

from fastapi.testclient import TestClient

from heracles_api.main import app
from heracles_api.core.dependencies import (
    get_ldap,
    get_auth,
    get_user_repository,
    get_group_repository,
    get_department_repository,
    get_redis,
)


@pytest.fixture
def test_client(
    mock_ldap_service,
    mock_auth_service,
    mock_user_repository,
    mock_group_repository,
    mock_department_repository,
    mock_redis,
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
    app.dependency_overrides[get_department_repository] = lambda: mock_department_repository
    app.dependency_overrides[get_redis] = lambda: mock_redis

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
