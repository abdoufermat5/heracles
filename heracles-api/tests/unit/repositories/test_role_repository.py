"""
Role Repository Tests
=====================

Tests for the role repository LDAP operations.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from heracles_api.repositories.role_repository import RoleRepository, RoleSearchResult
from heracles_api.schemas.role import RoleCreate, RoleUpdate
from heracles_api.services.ldap_service import LdapEntry, LdapOperationError


@pytest.fixture
def role_repository(mock_ldap_service):
    """Role repository with mocked LDAP service."""
    return RoleRepository(mock_ldap_service)


def create_mock_role_entry(
    dn="cn=sysadmin,ou=roles,dc=heracles,dc=local",
    cn="sysadmin",
    description="System administrators",
    role_occupants=None,
):
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


@pytest.mark.asyncio
class TestRoleRepository:
    """Tests for RoleRepository."""

    async def test_find_by_cn_success(self, role_repository, mock_ldap_service):
        """Test finding a role by CN."""
        entry = create_mock_role_entry()
        mock_ldap_service.search.return_value = [entry]
        mock_ldap_service._escape_filter = MagicMock(return_value="sysadmin")

        result = await role_repository.find_by_cn("sysadmin")

        assert result is not None
        assert result.dn == entry.dn
        mock_ldap_service.search.assert_called_once()

    async def test_find_by_cn_not_found(self, role_repository, mock_ldap_service):
        """Test finding a non-existent role."""
        mock_ldap_service.search.return_value = []
        mock_ldap_service._escape_filter = MagicMock(return_value="nonexistent")

        result = await role_repository.find_by_cn("nonexistent")

        assert result is None

    async def test_find_by_dn_success(self, role_repository, mock_ldap_service):
        """Test finding a role by DN."""
        entry = create_mock_role_entry()
        mock_ldap_service.get_by_dn.return_value = entry

        result = await role_repository.find_by_dn(entry.dn)

        assert result is not None
        assert result.dn == entry.dn

    async def test_exists_true(self, role_repository, mock_ldap_service):
        """Test checking role exists returns True."""
        entry = create_mock_role_entry()
        mock_ldap_service.search.return_value = [entry]
        mock_ldap_service._escape_filter = MagicMock(return_value="sysadmin")

        result = await role_repository.exists("sysadmin")

        assert result is True

    async def test_exists_false(self, role_repository, mock_ldap_service):
        """Test checking non-existent role returns False."""
        mock_ldap_service.search.return_value = []
        mock_ldap_service._escape_filter = MagicMock(return_value="nonexistent")

        result = await role_repository.exists("nonexistent")

        assert result is False

    @patch("heracles_api.repositories.role_repository.get_roles_rdn", new_callable=AsyncMock)
    async def test_search_roles(self, mock_get_rdn, role_repository, mock_ldap_service):
        """Test searching for roles."""
        mock_get_rdn.return_value = "ou=roles"
        entry1 = create_mock_role_entry(dn="cn=admin,ou=roles,dc=h,dc=l", cn="admin")
        entry2 = create_mock_role_entry(dn="cn=devops,ou=roles,dc=h,dc=l", cn="devops")
        mock_ldap_service.search.return_value = [entry1, entry2]

        result = await role_repository.search()

        assert isinstance(result, RoleSearchResult)
        assert result.total == 2
        assert len(result.roles) == 2
        mock_ldap_service.search.assert_called_once()

    @patch("heracles_api.repositories.role_repository.get_roles_rdn", new_callable=AsyncMock)
    async def test_search_with_term(self, mock_get_rdn, role_repository, mock_ldap_service):
        """Test searching with a search term."""
        mock_get_rdn.return_value = "ou=roles"
        mock_ldap_service.search.return_value = []
        mock_ldap_service._escape_filter = MagicMock(return_value="admin")

        await role_repository.search(search_term="admin")

        call_args = mock_ldap_service.search.call_args
        assert "cn=*admin*" in call_args.kwargs["search_filter"]

    @patch("heracles_api.repositories.role_repository.get_roles_rdn", new_callable=AsyncMock)
    async def test_search_with_base_dn(self, mock_get_rdn, role_repository, mock_ldap_service):
        """Test searching roles scoped to a department."""
        mock_get_rdn.return_value = "ou=roles"
        mock_ldap_service.search.return_value = []

        await role_repository.search(base_dn="ou=Engineering,dc=heracles,dc=local")

        call_args = mock_ldap_service.search.call_args
        assert call_args.kwargs["search_base"] == "ou=roles,ou=Engineering,dc=heracles,dc=local"

    @patch("heracles_api.repositories.role_repository.get_roles_rdn", new_callable=AsyncMock)
    async def test_create_role(self, mock_get_rdn, role_repository, mock_ldap_service):
        """Test creating a role."""
        mock_get_rdn.return_value = "ou=roles"
        entry = create_mock_role_entry(cn="newrole")
        mock_ldap_service.get_by_dn.return_value = entry

        create_data = RoleCreate(cn="newrole", description="New Role")
        result = await role_repository.create(create_data, member_dns=[])

        mock_ldap_service.add.assert_called_once()
        call_args = mock_ldap_service.add.call_args
        assert call_args.kwargs["object_classes"] == ["organizationalRole"]
        assert result is not None

    @patch("heracles_api.repositories.role_repository.get_roles_rdn", new_callable=AsyncMock)
    async def test_create_role_with_members(self, mock_get_rdn, role_repository, mock_ldap_service):
        """Test creating a role with initial members."""
        mock_get_rdn.return_value = "ou=roles"
        entry = create_mock_role_entry(cn="newrole")
        mock_ldap_service.get_by_dn.return_value = entry

        member_dns = ["uid=jdoe,ou=people,dc=heracles,dc=local"]
        create_data = RoleCreate(cn="newrole")
        await role_repository.create(create_data, member_dns=member_dns)

        call_args = mock_ldap_service.add.call_args
        assert call_args.kwargs["attributes"]["roleOccupant"] == member_dns

    @patch("heracles_api.repositories.role_repository.get_roles_rdn", new_callable=AsyncMock)
    async def test_create_role_in_department(self, mock_get_rdn, role_repository, mock_ldap_service):
        """Test creating a role within a department."""
        mock_get_rdn.return_value = "ou=roles"
        entry = create_mock_role_entry(
            dn="cn=teamlead,ou=roles,ou=Engineering,dc=heracles,dc=local",
            cn="teamlead",
        )
        mock_ldap_service.get_by_dn.return_value = entry

        create_data = RoleCreate(cn="teamlead")
        await role_repository.create(
            create_data,
            member_dns=[],
            department_dn="ou=Engineering,dc=heracles,dc=local",
        )

        call_args = mock_ldap_service.add.call_args
        assert "ou=Engineering" in call_args.kwargs["dn"]

    async def test_update_role(self, role_repository, mock_ldap_service):
        """Test updating a role."""
        entry = create_mock_role_entry()
        mock_ldap_service.search.return_value = [entry]
        mock_ldap_service._escape_filter = MagicMock(return_value="sysadmin")

        update_data = RoleUpdate(description="Updated description")
        result = await role_repository.update("sysadmin", update_data)

        mock_ldap_service.modify.assert_called_once()
        assert result is not None

    async def test_update_role_not_found(self, role_repository, mock_ldap_service):
        """Test updating a non-existent role."""
        mock_ldap_service.search.return_value = []
        mock_ldap_service._escape_filter = MagicMock(return_value="nonexistent")

        update_data = RoleUpdate(description="Test")
        result = await role_repository.update("nonexistent", update_data)

        assert result is None
        mock_ldap_service.modify.assert_not_called()

    async def test_update_role_clear_description(self, role_repository, mock_ldap_service):
        """Test clearing a role description."""
        entry = create_mock_role_entry()
        mock_ldap_service.search.return_value = [entry]
        mock_ldap_service._escape_filter = MagicMock(return_value="sysadmin")

        update_data = RoleUpdate(description="")
        await role_repository.update("sysadmin", update_data)

        call_args = mock_ldap_service.modify.call_args
        changes = call_args[0][1]
        assert changes["description"] == ("delete", [])

    async def test_delete_role(self, role_repository, mock_ldap_service):
        """Test deleting a role."""
        entry = create_mock_role_entry()
        mock_ldap_service.search.return_value = [entry]
        mock_ldap_service._escape_filter = MagicMock(return_value="sysadmin")

        result = await role_repository.delete("sysadmin")

        assert result is True
        mock_ldap_service.delete.assert_called_once_with(entry.dn)

    async def test_delete_role_not_found(self, role_repository, mock_ldap_service):
        """Test deleting a non-existent role."""
        mock_ldap_service.search.return_value = []
        mock_ldap_service._escape_filter = MagicMock(return_value="nonexistent")

        result = await role_repository.delete("nonexistent")

        assert result is False
        mock_ldap_service.delete.assert_not_called()

    async def test_add_member(self, role_repository, mock_ldap_service):
        """Test adding a member to a role."""
        entry = create_mock_role_entry(role_occupants=[])
        mock_ldap_service.search.return_value = [entry]
        mock_ldap_service._escape_filter = MagicMock(return_value="sysadmin")

        member_dn = "uid=jdoe,ou=people,dc=heracles,dc=local"
        result = await role_repository.add_member("sysadmin", member_dn)

        assert result is True
        mock_ldap_service.modify.assert_called_once()
        call_args = mock_ldap_service.modify.call_args
        assert call_args[0][1]["roleOccupant"] == ("add", [member_dn])

    async def test_add_member_already_exists(self, role_repository, mock_ldap_service):
        """Test adding a member that is already in the role."""
        member_dn = "uid=jdoe,ou=people,dc=heracles,dc=local"
        entry = create_mock_role_entry(role_occupants=[member_dn])
        mock_ldap_service.search.return_value = [entry]
        mock_ldap_service._escape_filter = MagicMock(return_value="sysadmin")

        with pytest.raises(LdapOperationError, match="already exists"):
            await role_repository.add_member("sysadmin", member_dn)

    async def test_add_member_role_not_found(self, role_repository, mock_ldap_service):
        """Test adding member to non-existent role."""
        mock_ldap_service.search.return_value = []
        mock_ldap_service._escape_filter = MagicMock(return_value="nonexistent")

        result = await role_repository.add_member("nonexistent", "uid=jdoe,ou=people,dc=h,dc=l")

        assert result is False

    async def test_remove_member(self, role_repository, mock_ldap_service):
        """Test removing a member from a role."""
        member_dn = "uid=jdoe,ou=people,dc=heracles,dc=local"
        entry = create_mock_role_entry(role_occupants=[member_dn])
        mock_ldap_service.search.return_value = [entry]
        mock_ldap_service._escape_filter = MagicMock(return_value="sysadmin")

        result = await role_repository.remove_member("sysadmin", member_dn)

        assert result is True
        mock_ldap_service.modify.assert_called_once()
        call_args = mock_ldap_service.modify.call_args
        assert call_args[0][1]["roleOccupant"] == ("delete", [member_dn])

    async def test_remove_member_not_in_role(self, role_repository, mock_ldap_service):
        """Test removing a member that is not in the role."""
        entry = create_mock_role_entry(role_occupants=[])
        mock_ldap_service.search.return_value = [entry]
        mock_ldap_service._escape_filter = MagicMock(return_value="sysadmin")

        with pytest.raises(LdapOperationError, match="not found"):
            await role_repository.remove_member("sysadmin", "uid=jdoe,ou=people,dc=heracles,dc=local")

    async def test_get_members(self, role_repository, mock_ldap_service):
        """Test getting role members as UIDs."""
        occupants = [
            "uid=jdoe,ou=people,dc=heracles,dc=local",
            "uid=admin,ou=people,dc=heracles,dc=local",
        ]
        entry = create_mock_role_entry(role_occupants=occupants)
        mock_ldap_service.search.return_value = [entry]
        mock_ldap_service._escape_filter = MagicMock(return_value="sysadmin")

        members = await role_repository.get_members("sysadmin")

        assert members == ["jdoe", "admin"]

    async def test_get_members_empty(self, role_repository, mock_ldap_service):
        """Test getting members of role with no members."""
        entry = create_mock_role_entry(role_occupants=[])
        mock_ldap_service.search.return_value = [entry]
        mock_ldap_service._escape_filter = MagicMock(return_value="sysadmin")

        members = await role_repository.get_members("sysadmin")

        assert members == []

    async def test_get_members_role_not_found(self, role_repository, mock_ldap_service):
        """Test getting members of non-existent role."""
        mock_ldap_service.search.return_value = []
        mock_ldap_service._escape_filter = MagicMock(return_value="nonexistent")

        members = await role_repository.get_members("nonexistent")

        assert members == []

    async def test_is_member_true(self, role_repository, mock_ldap_service):
        """Test checking membership returns True."""
        member_dn = "uid=jdoe,ou=people,dc=heracles,dc=local"
        entry = create_mock_role_entry(role_occupants=[member_dn])
        mock_ldap_service.search.return_value = [entry]
        mock_ldap_service._escape_filter = MagicMock(return_value="sysadmin")

        result = await role_repository.is_member("sysadmin", member_dn)

        assert result is True

    async def test_is_member_false(self, role_repository, mock_ldap_service):
        """Test checking membership returns False."""
        entry = create_mock_role_entry(role_occupants=[])
        mock_ldap_service.search.return_value = [entry]
        mock_ldap_service._escape_filter = MagicMock(return_value="sysadmin")

        result = await role_repository.is_member("sysadmin", "uid=other,ou=people,dc=heracles,dc=local")

        assert result is False

    async def test_get_user_roles(self, role_repository, mock_ldap_service):
        """Test getting all roles for a user."""
        role1 = create_mock_role_entry(cn="sysadmin")
        role2 = create_mock_role_entry(cn="devops", dn="cn=devops,ou=roles,dc=h,dc=l")
        mock_ldap_service.search.return_value = [role1, role2]

        user_dn = "uid=jdoe,ou=people,dc=heracles,dc=local"
        roles = await role_repository.get_user_roles(user_dn)

        assert len(roles) == 2
        call_args = mock_ldap_service.search.call_args
        assert f"roleOccupant={user_dn}" in call_args.kwargs["search_filter"]

    async def test_remove_user_from_all_roles(self, role_repository, mock_ldap_service):
        """Test removing a user from all their roles."""
        role1 = create_mock_role_entry(cn="sysadmin")
        role2 = create_mock_role_entry(cn="devops", dn="cn=devops,ou=roles,dc=h,dc=l")
        mock_ldap_service.search.return_value = [role1, role2]

        user_dn = "uid=jdoe,ou=people,dc=heracles,dc=local"
        count = await role_repository.remove_user_from_all_roles(user_dn)

        assert count == 2
        assert mock_ldap_service.modify.call_count == 2

    async def test_extract_uid_from_dn(self, role_repository):
        """Test extracting UID from DN."""
        assert role_repository._extract_uid_from_dn("uid=jdoe,ou=people,dc=h,dc=l") == "jdoe"
        assert role_repository._extract_uid_from_dn("cn=admin,ou=groups,dc=h,dc=l") == "cn=admin,ou=groups,dc=h,dc=l"

    async def test_get_occupants_list_string(self, role_repository):
        """Test handling roleOccupant as string."""
        entry = MagicMock(spec=LdapEntry)
        entry.get = lambda k, default=None: "uid=jdoe,ou=people,dc=h,dc=l" if k == "roleOccupant" else default

        result = role_repository._get_occupants_list(entry)

        assert result == ["uid=jdoe,ou=people,dc=h,dc=l"]

    async def test_get_occupants_list_empty(self, role_repository):
        """Test handling empty roleOccupant."""
        entry = MagicMock(spec=LdapEntry)
        entry.get = lambda k, default=None: [] if k == "roleOccupant" else default

        result = role_repository._get_occupants_list(entry)

        assert result == []
