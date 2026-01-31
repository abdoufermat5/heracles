"""
Departments API Unit Tests
==========================

Tests for department management endpoints.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from heracles_api.services.ldap_service import LdapEntry


def create_mock_department_entry(
    dn: str = "ou=Engineering,dc=heracles,dc=local",
    ou: str = "Engineering",
    description: str = "Engineering department",
    category: str = "division",
) -> MagicMock:
    """Create a mock department LDAP entry."""
    entry = MagicMock(spec=LdapEntry)
    entry.dn = dn
    entry.attributes = {
        "ou": ou,
        "description": description,
        "hrcDepartmentCategory": category,
        "objectClass": ["organizationalUnit", "heraclesDepartment"],
    }
    entry.get = lambda k, default=None: entry.attributes.get(k, default)
    entry.get_first = lambda k, default=None: (
        entry.attributes.get(k, default)
        if not isinstance(entry.attributes.get(k), list)
        else entry.attributes.get(k, [default])[0]
    )
    return entry


class TestGetDepartmentTree:
    """Tests for GET /api/v1/departments/tree"""

    def test_get_tree_unauthorized(self, test_client):
        """Test accessing department tree without token returns 401."""
        response = test_client.get("/api/v1/departments/tree")

        assert response.status_code == 401

    def test_get_tree_empty(self, test_client, auth_headers, mock_department_repository):
        """Test getting tree when no departments exist."""
        mock_department_repository.get_tree.return_value = []

        response = test_client.get("/api/v1/departments/tree", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["tree"] == []
        assert data["total"] == 0

    def test_get_tree_with_departments(
        self, test_client, auth_headers, mock_department_repository
    ):
        """Test getting tree with departments."""
        mock_tree = [
            {
                "dn": "ou=Engineering,dc=heracles,dc=local",
                "ou": "Engineering",
                "description": "Engineering department",
                "path": "/Engineering",
                "depth": 0,
                "children": [
                    {
                        "dn": "ou=DevOps,ou=Engineering,dc=heracles,dc=local",
                        "ou": "DevOps",
                        "description": "DevOps team",
                        "path": "/Engineering/DevOps",
                        "depth": 1,
                        "children": [],
                    }
                ],
            }
        ]
        mock_department_repository.get_tree.return_value = mock_tree

        response = test_client.get("/api/v1/departments/tree", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["tree"]) == 1
        assert data["tree"][0]["ou"] == "Engineering"


class TestListDepartments:
    """Tests for GET /api/v1/departments/"""

    def test_list_departments_unauthorized(self, test_client):
        """Test accessing departments list without token returns 401."""
        response = test_client.get("/api/v1/departments")

        assert response.status_code == 401

    def test_list_departments_empty(
        self, test_client, auth_headers, mock_department_repository
    ):
        """Test listing departments when none exist."""
        search_result = MagicMock()
        search_result.departments = []
        search_result.total = 0
        mock_department_repository.search.return_value = search_result

        response = test_client.get("/api/v1/departments", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["departments"] == []

    def test_list_departments_with_results(
        self, test_client, auth_headers, mock_department_repository
    ):
        """Test listing departments returns results."""
        entry1 = create_mock_department_entry(
            dn="ou=Engineering,dc=heracles,dc=local",
            ou="Engineering",
        )
        entry2 = create_mock_department_entry(
            dn="ou=Sales,dc=heracles,dc=local",
            ou="Sales",
        )

        search_result = MagicMock()
        search_result.departments = [entry1, entry2]
        search_result.total = 2
        mock_department_repository.search.return_value = search_result
        mock_department_repository.get_children_count.return_value = 0

        # Mock the response conversion
        mock_department_repository._entry_to_response.side_effect = lambda e, c: {
            "dn": e.dn,
            "ou": e.get_first("ou"),
            "description": e.get_first("description"),
            "path": f"/{e.get_first('ou')}",
            "parentDn": None,
            "childrenCount": c,
        }

        response = test_client.get("/api/v1/departments", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_list_departments_with_search(
        self, test_client, auth_headers, mock_department_repository
    ):
        """Test listing departments with search filter."""
        entry = create_mock_department_entry(
            dn="ou=Engineering,dc=heracles,dc=local",
            ou="Engineering",
        )

        search_result = MagicMock()
        search_result.departments = [entry]
        search_result.total = 1
        mock_department_repository.search.return_value = search_result
        mock_department_repository.get_children_count.return_value = 0

        mock_department_repository._entry_to_response.return_value = {
            "dn": entry.dn,
            "ou": "Engineering",
            "description": "Engineering department",
            "path": "/Engineering",
            "parentDn": None,
            "childrenCount": 0,
        }

        response = test_client.get(
            "/api/v1/departments",
            params={"search": "eng"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        mock_department_repository.search.assert_called_once()


class TestCreateDepartment:
    """Tests for POST /api/v1/departments/"""

    def test_create_department_success(
        self, test_client, auth_headers, mock_department_repository
    ):
        """Test creating a new department."""
        entry = create_mock_department_entry()
        mock_department_repository.create.return_value = entry
        mock_department_repository._entry_to_response.return_value = {
            "dn": entry.dn,
            "ou": "Engineering",
            "description": "Engineering department",
            "path": "/Engineering",
            "parentDn": None,
            "childrenCount": 0,
        }

        response = test_client.post(
            "/api/v1/departments",
            json={
                "ou": "Engineering",
                "description": "Engineering department",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        mock_department_repository.create.assert_called_once()

    def test_create_department_with_parent(
        self, test_client, auth_headers, mock_department_repository
    ):
        """Test creating a department with parent."""
        entry = create_mock_department_entry(
            dn="ou=DevOps,ou=Engineering,dc=heracles,dc=local",
            ou="DevOps",
        )
        mock_department_repository.create.return_value = entry
        mock_department_repository._entry_to_response.return_value = {
            "dn": entry.dn,
            "ou": "DevOps",
            "description": "DevOps team",
            "path": "/Engineering/DevOps",
            "parentDn": "ou=Engineering,dc=heracles,dc=local",
            "childrenCount": 0,
        }

        response = test_client.post(
            "/api/v1/departments",
            json={
                "ou": "DevOps",
                "parentDn": "ou=Engineering,dc=heracles,dc=local",
                "description": "DevOps team",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201

    def test_create_department_missing_ou(self, test_client, auth_headers):
        """Test creating a department without ou returns 422."""
        response = test_client.post(
            "/api/v1/departments",
            json={"description": "Test department"},
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_create_department_unauthorized(self, test_client):
        """Test creating a department without auth returns 401."""
        response = test_client.post(
            "/api/v1/departments",
            json={"ou": "Test"},
        )

        assert response.status_code == 401


class TestGetDepartment:
    """Tests for GET /api/v1/departments/{dn}"""

    def test_get_department_success(
        self, test_client, auth_headers, mock_department_repository
    ):
        """Test getting a department by DN."""
        entry = create_mock_department_entry()
        mock_department_repository.find_by_dn.return_value = entry
        mock_department_repository.get_children_count.return_value = 2
        mock_department_repository._entry_to_response.return_value = {
            "dn": entry.dn,
            "ou": "Engineering",
            "description": "Engineering department",
            "path": "/Engineering",
            "parentDn": None,
            "childrenCount": 2,
        }

        dn = "ou=Engineering,dc=heracles,dc=local"
        response = test_client.get(
            f"/api/v1/departments/{dn}",
            headers=auth_headers,
        )

        assert response.status_code == 200

    def test_get_department_not_found(
        self, test_client, auth_headers, mock_department_repository
    ):
        """Test getting a non-existent department returns 404."""
        mock_department_repository.find_by_dn.return_value = None

        dn = "ou=Nonexistent,dc=heracles,dc=local"
        response = test_client.get(
            f"/api/v1/departments/{dn}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_get_department_unauthorized(self, test_client):
        """Test getting a department without auth returns 401."""
        dn = "ou=Engineering,dc=heracles,dc=local"
        response = test_client.get(f"/api/v1/departments/{dn}")

        assert response.status_code == 401


class TestUpdateDepartment:
    """Tests for PATCH /api/v1/departments/{dn}"""

    def test_update_department_success(
        self, test_client, auth_headers, mock_department_repository
    ):
        """Test updating a department."""
        entry = create_mock_department_entry()
        mock_department_repository.update.return_value = entry
        mock_department_repository.get_children_count.return_value = 0
        mock_department_repository._entry_to_response.return_value = {
            "dn": entry.dn,
            "ou": "Engineering",
            "description": "Updated description",
            "path": "/Engineering",
            "parentDn": None,
            "childrenCount": 0,
        }

        dn = "ou=Engineering,dc=heracles,dc=local"
        response = test_client.patch(
            f"/api/v1/departments/{dn}",
            json={"description": "Updated description"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        mock_department_repository.update.assert_called_once()

    def test_update_department_not_found(
        self, test_client, auth_headers, mock_department_repository
    ):
        """Test updating a non-existent department returns 404."""
        mock_department_repository.update.return_value = None

        dn = "ou=Nonexistent,dc=heracles,dc=local"
        response = test_client.patch(
            f"/api/v1/departments/{dn}",
            json={"description": "Test"},
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_update_department_unauthorized(self, test_client):
        """Test updating a department without auth returns 401."""
        dn = "ou=Engineering,dc=heracles,dc=local"
        response = test_client.patch(
            f"/api/v1/departments/{dn}",
            json={"description": "Test"},
        )

        assert response.status_code == 401


class TestDeleteDepartment:
    """Tests for DELETE /api/v1/departments/{dn}"""

    def test_delete_department_success(
        self, test_client, auth_headers, mock_department_repository
    ):
        """Test deleting a department."""
        mock_department_repository.delete.return_value = True

        dn = "ou=Engineering,dc=heracles,dc=local"
        response = test_client.delete(
            f"/api/v1/departments/{dn}",
            headers=auth_headers,
        )

        assert response.status_code == 204
        mock_department_repository.delete.assert_called_once()

    def test_delete_department_not_found(
        self, test_client, auth_headers, mock_department_repository
    ):
        """Test deleting a non-existent department returns 404."""
        mock_department_repository.delete.return_value = False

        dn = "ou=Nonexistent,dc=heracles,dc=local"
        response = test_client.delete(
            f"/api/v1/departments/{dn}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_delete_department_recursive(
        self, test_client, auth_headers, mock_department_repository
    ):
        """Test deleting a department recursively."""
        mock_department_repository.delete.return_value = True

        dn = "ou=Engineering,dc=heracles,dc=local"
        response = test_client.delete(
            f"/api/v1/departments/{dn}",
            params={"recursive": "true"},
            headers=auth_headers,
        )

        assert response.status_code == 204
        mock_department_repository.delete.assert_called_once()

    def test_delete_department_unauthorized(self, test_client):
        """Test deleting a department without auth returns 401."""
        dn = "ou=Engineering,dc=heracles,dc=local"
        response = test_client.delete(f"/api/v1/departments/{dn}")

        assert response.status_code == 401
