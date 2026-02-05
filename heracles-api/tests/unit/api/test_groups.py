"""
Groups API Unit Tests
=====================

Tests for group management endpoints.
"""

import pytest
from unittest.mock import MagicMock


class TestListGroups:
    """Tests for GET /api/v1/groups/"""

    def test_list_groups_unauthorized(self, test_client):
        """Test accessing groups list without token returns 401."""
        response = test_client.get("/api/v1/groups/")

        assert response.status_code == 401

    def test_list_groups_empty(self, test_client, auth_headers, mock_group_repository):
        """Test listing groups when none exist."""
        search_result = MagicMock()
        search_result.groups = []
        search_result.total = 0
        mock_group_repository.search.return_value = search_result

        response = test_client.get("/api/v1/groups/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["groups"] == []

    def test_list_groups_with_results(
        self, test_client, auth_headers, mock_group_repository, group_entry_factory
    ):
        """Test listing groups returns paginated results."""
        entry1 = group_entry_factory(cn="admins", description="Administrators")
        entry2 = group_entry_factory(cn="users", description="Standard Users")

        search_result = MagicMock()
        search_result.groups = [entry1, entry2]
        search_result.total = 2
        mock_group_repository.search.return_value = search_result
        mock_group_repository.get_members.return_value = ["uid=admin,ou=people,dc=heracles,dc=local"]

        response = test_client.get("/api/v1/groups/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["groups"]) == 2
        assert data["groups"][0]["cn"] == "admins"

    def test_list_groups_with_search(
        self, test_client, auth_headers, mock_group_repository, group_entry_factory
    ):
        """Test listing groups with search filter."""
        entry = group_entry_factory(cn="developers", description="Development Team")

        search_result = MagicMock()
        search_result.groups = [entry]
        search_result.total = 1
        mock_group_repository.search.return_value = search_result
        mock_group_repository.get_members.return_value = []

        response = test_client.get(
            "/api/v1/groups/",
            params={"search": "dev"},
            headers=auth_headers
        )

        assert response.status_code == 200
        mock_group_repository.search.assert_called_once()


class TestGetGroup:
    """Tests for GET /api/v1/groups/{cn}"""

    def test_get_group_success(
        self, test_client, auth_headers, mock_group_repository, mock_group_entry
    ):
        """Test getting a group by CN."""
        mock_group_repository.find_by_cn.return_value = mock_group_entry
        mock_group_repository.get_members.return_value = [
            "uid=user1,ou=people,dc=heracles,dc=local",
            "uid=user2,ou=people,dc=heracles,dc=local",
        ]

        response = test_client.get("/api/v1/groups/developers", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["cn"] == "developers"
        assert data["description"] == "Development Team"

    def test_get_group_not_found(self, test_client, auth_headers, mock_group_repository):
        """Test getting a non-existent group returns 404."""
        mock_group_repository.find_by_cn.return_value = None

        response = test_client.get("/api/v1/groups/nonexistent", headers=auth_headers)

        assert response.status_code == 404

    def test_get_group_unauthorized(self, test_client):
        """Test getting a group without auth returns 401."""
        response = test_client.get("/api/v1/groups/admins")

        assert response.status_code == 401


class TestCreateGroup:
    """Tests for POST /api/v1/groups/"""

    def test_create_group_success(
        self, test_client, auth_headers, mock_group_repository, mock_group_entry
    ):
        """Test creating a new group."""
        mock_group_repository.exists.return_value = False
        mock_group_repository.create.return_value = mock_group_entry
        mock_group_repository.get_members.return_value = []

        response = test_client.post(
            "/api/v1/groups/",
            json={
                "cn": "newgroup",
                "description": "New Group",
            },
            headers=auth_headers
        )

        assert response.status_code == 201
        mock_group_repository.create.assert_called_once()

    def test_create_group_already_exists(
        self, test_client, auth_headers, mock_group_repository, mock_group_entry
    ):
        """Test creating a group that already exists returns 409."""
        mock_group_repository.exists.return_value = True

        response = test_client.post(
            "/api/v1/groups/",
            json={
                "cn": "developers",
                "description": "Already exists",
            },
            headers=auth_headers
        )

        assert response.status_code == 409

    def test_create_group_missing_required_fields(self, test_client, auth_headers):
        """Test creating a group without required fields returns 422."""
        response = test_client.post(
            "/api/v1/groups/",
            json={},  # Missing cn
            headers=auth_headers
        )

        assert response.status_code == 422


class TestUpdateGroup:
    """Tests for PATCH /api/v1/groups/{cn}"""

    def test_update_group_success(
        self, test_client, auth_headers, mock_group_repository, mock_group_entry
    ):
        """Test updating a group."""
        mock_group_repository.find_by_cn.return_value = mock_group_entry
        mock_group_repository.update.return_value = mock_group_entry
        mock_group_repository.get_members.return_value = []

        response = test_client.patch(
            "/api/v1/groups/developers",
            json={"description": "Updated Description"},
            headers=auth_headers
        )

        assert response.status_code == 200
        mock_group_repository.update.assert_called_once()

    def test_update_group_not_found(self, test_client, auth_headers, mock_group_repository):
        """Test updating a non-existent group returns 404."""
        mock_group_repository.update.return_value = None

        response = test_client.patch(
            "/api/v1/groups/nonexistent",
            json={"description": "test"},
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_update_group_unauthorized(self, test_client):
        """Test updating a group without auth returns 401."""
        response = test_client.patch(
            "/api/v1/groups/developers",
            json={"description": "test"}
        )

        assert response.status_code == 401


class TestDeleteGroup:
    """Tests for DELETE /api/v1/groups/{cn}"""

    def test_delete_group_success(
        self, test_client, auth_headers, mock_group_repository
    ):
        """Test deleting a group."""
        # Now endpoint uses find_by_cn for ACL check
        entry = MagicMock()
        entry.dn = "cn=developers,ou=groups,dc=heracles,dc=local"
        mock_group_repository.find_by_cn.return_value = entry

        response = test_client.delete("/api/v1/groups/developers", headers=auth_headers)

        assert response.status_code == 204
        mock_group_repository.delete.assert_called_once()

    def test_delete_group_not_found(self, test_client, auth_headers, mock_group_repository):
        """Test deleting a non-existent group returns 404."""
        mock_group_repository.find_by_cn.return_value = None

        response = test_client.delete("/api/v1/groups/nonexistent", headers=auth_headers)

        assert response.status_code == 404

    def test_delete_group_unauthorized(self, test_client):
        """Test deleting a group without auth returns 401."""
        response = test_client.delete("/api/v1/groups/developers")

        assert response.status_code == 401


class TestGroupMembers:
    """Tests for group member operations."""

    def test_add_member_success(
        self, test_client, auth_headers, mock_group_repository, mock_user_repository, mock_user_entry
    ):
        """Test adding a member to a group."""
        # Now endpoint uses find_by_cn for ACL check
        entry = MagicMock()
        entry.dn = "cn=developers,ou=groups,dc=heracles,dc=local"
        mock_group_repository.find_by_cn.return_value = entry
        mock_user_repository.find_by_uid.return_value = mock_user_entry
        mock_group_repository.get_members.return_value = []

        response = test_client.post(
            "/api/v1/groups/developers/members",
            json={"uid": "newuser"},
            headers=auth_headers
        )

        assert response.status_code == 204
        mock_group_repository.add_member.assert_called_once()

    def test_add_member_group_not_found(
        self, test_client, auth_headers, mock_group_repository
    ):
        """Test adding a member to non-existent group returns 404."""
        mock_group_repository.find_by_cn.return_value = None

        response = test_client.post(
            "/api/v1/groups/nonexistent/members",
            json={"uid": "user"},
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_remove_member_success(
        self, test_client, auth_headers, mock_group_repository, mock_user_repository, mock_user_entry
    ):
        """Test removing a member from a group."""
        # Now endpoint uses find_by_cn for ACL check
        entry = MagicMock()
        entry.dn = "cn=developers,ou=groups,dc=heracles,dc=local"
        mock_group_repository.find_by_cn.return_value = entry
        mock_user_repository.find_by_uid.return_value = mock_user_entry

        response = test_client.delete(
            "/api/v1/groups/developers/members/user1",
            headers=auth_headers
        )

        assert response.status_code == 204
        mock_group_repository.remove_member.assert_called_once()

    def test_remove_member_unauthorized(self, test_client):
        """Test removing a member without auth returns 401."""
        response = test_client.delete("/api/v1/groups/developers/members/user1")

        assert response.status_code == 401
