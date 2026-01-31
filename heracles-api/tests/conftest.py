"""
Test Configuration
==================

Root conftest.py - imports all fixtures for the test suite.

Structure:
    tests/
    ├── conftest.py          # This file - root configuration
    ├── fixtures/            # Reusable fixtures
    │   ├── auth.py          # Authentication fixtures
    │   ├── repositories.py  # Repository mocks
    │   └── entries.py       # LDAP entry mocks
    ├── factories/           # Test data factories
    │   ├── user.py
    │   └── group.py
    ├── unit/                # Unit tests (mocked)
    │   ├── conftest.py      # Unit-specific fixtures
    │   └── api/             # API endpoint tests
    └── integration/         # Integration tests (real services)
        └── conftest.py      # Integration-specific fixtures

Usage:
    # Run all tests
    pytest -v

    # Run only unit tests
    pytest tests/unit/ -v

    # Run only integration tests (requires infrastructure)
    INTEGRATION_TESTS=1 pytest tests/integration/ -v

    # Run with coverage
    pytest --cov=heracles_api --cov-report=html
"""

import os
import sys
import pytest

# Override settings for testing - MUST happen before app imports
# Use os.environ[] instead of setdefault to force override
os.environ["TESTING"] = "true"
os.environ["LDAP_URI"] = "ldap://localhost"
os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost:5432/db"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"

# Add the project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all fixtures from fixtures module
from tests.fixtures.auth import (
    mock_auth_service,
    mock_redis,
    auth_headers,
    admin_session,
    user_session,
)

from tests.fixtures.repositories import (
    mock_ldap_service,
    mock_user_repository,
    mock_group_repository,
    mock_posix_service,
    mock_sudo_service,
    mock_ssh_service,
    mock_dns_service,
    mock_dhcp_service,
)

from tests.fixtures.entries import (
    create_mock_entry,
    mock_user_entry,
    mock_admin_entry,
    mock_posix_user_entry,
    mock_group_entry,
    mock_posix_group_entry,
    mock_mixed_group_entry,
    mock_system_entry,
    mock_sudo_entry,
    mock_dns_zone_entry,
    user_entry_factory,
    group_entry_factory,
)


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as unit test (no external services)"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires services)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        # Mark tests in unit/ directory
        if "/unit/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Mark tests in integration/ directory
        if "/integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


# ============================================================================
# Common Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def reset_app_state():
    """Reset application state between tests."""
    yield
    # Cleanup after test if needed


@pytest.fixture
def base_dn():
    """Return the base DN for tests."""
    return "dc=heracles,dc=local"


@pytest.fixture
def people_dn(base_dn):
    """Return the people OU DN."""
    return f"ou=people,{base_dn}"


@pytest.fixture
def groups_dn(base_dn):
    """Return the groups OU DN."""
    return f"ou=groups,{base_dn}"
