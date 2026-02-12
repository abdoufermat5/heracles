"""
Users API Unit Tests
====================

Tests for user management endpoints.
"""

from unittest.mock import MagicMock


class TestListUsers:
    """Tests for GET /api/v1/users/"""

    def test_list_users_unauthorized(self, test_client):
        """Test accessing users list without token returns 401."""
        response = test_client.get("/api/v1/users/")

        assert response.status_code == 401

    def test_list_users_empty(self, test_client, auth_headers, mock_user_repository):
        """Test listing users when none exist."""
        search_result = MagicMock()
        search_result.users = []
        search_result.total = 0
        mock_user_repository.search.return_value = search_result

        response = test_client.get("/api/v1/users/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["users"] == []

    def test_list_users_with_results(
        self, test_client, auth_headers, mock_user_repository, user_entry_factory
    ):
        """Test listing users returns paginated results."""
        entry1 = user_entry_factory(uid="user1", cn="User One")
        entry2 = user_entry_factory(uid="user2", cn="User Two")

        search_result = MagicMock()
        search_result.users = [entry1, entry2]
        search_result.total = 2
        mock_user_repository.search.return_value = search_result
        mock_user_repository.get_groups.return_value = ["users"]

        response = test_client.get("/api/v1/users/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["users"]) == 2
        assert data["users"][0]["uid"] == "user1"
        assert data["users"][1]["uid"] == "user2"

    def test_list_users_with_search(
        self, test_client, auth_headers, mock_user_repository, user_entry_factory
    ):
        """Test listing users with search filter."""
        entry = user_entry_factory(uid="john", cn="John Doe")

        search_result = MagicMock()
        search_result.users = [entry]
        search_result.total = 1
        mock_user_repository.search.return_value = search_result
        mock_user_repository.get_groups.return_value = []

        response = test_client.get(
            "/api/v1/users/",
            params={"search": "john"},
            headers=auth_headers
        )

        assert response.status_code == 200
        mock_user_repository.search.assert_called_once()

    def test_list_users_pagination(
        self, test_client, auth_headers, mock_user_repository, user_entry_factory
    ):
        """Test listing users with pagination."""
        entries = [user_entry_factory(uid=f"user{i}") for i in range(10)]

        search_result = MagicMock()
        search_result.users = entries
        search_result.total = 100
        mock_user_repository.search.return_value = search_result
        mock_user_repository.get_groups.return_value = []

        response = test_client.get(
            "/api/v1/users/",
            params={"page": 1, "page_size": 10},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert data["has_more"] is True


class TestGetUser:
    """Tests for GET /api/v1/users/{uid}"""

    def test_get_user_success(
        self, test_client, auth_headers, mock_user_repository, mock_user_entry
    ):
        """Test getting a user by UID."""
        mock_user_repository.find_by_uid.return_value = mock_user_entry
        mock_user_repository.get_groups.return_value = ["users", "developers"]

        response = test_client.get("/api/v1/users/testuser", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["uid"] == "testuser"
        assert data["cn"] == "Test User"

    def test_get_user_not_found(self, test_client, auth_headers, mock_user_repository):
        """Test getting a non-existent user returns 404."""
        mock_user_repository.find_by_uid.return_value = None

        response = test_client.get("/api/v1/users/nonexistent", headers=auth_headers)

        assert response.status_code == 404

    def test_get_user_unauthorized(self, test_client):
        """Test getting a user without auth returns 401."""
        response = test_client.get("/api/v1/users/testuser")

        assert response.status_code == 401


class TestCreateUser:
    """Tests for POST /api/v1/users/"""

    def test_create_user_success(
        self, test_client, auth_headers, mock_user_repository, mock_user_entry
    ):
        """Test creating a new user."""
        mock_user_repository.exists.return_value = False
        mock_user_repository.create.return_value = mock_user_entry
        mock_user_repository.get_groups.return_value = []

        response = test_client.post(
            "/api/v1/users/",
            json={
                "uid": "newuser",
                "cn": "New User",
                "sn": "User",
                "mail": "newuser@heracles.local",
                "password": "SecurePassword123!",
            },
            headers=auth_headers
        )

        assert response.status_code == 201
        mock_user_repository.create.assert_called_once()

    def test_create_user_already_exists(
        self, test_client, auth_headers, mock_user_repository, mock_user_entry
    ):
        """Test creating a user that already exists returns 409."""
        mock_user_repository.exists.return_value = True

        response = test_client.post(
            "/api/v1/users/",
            json={
                "uid": "testuser",
                "cn": "Test User",
                "sn": "User",
                "password": "SecurePassword123!",
            },
            headers=auth_headers
        )

        assert response.status_code == 409

    def test_create_user_missing_required_fields(self, test_client, auth_headers):
        """Test creating a user without required fields returns 422."""
        response = test_client.post(
            "/api/v1/users/",
            json={"uid": "newuser"},  # Missing cn and sn
            headers=auth_headers
        )

        assert response.status_code == 422


class TestUpdateUser:
    """Tests for PATCH /api/v1/users/{uid}"""

    def test_update_user_success(
        self, test_client, auth_headers, mock_user_repository, mock_user_entry
    ):
        """Test updating a user."""
        mock_user_repository.find_by_uid.return_value = mock_user_entry
        mock_user_repository.update.return_value = mock_user_entry
        mock_user_repository.get_groups.return_value = []

        response = test_client.patch(
            "/api/v1/users/testuser",
            json={"mail": "newemail@example.com"},
            headers=auth_headers
        )

        assert response.status_code == 200
        mock_user_repository.update.assert_called_once()

    def test_update_user_not_found(self, test_client, auth_headers, mock_user_repository):
        """Test updating a non-existent user returns 404."""
        mock_user_repository.update.return_value = None

        response = test_client.patch(
            "/api/v1/users/nonexistent",
            json={"mail": "test@example.com"},
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_update_user_unauthorized(self, test_client):
        """Test updating a user without auth returns 401."""
        response = test_client.patch(
            "/api/v1/users/testuser",
            json={"mail": "test@example.com"}
        )

        assert response.status_code == 401


class TestDeleteUser:
    """Tests for DELETE /api/v1/users/{uid}"""

    def test_delete_user_success(
        self, test_client, auth_headers, mock_user_repository, mock_user_entry
    ):
        """Test deleting a user."""
        mock_user_repository.find_by_uid.return_value = mock_user_entry
        mock_user_repository.delete.return_value = True

        response = test_client.delete("/api/v1/users/testuser", headers=auth_headers)

        assert response.status_code == 204
        mock_user_repository.delete.assert_called_once()

    def test_delete_user_not_found(self, test_client, auth_headers, mock_user_repository):
        """Test deleting a non-existent user returns 404."""
        mock_user_repository.find_by_uid.return_value = None

        response = test_client.delete("/api/v1/users/nonexistent", headers=auth_headers)

        assert response.status_code == 404

    def test_delete_user_unauthorized(self, test_client):
        """Test deleting a user without auth returns 401."""
        response = test_client.delete("/api/v1/users/testuser")

        assert response.status_code == 401
