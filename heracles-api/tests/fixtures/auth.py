"""
Authentication Fixtures
=======================

Fixtures for authentication and authorization testing.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock

from heracles_api.services.auth_service import TokenPayload, UserSession


@pytest.fixture
def mock_auth_service():
    """
    Mock the Auth service.

    Provides a fully configured mock with:
    - Sync methods: verify_token, create_access_token, create_refresh_token, get_cookie_settings
    - Async methods: is_token_revoked, get_session, create_session, etc.
    """
    service = MagicMock()

    # Sync methods
    service.verify_token.return_value = TokenPayload(
        sub="cn=admin,dc=heracles,dc=local",
        uid="admin",
        exp=datetime.now(),
        iat=datetime.now(),
        jti="mock-jti",
        type="access"
    )
    service.create_access_token.return_value = ("mock-access-token", "mock-jti")
    service.create_refresh_token.return_value = ("mock-refresh-token", "mock-refresh-jti")
    service.get_cookie_settings.return_value = {
        "key": "access_token",
        "httponly": True,
        "secure": False,
        "samesite": "lax",
        "max_age": 3600,
    }

    # Async methods
    service.is_token_revoked = AsyncMock(return_value=False)
    service.get_session = AsyncMock(return_value=UserSession(
        user_dn="cn=admin,dc=heracles,dc=local",
        uid="admin",
        display_name="Admin User",
        mail="admin@example.com",
        groups=["cn=admins,ou=groups,dc=heracles,dc=local"],
        created_at=datetime.now(),
        last_activity=datetime.now(),
        token_jti="mock-jti"
    ))
    service.create_session = AsyncMock()
    service.update_session_activity = AsyncMock()
    service.invalidate_session = AsyncMock()
    service.invalidate_all_user_sessions = AsyncMock(return_value=1)

    return service


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.exists = AsyncMock(return_value=0)
    redis.expire = AsyncMock(return_value=True)
    return redis


@pytest.fixture
def auth_headers():
    """Standard authentication headers for testing."""
    return {"Authorization": "Bearer mock-access-token"}


@pytest.fixture
def admin_session():
    """Admin user session for testing."""
    return UserSession(
        user_dn="cn=admin,dc=heracles,dc=local",
        uid="admin",
        display_name="Admin User",
        mail="admin@example.com",
        groups=["cn=admins,ou=groups,dc=heracles,dc=local"],
        created_at=datetime.now(),
        last_activity=datetime.now(),
        token_jti="admin-jti"
    )


@pytest.fixture
def user_session():
    """Regular user session for testing."""
    return UserSession(
        user_dn="uid=testuser,ou=people,dc=heracles,dc=local",
        uid="testuser",
        display_name="Test User",
        mail="testuser@example.com",
        groups=["cn=users,ou=groups,dc=heracles,dc=local"],
        created_at=datetime.now(),
        last_activity=datetime.now(),
        token_jti="user-jti"
    )
