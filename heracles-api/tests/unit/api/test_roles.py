"""
Roles API Unit Tests
====================

Tests for role management endpoints.
"""

from unittest.mock import MagicMock

from heracles_api.services.ldap_service import LdapEntry, LdapOperationError


def create_mock_role_entry(
    dn: str = "cn=sysadmin,ou=roles,dc=heracles,dc=local",
    cn: str = "sysadmin",
    description: str = "System administrators",
    role_occupants: list[str] | None = None,
) -> MagicMock:
    """Create a mock role LDAP entry."""
    entry = MagicMock(spec=LdapEntry)
    entry.dn = dn
    entry.attributes = {
        "cn": cn,
        "description": description,
        "roleOccupant": role_occupants or [],
        "objectClass": ["organizationalRole"],
    }

    def get_first(key, default=None):
        val = entry.attributes.get(key)
        if val is None:
            return default
        if isinstance(val, list):
            return val[0] if val else default
        return val

    entry.get = lambda k, default=None: entry.attributes.get(k, default)
    entry.get_first = get_first
    return entry


class TestListRoles:
    """Tests for GET /api/v1/roles"""

    def test_list_roles_unauthorized(self, test_client):
        """Test listing roles without token returns 401."""
        response = test_client.get("/api/v1/roles")
        assert response.status_code == 401

    def test_list_roles_empty(self, test_client, auth_headers, mock_role_repository):
        """Test listing roles when none exist."""
        search_result = MagicMock()
        search_result.roles = []
        search_result.total = 0
        mock_role_repository.search.return_value = search_result

        response = test_client.get("/api/v1/roles", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["roles"] == []

    def test_list_roles_with_results(self, test_client, auth_headers, mock_role_repository):
        """Test listing roles returns results."""
        entry1 = create_mock_role_entry(cn="sysadmin")
        entry2 = create_mock_role_entry(
            dn="cn=devops,ou=roles,dc=heracles,dc=local",
            cn="devops",
            description="DevOps engineers",
        )

        search_result = MagicMock()
        search_result.roles = [entry1, entry2]
        search_result.total = 2
        mock_role_repository.search.return_value = search_result
        mock_role_repository.get_members.return_value = []

        response = test_client.get("/api/v1/roles", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["roles"]) == 2
        assert data["roles"][0]["cn"] == "sysadmin"
        assert data["roles"][1]["cn"] == "devops"

    def test_list_roles_with_search(self, test_client, auth_headers, mock_role_repository):
        """Test listing roles with search filter."""
        entry = create_mock_role_entry(cn="sysadmin")
        search_result = MagicMock()
        search_result.roles = [entry]
        search_result.total = 1
        mock_role_repository.search.return_value = search_result
        mock_role_repository.get_members.return_value = ["admin"]

        response = test_client.get(
            "/api/v1/roles",
            params={"search": "sys"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        mock_role_repository.search.assert_called_once()

    def test_list_roles_with_pagination(self, test_client, auth_headers, mock_role_repository):
        """Test listing roles with pagination params."""
        search_result = MagicMock()
        search_result.roles = []
        search_result.total = 0
        mock_role_repository.search.return_value = search_result

        response = test_client.get(
            "/api/v1/roles",
            params={"page": 2, "page_size": 10},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["pageSize"] == 10

    def test_list_roles_with_base_dn(self, test_client, auth_headers, mock_role_repository):
        """Test listing roles scoped to a department."""
        search_result = MagicMock()
        search_result.roles = []
        search_result.total = 0
        mock_role_repository.search.return_value = search_result

        response = test_client.get(
            "/api/v1/roles",
            params={"base": "ou=Engineering,dc=heracles,dc=local"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        mock_role_repository.search.assert_called_once_with(
            search_term=None,
            base_dn="ou=Engineering,dc=heracles,dc=local",
        )


class TestGetRole:
    """Tests for GET /api/v1/roles/{cn}"""

    def test_get_role_unauthorized(self, test_client):
        """Test getting a role without token returns 401."""
        response = test_client.get("/api/v1/roles/sysadmin")
        assert response.status_code == 401

    def test_get_role_success(self, test_client, auth_headers, mock_role_repository):
        """Test getting a role by CN."""
        entry = create_mock_role_entry()
        mock_role_repository.find_by_cn.return_value = entry
        mock_role_repository.get_members.return_value = ["admin", "jdoe"]

        response = test_client.get("/api/v1/roles/sysadmin", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["cn"] == "sysadmin"
        assert data["description"] == "System administrators"
        assert data["members"] == ["admin", "jdoe"]
        assert data["memberCount"] == 2

    def test_get_role_not_found(self, test_client, auth_headers, mock_role_repository):
        """Test getting a non-existent role returns 404."""
        mock_role_repository.find_by_cn.return_value = None

        response = test_client.get("/api/v1/roles/nonexistent", headers=auth_headers)

        assert response.status_code == 404


class TestCreateRole:
    """Tests for POST /api/v1/roles"""

    def test_create_role_unauthorized(self, test_client):
        """Test creating a role without auth returns 401."""
        response = test_client.post(
            "/api/v1/roles",
            json={"cn": "testrole"},
        )
        assert response.status_code == 401

    def test_create_role_success(self, test_client, auth_headers, mock_role_repository, mock_user_repository):
        """Test creating a new role."""
        entry = create_mock_role_entry(cn="newrole", description="New role")
        mock_role_repository.exists.return_value = False
        mock_role_repository.create.return_value = entry

        response = test_client.post(
            "/api/v1/roles",
            json={
                "cn": "newrole",
                "description": "New role",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["cn"] == "newrole"
        mock_role_repository.create.assert_called_once()

    def test_create_role_with_members(self, test_client, auth_headers, mock_role_repository, mock_user_repository):
        """Test creating a role with initial members."""
        user_entry = MagicMock(spec=LdapEntry)
        user_entry.dn = "uid=jdoe,ou=people,dc=heracles,dc=local"
        mock_user_repository.find_by_uid.return_value = user_entry

        entry = create_mock_role_entry(cn="newrole")
        mock_role_repository.exists.return_value = False
        mock_role_repository.create.return_value = entry

        response = test_client.post(
            "/api/v1/roles",
            json={
                "cn": "newrole",
                "description": "New role",
                "members": ["jdoe"],
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        mock_user_repository.find_by_uid.assert_called_once_with("jdoe")
        mock_role_repository.create.assert_called_once()

    def test_create_role_conflict(self, test_client, auth_headers, mock_role_repository):
        """Test creating a role that already exists returns 409."""
        mock_role_repository.exists.return_value = True

        response = test_client.post(
            "/api/v1/roles",
            json={"cn": "sysadmin"},
            headers=auth_headers,
        )

        assert response.status_code == 409

    def test_create_role_member_not_found(self, test_client, auth_headers, mock_role_repository, mock_user_repository):
        """Test creating a role with non-existent member returns 400."""
        mock_role_repository.exists.return_value = False
        mock_user_repository.find_by_uid.return_value = None

        response = test_client.post(
            "/api/v1/roles",
            json={
                "cn": "newrole",
                "members": ["nonexistent"],
            },
            headers=auth_headers,
        )

        assert response.status_code == 400

    def test_create_role_invalid_cn(self, test_client, auth_headers):
        """Test creating a role with invalid CN returns 422."""
        response = test_client.post(
            "/api/v1/roles",
            json={"cn": "invalid name with spaces!"},
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_create_role_missing_cn(self, test_client, auth_headers):
        """Test creating a role without cn returns 422."""
        response = test_client.post(
            "/api/v1/roles",
            json={"description": "Missing cn"},
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_create_role_with_department(self, test_client, auth_headers, mock_role_repository, mock_user_repository):
        """Test creating a role within a department."""
        entry = create_mock_role_entry(
            dn="cn=teamlead,ou=roles,ou=Engineering,dc=heracles,dc=local",
            cn="teamlead",
        )
        mock_role_repository.exists.return_value = False
        mock_role_repository.create.return_value = entry

        response = test_client.post(
            "/api/v1/roles",
            json={
                "cn": "teamlead",
                "departmentDn": "ou=Engineering,dc=heracles,dc=local",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201


class TestUpdateRole:
    """Tests for PATCH /api/v1/roles/{cn}"""

    def test_update_role_unauthorized(self, test_client):
        """Test updating a role without auth returns 401."""
        response = test_client.patch(
            "/api/v1/roles/sysadmin",
            json={"description": "Updated"},
        )
        assert response.status_code == 401

    def test_update_role_success(self, test_client, auth_headers, mock_role_repository):
        """Test updating a role."""
        entry = create_mock_role_entry(description="Updated description")
        mock_role_repository.find_by_cn.return_value = entry
        mock_role_repository.update.return_value = entry
        mock_role_repository.get_members.return_value = []

        response = test_client.patch(
            "/api/v1/roles/sysadmin",
            json={"description": "Updated description"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"
        mock_role_repository.update.assert_called_once()

    def test_update_role_not_found(self, test_client, auth_headers, mock_role_repository):
        """Test updating a non-existent role returns 404."""
        mock_role_repository.update.return_value = None

        response = test_client.patch(
            "/api/v1/roles/nonexistent",
            json={"description": "test"},
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestDeleteRole:
    """Tests for DELETE /api/v1/roles/{cn}"""

    def test_delete_role_unauthorized(self, test_client):
        """Test deleting a role without auth returns 401."""
        response = test_client.delete("/api/v1/roles/sysadmin")
        assert response.status_code == 401

    def test_delete_role_success(self, test_client, auth_headers, mock_role_repository):
        """Test deleting a role."""
        entry = create_mock_role_entry(cn="sysadmin")
        mock_role_repository.find_by_cn.return_value = entry

        response = test_client.delete("/api/v1/roles/sysadmin", headers=auth_headers)

        assert response.status_code == 204
        mock_role_repository.delete.assert_called_once_with("sysadmin")

    def test_delete_role_not_found(self, test_client, auth_headers, mock_role_repository):
        """Test deleting a non-existent role returns 404."""
        mock_role_repository.find_by_cn.return_value = None

        response = test_client.delete("/api/v1/roles/nonexistent", headers=auth_headers)

        assert response.status_code == 404


class TestAddRoleMember:
    """Tests for POST /api/v1/roles/{cn}/members"""

    def test_add_member_unauthorized(self, test_client):
        """Test adding member without auth returns 401."""
        response = test_client.post(
            "/api/v1/roles/sysadmin/members",
            json={"uid": "jdoe"},
        )
        assert response.status_code == 401

    def test_add_member_success(self, test_client, auth_headers, mock_role_repository, mock_user_repository):
        """Test adding a member to a role."""
        role_entry = create_mock_role_entry(cn="sysadmin")
        mock_role_repository.find_by_cn.return_value = role_entry
        user_entry = MagicMock(spec=LdapEntry)
        user_entry.dn = "uid=jdoe,ou=people,dc=heracles,dc=local"
        mock_user_repository.find_by_uid.return_value = user_entry

        response = test_client.post(
            "/api/v1/roles/sysadmin/members",
            json={"uid": "jdoe"},
            headers=auth_headers,
        )

        assert response.status_code == 204
        mock_role_repository.add_member.assert_called_once_with("sysadmin", user_entry.dn)

    def test_add_member_role_not_found(self, test_client, auth_headers, mock_role_repository):
        """Test adding member to non-existent role returns 404."""
        mock_role_repository.find_by_cn.return_value = None

        response = test_client.post(
            "/api/v1/roles/nonexistent/members",
            json={"uid": "jdoe"},
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_add_member_user_not_found(self, test_client, auth_headers, mock_role_repository, mock_user_repository):
        """Test adding non-existent user to role returns 404."""
        role_entry = create_mock_role_entry(cn="sysadmin")
        mock_role_repository.find_by_cn.return_value = role_entry
        mock_user_repository.find_by_uid.return_value = None

        response = test_client.post(
            "/api/v1/roles/sysadmin/members",
            json={"uid": "nonexistent"},
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_add_member_already_exists(self, test_client, auth_headers, mock_role_repository, mock_user_repository):
        """Test adding a member that already exists returns 409."""
        role_entry = create_mock_role_entry(cn="sysadmin")
        mock_role_repository.find_by_cn.return_value = role_entry
        user_entry = MagicMock(spec=LdapEntry)
        user_entry.dn = "uid=jdoe,ou=people,dc=heracles,dc=local"
        mock_user_repository.find_by_uid.return_value = user_entry
        mock_role_repository.add_member.side_effect = LdapOperationError("Member already exists in role")

        response = test_client.post(
            "/api/v1/roles/sysadmin/members",
            json={"uid": "jdoe"},
            headers=auth_headers,
        )

        assert response.status_code == 409


class TestRemoveRoleMember:
    """Tests for DELETE /api/v1/roles/{cn}/members/{uid}"""

    def test_remove_member_unauthorized(self, test_client):
        """Test removing member without auth returns 401."""
        response = test_client.delete("/api/v1/roles/sysadmin/members/jdoe")
        assert response.status_code == 401

    def test_remove_member_success(self, test_client, auth_headers, mock_role_repository, mock_user_repository):
        """Test removing a member from a role."""
        role_entry = create_mock_role_entry(cn="sysadmin")
        mock_role_repository.find_by_cn.return_value = role_entry
        user_entry = MagicMock(spec=LdapEntry)
        user_entry.dn = "uid=jdoe,ou=people,dc=heracles,dc=local"
        mock_user_repository.find_by_uid.return_value = user_entry

        response = test_client.delete(
            "/api/v1/roles/sysadmin/members/jdoe",
            headers=auth_headers,
        )

        assert response.status_code == 204
        mock_role_repository.remove_member.assert_called_once_with("sysadmin", user_entry.dn)

    def test_remove_member_role_not_found(self, test_client, auth_headers, mock_role_repository):
        """Test removing member from non-existent role returns 404."""
        mock_role_repository.find_by_cn.return_value = None

        response = test_client.delete(
            "/api/v1/roles/nonexistent/members/jdoe",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_remove_member_user_not_found(self, test_client, auth_headers, mock_role_repository, mock_user_repository):
        """Test removing non-existent user from role returns 404."""
        role_entry = create_mock_role_entry(cn="sysadmin")
        mock_role_repository.find_by_cn.return_value = role_entry
        mock_user_repository.find_by_uid.return_value = None

        response = test_client.delete(
            "/api/v1/roles/sysadmin/members/nonexistent",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_remove_member_not_in_role(self, test_client, auth_headers, mock_role_repository, mock_user_repository):
        """Test removing a member that is not in the role returns 404."""
        role_entry = create_mock_role_entry(cn="sysadmin")
        mock_role_repository.find_by_cn.return_value = role_entry
        user_entry = MagicMock(spec=LdapEntry)
        user_entry.dn = "uid=jdoe,ou=people,dc=heracles,dc=local"
        mock_user_repository.find_by_uid.return_value = user_entry
        mock_role_repository.remove_member.side_effect = LdapOperationError("Member not found in role")

        response = test_client.delete(
            "/api/v1/roles/sysadmin/members/jdoe",
            headers=auth_headers,
        )

        assert response.status_code == 404
