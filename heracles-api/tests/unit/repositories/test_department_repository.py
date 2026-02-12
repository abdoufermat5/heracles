"""
Department Repository Tests
===========================

Tests for the department repository LDAP operations.
"""

import pytest
from unittest.mock import MagicMock

from heracles_api.repositories.department_repository import DepartmentRepository, DepartmentSearchResult
from heracles_api.schemas.department import DepartmentCreate, DepartmentUpdate
from heracles_api.services.ldap_service import LdapEntry, LdapOperationError


@pytest.fixture
def department_repository(mock_ldap_service):
    """Department repository with mocked LDAP service."""
    return DepartmentRepository(mock_ldap_service)


def create_mock_department_entry(
    dn="ou=Engineering,dc=heracles,dc=local",
    ou="Engineering",
    description="Engineering department",
):
    """Create a mock department LDAP entry."""
    entry = MagicMock(spec=LdapEntry)
    entry.dn = dn
    entry.attributes = {
        "ou": ou,
        "description": description,
        "hrcDepartmentCategory": "division",
        "objectClass": ["organizationalUnit", "hrcDepartment"],
    }
    
    # Mock get and get_first methods safely
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
class TestDepartmentRepository:
    """Tests for DepartmentRepository."""

    async def test_find_by_dn_success(self, department_repository, mock_ldap_service):
        """Test finding a department by DN."""
        entry = create_mock_department_entry()
        mock_ldap_service.get_by_dn.return_value = entry

        result = await department_repository.find_by_dn("ou=Engineering,dc=heracles,dc=local")

        assert result is not None
        assert result.dn == entry.dn
        mock_ldap_service.get_by_dn.assert_called_once()

    async def test_find_by_dn_not_found(self, department_repository, mock_ldap_service):
        """Test finding a non-existent department."""
        mock_ldap_service.get_by_dn.return_value = None

        result = await department_repository.find_by_dn("ou=Nonexistent,dc=heracles,dc=local")

        assert result is None

    async def test_find_by_dn_not_a_department(self, department_repository, mock_ldap_service):
        """Test finding an entry that is not a department."""
        entry = create_mock_department_entry()
        entry.attributes["objectClass"] = ["organizationalUnit"]  # Missing hrcDepartment
        mock_ldap_service.get_by_dn.return_value = entry

        result = await department_repository.find_by_dn("ou=JustOU,dc=heracles,dc=local")

        assert result is None

    async def test_search_departments(self, department_repository, mock_ldap_service):
        """Test searching for departments."""
        entry1 = create_mock_department_entry(dn="ou=Eng,dc=h,dc=l", ou="Eng")
        entry2 = create_mock_department_entry(dn="ou=HR,dc=h,dc=l", ou="HR")
        mock_ldap_service.search.return_value = [entry1, entry2]

        result = await department_repository.search()

        assert isinstance(result, DepartmentSearchResult)
        assert result.total == 2
        assert len(result.departments) == 2
        mock_ldap_service.search.assert_called_once()

    async def test_search_with_filter(self, department_repository, mock_ldap_service):
        """Test searching with filter."""
        mock_ldap_service.search.return_value = []
        # Ensure _escape_filter is synchronous
        mock_ldap_service._escape_filter = MagicMock(return_value="eng")

        await department_repository.search(search_term="eng")

        # Verify filter construction
        call_args = mock_ldap_service.search.call_args
        assert "ou=*eng*" in call_args.kwargs["search_filter"]

    async def test_create_department(self, department_repository, mock_ldap_service):
        """Test creating a department."""
        mock_ldap_service.get_by_dn.side_effect = [None, create_mock_department_entry()]  # First checks existence, then returns created
        mock_ldap_service.search.return_value = []  # No existing containers

        create_data = DepartmentCreate(ou="Sales", description="Sales Dept")
        
        result = await department_repository.create(create_data)

        mock_ldap_service.add.assert_called()
        assert result is not None

    async def test_create_department_exists(self, department_repository, mock_ldap_service):
        """Test creating an existing department throws error."""
        entry = create_mock_department_entry()
        mock_ldap_service.get_by_dn.return_value = entry

        create_data = DepartmentCreate(ou="Engineering")
        
        with pytest.raises(LdapOperationError) as exc:
            await department_repository.create(create_data)
        
        assert "already exists" in str(exc.value)

    async def test_update_department(self, department_repository, mock_ldap_service):
        """Test updating a department."""
        entry = create_mock_department_entry()
        mock_ldap_service.get_by_dn.return_value = entry

        update_data = DepartmentUpdate(description="New Desc")
        
        result = await department_repository.update(entry.dn, update_data)

        mock_ldap_service.modify.assert_called_once()
        assert result is not None

    async def test_delete_department(self, department_repository, mock_ldap_service):
        """Test deleting a department."""
        entry = create_mock_department_entry()
        mock_ldap_service.get_by_dn.return_value = entry
        mock_ldap_service.search.return_value = []  # No children

        result = await department_repository.delete(entry.dn)

        assert result is True
        mock_ldap_service.delete.assert_called_once_with(entry.dn)

    async def test_delete_department_with_children_fails(self, department_repository, mock_ldap_service):
        """Test deleting a department with children (non-recursive) fails."""
        entry = create_mock_department_entry()
        mock_ldap_service.get_by_dn.return_value = entry
        
        child = MagicMock(spec=LdapEntry)
        child.dn = "uid=user1,ou=Eng,dc=h,dc=l"
        mock_ldap_service.search.return_value = [child]

        with pytest.raises(LdapOperationError) as exc:
            await department_repository.delete(entry.dn, recursive=False)
        
        assert "children" in str(exc.value)

    async def test_get_tree(self, department_repository, mock_ldap_service):
        """Test building department tree."""
        root = create_mock_department_entry(dn="ou=Root,dc=h,dc=l", ou="Root")
        child = create_mock_department_entry(dn="ou=Child,ou=Root,dc=h,dc=l", ou="Child")
        mock_ldap_service.search.return_value = [root, child]

        tree = await department_repository.get_tree()

        assert len(tree) == 1
        assert tree[0].ou == "Root"
        assert len(tree[0].children) == 1
        assert tree[0].children[0].ou == "Child"
