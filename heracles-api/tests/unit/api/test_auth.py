"""
Auth API Unit Tests
===================

Tests for authentication endpoints.
"""

import pytest


class TestLogin:
    """Tests for POST /api/v1/auth/login"""

    def test_login_success(self, test_client, mock_user_repository, mock_user_entry):
        """Test successful login returns tokens."""
        mock_user_repository.authenticate.return_value = mock_user_entry
        mock_user_repository.get_groups.return_value = ["users", "developers"]

        response = test_client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "password"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, test_client, mock_user_repository):
        """Test login with invalid credentials returns 401."""
        mock_user_repository.authenticate.return_value = None

        response = test_client.post(
            "/api/v1/auth/login",
            json={"username": "wronguser", "password": "wrongpassword"}
        )

        assert response.status_code == 401

    def test_login_missing_username(self, test_client):
        """Test login without username returns validation error."""
        response = test_client.post(
            "/api/v1/auth/login",
            json={"password": "password"}
        )

        assert response.status_code == 422

    def test_login_missing_password(self, test_client):
        """Test login without password returns validation error."""
        response = test_client.post(
            "/api/v1/auth/login",
            json={"username": "testuser"}
        )

        assert response.status_code == 422


class TestLogout:
    """Tests for POST /api/v1/auth/logout"""

    def test_logout_success(self, test_client, auth_headers):
        """Test successful logout."""
        response = test_client.post("/api/v1/auth/logout", headers=auth_headers)

        assert response.status_code == 204

    def test_logout_unauthenticated(self, test_client):
        """Test logout without authentication returns 401."""
        response = test_client.post("/api/v1/auth/logout")

        assert response.status_code == 401


class TestGetMe:
    """Tests for GET /api/v1/auth/me"""

    def test_get_me_authenticated(self, test_client, auth_headers):
        """Test getting current user info when authenticated."""
        response = test_client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["uid"] == "admin"
        assert data["display_name"] == "Admin User"
        assert "groups" in data

    def test_get_me_unauthenticated(self, test_client):
        """Test getting current user info without authentication returns 401."""
        response = test_client.get("/api/v1/auth/me")

        assert response.status_code == 401


class TestRefreshToken:
    """Tests for POST /api/v1/auth/refresh"""

    def test_refresh_with_valid_token(
        self, test_client, mock_user_repository, mock_user_entry, mock_auth_service
    ):
        """Test refreshing with valid refresh token."""
        mock_user_repository.find_by_dn.return_value = mock_user_entry
        mock_user_repository.get_groups.return_value = ["users"]

        response = test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "mock-refresh-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
