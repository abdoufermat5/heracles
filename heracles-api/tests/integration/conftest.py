"""
Integration Test Configuration
==============================

Fixtures for integration tests with real services.

IMPORTANT: These tests require running infrastructure.
Use `make up-infra` before running integration tests.
"""

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from heracles_api.main import app


@pytest.fixture(scope="session")
def integration_test_enabled():
    """
    Check if integration tests should run.

    Set INTEGRATION_TESTS=1 environment variable to enable.
    """
    enabled = os.environ.get("INTEGRATION_TESTS", "0") == "1"
    if not enabled:
        pytest.skip("Integration tests disabled. Set INTEGRATION_TESTS=1 to enable.")
    return enabled


@pytest.fixture(scope="session")
def ldap_connection(integration_test_enabled):
    """
    Real LDAP connection for integration tests.

    Requires LDAP server to be running.
    """
    from heracles_api.services import get_ldap_service

    service = get_ldap_service()
    yield service


@pytest.fixture(scope="session")
def redis_connection(integration_test_enabled):
    """
    Real Redis connection for integration tests.

    Requires Redis server to be running.
    """
    from redis import Redis

    from heracles_api.config import settings

    redis = Redis.from_url(settings.REDIS_URL)
    yield redis
    redis.close()


@pytest.fixture
def integration_client(integration_test_enabled) -> Generator[TestClient, None, None]:
    """
    Test client for integration tests.

    Uses real services (no mocks).
    """
    with TestClient(app) as client:
        yield client


@pytest.fixture
def authenticated_client(integration_client, ldap_connection):
    """
    Authenticated test client for integration tests.

    Logs in with test user and returns client with auth headers.
    """
    # Login with test user
    response = integration_client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin_secret"})

    if response.status_code != 200:
        pytest.skip("Could not authenticate. Check LDAP credentials.")

    token = response.json()["access_token"]

    # Add auth to client
    integration_client.headers["Authorization"] = f"Bearer {token}"
    return integration_client
