"""
Mail Plugin Route Tests
=======================

API route tests for mail account management.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from heracles_plugins.mail.routes import router, get_mail_user_service, get_mail_group_service
from heracles_plugins.mail.schemas import (
    UserMailStatus,
    MailAccountRead,
    GroupMailStatus,
    MailGroupRead,
    DeliveryMode,
)
from heracles_plugins.mail.services.base import (
    MailValidationError,
    MailAlreadyExistsError,
)
from heracles_api.core.dependencies import get_current_user


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_mail_user_service():
    """Create mock mail user service."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_mail_group_service():
    """Create mock mail group service."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_current_user():
    """Create mock current user."""
    user = MagicMock()
    user.uid = "admin"
    user.dn = "uid=admin,ou=people,dc=example,dc=com"
    return user


@pytest.fixture
def app_with_mocks(mock_mail_user_service, mock_mail_group_service, mock_current_user):
    """Create FastAPI app with all dependencies mocked."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    # Override dependencies
    app.dependency_overrides[get_mail_user_service] = lambda: mock_mail_user_service
    app.dependency_overrides[get_mail_group_service] = lambda: mock_mail_group_service
    app.dependency_overrides[get_current_user] = lambda: mock_current_user

    return app


# ============================================================================
# User Mail Endpoint Tests
# ============================================================================


class TestUserMailEndpoints:
    """Tests for user mail API endpoints."""

    @pytest.mark.asyncio
    async def test_get_user_mail_status(self, app_with_mocks, mock_mail_user_service):
        """Test GET /mail/users/{uid}."""
        mock_mail_user_service.get_user_mail_status.return_value = UserMailStatus(
            uid="testuser",
            dn="uid=testuser,ou=people,dc=example,dc=com",
            active=True,
            data=MailAccountRead(
                mail="user@example.com",
                alternateAddresses=[],
                forwardingAddresses=[],
                deliveryMode=DeliveryMode.NORMAL,
                vacationEnabled=False,
            ),
        )

        async with AsyncClient(transport=ASGITransport(app=app_with_mocks), base_url="http://test") as client:
            response = await client.get("/api/v1/mail/users/testuser")

        assert response.status_code == 200
        data = response.json()
        assert data["uid"] == "testuser"
        assert data["active"] is True
        assert data["data"]["mail"] == "user@example.com"

    @pytest.mark.asyncio
    async def test_get_user_mail_status_not_found(self, app_with_mocks, mock_mail_user_service):
        """Test GET /mail/users/{uid} with non-existent user."""
        mock_mail_user_service.get_user_mail_status.side_effect = Exception("User not found")

        async with AsyncClient(transport=ASGITransport(app=app_with_mocks), base_url="http://test") as client:
            response = await client.get("/api/v1/mail/users/nonexistent")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_activate_user_mail(self, app_with_mocks, mock_mail_user_service):
        """Test POST /mail/users/{uid}/activate."""
        mock_mail_user_service.activate_mail.return_value = UserMailStatus(
            uid="testuser",
            dn="uid=testuser,ou=people,dc=example,dc=com",
            active=True,
            data=MailAccountRead(
                mail="new@example.com",
                alternateAddresses=[],
                forwardingAddresses=[],
                deliveryMode=DeliveryMode.NORMAL,
                vacationEnabled=False,
            ),
        )

        async with AsyncClient(transport=ASGITransport(app=app_with_mocks), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/mail/users/testuser/activate",
                json={"mail": "new@example.com"},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["active"] is True
        assert data["data"]["mail"] == "new@example.com"

    @pytest.mark.asyncio
    async def test_activate_user_mail_already_active(self, app_with_mocks, mock_mail_user_service):
        """Test POST /mail/users/{uid}/activate when already active."""
        # MailAlreadyExistsError returns 409 Conflict
        mock_mail_user_service.activate_mail.side_effect = MailAlreadyExistsError("Mail already active")

        async with AsyncClient(transport=ASGITransport(app=app_with_mocks), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/mail/users/testuser/activate",
                json={"mail": "test@example.com"},
            )

        assert response.status_code == 409  # Conflict

    @pytest.mark.asyncio
    async def test_activate_user_mail_validation_error(self, app_with_mocks, mock_mail_user_service):
        """Test POST /mail/users/{uid}/activate with validation error."""
        # MailValidationError returns 400 Bad Request
        # Email format is valid (passes Pydantic) but service rejects it
        mock_mail_user_service.activate_mail.side_effect = MailValidationError("Email already in use")

        async with AsyncClient(transport=ASGITransport(app=app_with_mocks), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/mail/users/testuser/activate",
                json={"mail": "taken@example.com"},
            )

        assert response.status_code == 400  # Bad Request

    @pytest.mark.asyncio
    async def test_update_user_mail(self, app_with_mocks, mock_mail_user_service):
        """Test PATCH /mail/users/{uid}."""
        mock_mail_user_service.update_mail.return_value = UserMailStatus(
            uid="testuser",
            dn="uid=testuser,ou=people,dc=example,dc=com",
            active=True,
            data=MailAccountRead(
                mail="user@example.com",
                alternateAddresses=[],
                forwardingAddresses=["forward@example.com"],
                deliveryMode=DeliveryMode.FORWARD_ONLY,
                vacationEnabled=False,
            ),
        )

        async with AsyncClient(transport=ASGITransport(app=app_with_mocks), base_url="http://test") as client:
            response = await client.patch(
                "/api/v1/mail/users/testuser",
                json={
                    "forwardingAddresses": ["forward@example.com"],
                    "deliveryMode": "forward_only",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["forwardingAddresses"] == ["forward@example.com"]
        assert data["data"]["deliveryMode"] == "forward_only"

    @pytest.mark.asyncio
    async def test_deactivate_user_mail(self, app_with_mocks, mock_mail_user_service):
        """Test POST /mail/users/{uid}/deactivate (note: POST not DELETE)."""
        mock_mail_user_service.deactivate_mail.return_value = UserMailStatus(
            uid="testuser",
            dn="uid=testuser,ou=people,dc=example,dc=com",
            active=False,
            data=None,
        )

        async with AsyncClient(transport=ASGITransport(app=app_with_mocks), base_url="http://test") as client:
            # Note: deactivate is a POST endpoint, not DELETE
            response = await client.post("/api/v1/mail/users/testuser/deactivate")

        assert response.status_code == 200
        data = response.json()
        assert data["active"] is False
        assert data["data"] is None


# ============================================================================
# Group Mail Endpoint Tests
# ============================================================================


class TestGroupMailEndpoints:
    """Tests for group mail API endpoints."""

    @pytest.mark.asyncio
    async def test_get_group_mail_status(self, app_with_mocks, mock_mail_group_service):
        """Test GET /mail/groups/{cn}."""
        mock_mail_group_service.get_group_mail_status.return_value = GroupMailStatus(
            cn="developers",
            dn="cn=developers,ou=groups,dc=example,dc=com",
            active=True,
            data=MailGroupRead(
                mail="devs@example.com",
                alternateAddresses=[],
                maxSize=None,
                localOnly=False,
                memberEmails=["user1@example.com", "user2@example.com"],
            ),
        )

        async with AsyncClient(transport=ASGITransport(app=app_with_mocks), base_url="http://test") as client:
            response = await client.get("/api/v1/mail/groups/developers")

        assert response.status_code == 200
        data = response.json()
        assert data["cn"] == "developers"
        assert data["active"] is True
        assert data["data"]["mail"] == "devs@example.com"
        # Note: JSON uses alias "memberEmails" 
        assert len(data["data"]["memberEmails"]) == 2

    @pytest.mark.asyncio
    async def test_activate_group_mail(self, app_with_mocks, mock_mail_group_service):
        """Test POST /mail/groups/{cn}/activate."""
        # Route calls service.activate_mail (not activate_group_mail)
        mock_mail_group_service.activate_mail.return_value = GroupMailStatus(
            cn="newgroup",
            dn="cn=newgroup,ou=groups,dc=example,dc=com",
            active=True,
            data=MailGroupRead(
                mail="newgroup@example.com",
                alternateAddresses=[],
                maxSize=None,
                localOnly=False,
                memberEmails=[],
            ),
        )

        async with AsyncClient(transport=ASGITransport(app=app_with_mocks), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/mail/groups/newgroup/activate",
                json={"mail": "newgroup@example.com"},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["active"] is True
        assert data["data"]["mail"] == "newgroup@example.com"

    @pytest.mark.asyncio
    async def test_update_group_mail_local_only(self, app_with_mocks, mock_mail_group_service):
        """Test PATCH /mail/groups/{cn} to set localOnly."""
        # Route calls service.update_mail (not update_group_mail)
        mock_mail_group_service.update_mail.return_value = GroupMailStatus(
            cn="internalgroup",
            dn="cn=internalgroup,ou=groups,dc=example,dc=com",
            active=True,
            data=MailGroupRead(
                mail="internal@example.com",
                alternateAddresses=[],
                maxSize=None,
                localOnly=True,
                memberEmails=[],
            ),
        )

        async with AsyncClient(transport=ASGITransport(app=app_with_mocks), base_url="http://test") as client:
            response = await client.patch(
                "/api/v1/mail/groups/internalgroup",
                json={"localOnly": True},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["localOnly"] is True

    @pytest.mark.asyncio
    async def test_deactivate_group_mail(self, app_with_mocks, mock_mail_group_service):
        """Test POST /mail/groups/{cn}/deactivate (note: POST not DELETE)."""
        # Route calls service.deactivate_mail (not deactivate_group_mail)
        mock_mail_group_service.deactivate_mail.return_value = GroupMailStatus(
            cn="oldgroup",
            dn="cn=oldgroup,ou=groups,dc=example,dc=com",
            active=False,
            data=None,
        )

        async with AsyncClient(transport=ASGITransport(app=app_with_mocks), base_url="http://test") as client:
            # Note: deactivate is a POST endpoint, not DELETE
            response = await client.post("/api/v1/mail/groups/oldgroup/deactivate")

        assert response.status_code == 200
        data = response.json()
        assert data["active"] is False
        assert data["data"] is None
