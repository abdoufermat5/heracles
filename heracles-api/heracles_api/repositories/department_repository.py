"""
Department Repository
=====================

Data access layer for department/OU LDAP operations.
"""

from typing import Optional, List
from dataclasses import dataclass

from heracles_api.services.ldap_service import (
    LdapService,
    LdapEntry,
    LdapOperationError,
    SearchScope,
)
from heracles_api.schemas.department import (
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse,
    DepartmentTreeNode,
)
from heracles_api.config import settings

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class DepartmentSearchResult:
    """Department search result."""
    departments: List[LdapEntry]
    total: int


class DepartmentRepository:
    """
    Repository for department LDAP operations.

    Departments are OUs with the hrcDepartment auxiliary objectClass.
    This approach mirrors gosaDepartment pattern.
    """

    # Filter to identify departments (OUs marked with hrcDepartment)
    DEPARTMENT_FILTER = "(&(objectClass=organizationalUnit)(objectClass=hrcDepartment))"
    OBJECT_CLASSES = ["organizationalUnit", "hrcDepartment"]
    DEPARTMENT_ATTRIBUTES = [
        "ou",
        "description",
        "hrcDepartmentCategory",
        "hrcDepartmentManager",
        "labeledURI",
    ]

    def __init__(self, ldap: LdapService):
        self.ldap = ldap
        self.base_dn = settings.LDAP_BASE_DN

    def _build_department_dn(self, ou: str, parent_dn: Optional[str] = None) -> str:
        """Build department DN from OU name."""
        if parent_dn:
            return f"ou={ou},{parent_dn}"
        return f"ou={ou},{self.base_dn}"

    def _entry_to_response(self, entry: LdapEntry, children_count: int = 0) -> DepartmentResponse:
        """Convert LDAP entry to DepartmentResponse."""
        ou = entry.get_first("ou", "")
        return DepartmentResponse(
            dn=entry.dn,
            ou=ou,
            description=entry.get_first("description"),
            path=self._dn_to_path(entry.dn),
            parent_dn=self._get_parent_dn(entry.dn),
            children_count=children_count,
            category=entry.get_first("hrcDepartmentCategory"),
            manager_dn=entry.get_first("hrcDepartmentManager"),
        )

    def _dn_to_path(self, dn: str) -> str:
        """
        Convert DN to human-readable path.

        Example: ou=DevOps,ou=Engineering,dc=heracles,dc=local -> /Engineering/DevOps
        """
        parts = []
        for component in dn.split(","):
            component = component.strip()
            if component.lower().startswith("ou="):
                parts.append(component.split("=", 1)[1])
            elif component.lower().startswith("dc="):
                break

        # Reverse to get path from root to leaf
        parts.reverse()
        return "/" + "/".join(parts) if parts else "/"

    def _get_parent_dn(self, dn: str) -> Optional[str]:
        """Get parent DN from a DN."""
        parts = dn.split(",", 1)
        if len(parts) > 1:
            parent = parts[1]
            # If parent is the base_dn, return None (no parent department)
            if parent == self.base_dn:
                return None
            return parent
        return None

    def _get_depth(self, dn: str) -> int:
        """Calculate depth of department from base_dn."""
        # Count OU components between this DN and base_dn
        suffix = "," + self.base_dn
        if dn.endswith(suffix):
            relative = dn[: -len(suffix)]
        else:
            relative = dn.replace("," + self.base_dn, "")

        ou_count = sum(1 for p in relative.split(",") if p.strip().lower().startswith("ou="))
        return ou_count - 1  # -1 because root departments have depth 0

    async def get_root_containers(self) -> List[str]:
        """
        Discover container OUs at root level (those without hrcDepartment).

        These are the containers like ou=people, ou=groups, ou=sudoers, etc.
        that should be auto-created within new departments.
        """
        # Find OUs directly under base_dn that are NOT departments
        filter_str = "(&(objectClass=organizationalUnit)(!(objectClass=hrcDepartment)))"

        try:
            entries = await self.ldap.search(
                search_base=self.base_dn,
                search_filter=filter_str,
                scope=SearchScope.ONELEVEL,
                attributes=["ou"],
            )
            return [e.get_first("ou") for e in entries if e.get_first("ou")]
        except LdapOperationError:
            logger.warning("failed_to_get_root_containers")
            return []

    async def find_by_dn(self, dn: str) -> Optional[LdapEntry]:
        """
        Find department by DN.

        Verifies the entry has the hrcDepartment objectClass.
        """
        entry = await self.ldap.get_by_dn(dn, attributes=self.DEPARTMENT_ATTRIBUTES + ["objectClass"])
        if not entry:
            return None

        # Verify it's a department (has hrcDepartment objectClass)
        object_classes = entry.get("objectClass", [])
        if isinstance(object_classes, str):
            object_classes = [object_classes]

        if not any(oc.lower() == "hrcdepartment" for oc in object_classes):
            return None

        return entry

    async def search(
        self,
        parent_dn: Optional[str] = None,
        search_term: Optional[str] = None,
        limit: int = 0,
    ) -> DepartmentSearchResult:
        """
        Search departments with optional filtering.

        Args:
            parent_dn: Search only direct children of this DN
            search_term: Search in ou, description
            limit: Maximum results (0 = unlimited)
        """
        base_filter = self.DEPARTMENT_FILTER

        if search_term:
            escaped = self.ldap._escape_filter(search_term)
            search_filter = f"(&{base_filter}(|(ou=*{escaped}*)(description=*{escaped}*)))"
        else:
            search_filter = base_filter

        # Determine search scope
        if parent_dn:
            search_base = parent_dn
            scope = SearchScope.ONELEVEL
        else:
            search_base = self.base_dn
            scope = SearchScope.SUBTREE

        entries = await self.ldap.search(
            search_base=search_base,
            search_filter=search_filter,
            scope=scope,
            attributes=self.DEPARTMENT_ATTRIBUTES,
            size_limit=limit,
        )

        return DepartmentSearchResult(departments=entries, total=len(entries))

    async def get_tree(self) -> List[DepartmentTreeNode]:
        """
        Build hierarchical department tree.

        Returns a list of root-level department nodes with nested children.
        """
        # Get all departments
        result = await self.search()
        entries = result.departments

        if not entries:
            return []

        # Build lookup by DN
        entry_map = {e.dn: e for e in entries}

        # Count children for each department
        children_count = {e.dn: 0 for e in entries}
        for entry in entries:
            parent_dn = self._get_parent_dn(entry.dn)
            if parent_dn and parent_dn in children_count:
                children_count[parent_dn] += 1

        # Build tree nodes
        nodes = {}
        for entry in entries:
            node = DepartmentTreeNode(
                dn=entry.dn,
                ou=entry.get_first("ou", ""),
                description=entry.get_first("description"),
                path=self._dn_to_path(entry.dn),
                depth=self._get_depth(entry.dn),
                children=[],
            )
            nodes[entry.dn] = node

        # Link children to parents
        root_nodes = []
        for dn, node in nodes.items():
            parent_dn = self._get_parent_dn(dn)
            if parent_dn and parent_dn in nodes:
                nodes[parent_dn].children.append(node)
            else:
                # This is a root-level department
                root_nodes.append(node)

        # Sort nodes by ou at each level
        def sort_children(node: DepartmentTreeNode):
            node.children.sort(key=lambda n: n.ou.lower())
            for child in node.children:
                sort_children(child)

        root_nodes.sort(key=lambda n: n.ou.lower())
        for node in root_nodes:
            sort_children(node)

        return root_nodes

    async def create(self, department: DepartmentCreate) -> LdapEntry:
        """
        Create a new department.

        Also creates container OUs inside the department (ou=people, ou=groups, etc.)
        mirroring the root-level structure.

        Args:
            department: Department creation data

        Returns:
            Created department entry
        """
        dept_dn = self._build_department_dn(department.ou, department.parent_dn)

        # Check if already exists
        existing = await self.ldap.get_by_dn(dept_dn, attributes=["ou"])
        if existing:
            raise LdapOperationError(f"Department already exists: {dept_dn}")

        # Build attributes
        attrs = {
            "ou": department.ou,
        }

        if department.description:
            attrs["description"] = department.description
        if department.category:
            attrs["hrcDepartmentCategory"] = department.category
        if department.manager_dn:
            attrs["hrcDepartmentManager"] = department.manager_dn

        # Create the department
        await self.ldap.add(
            dn=dept_dn,
            object_classes=self.OBJECT_CLASSES,
            attributes=attrs,
        )

        logger.info("department_created", ou=department.ou, dn=dept_dn)

        # Create container OUs inside the department
        root_containers = await self.get_root_containers()
        for container_ou in root_containers:
            container_dn = f"ou={container_ou},{dept_dn}"
            try:
                await self.ldap.add(
                    dn=container_dn,
                    object_classes=["organizationalUnit"],
                    attributes={"ou": container_ou},
                )
                logger.debug("department_container_created", container=container_ou, parent=dept_dn)
            except LdapOperationError as e:
                # Container might already exist, skip
                logger.debug("container_creation_skipped", container=container_ou, error=str(e))

        return await self.find_by_dn(dept_dn)

    async def update(self, dn: str, updates: DepartmentUpdate) -> Optional[LdapEntry]:
        """
        Update department attributes.

        Args:
            dn: Department DN
            updates: Fields to update

        Returns:
            Updated department entry or None if not found
        """
        entry = await self.find_by_dn(dn)
        if not entry:
            return None

        changes = {}
        update_data = updates.model_dump(exclude_unset=True, by_alias=True)

        attr_mapping = {
            "description": "description",
            "hrcDepartmentCategory": "hrcDepartmentCategory",
            "hrcDepartmentManager": "hrcDepartmentManager",
        }

        for field, ldap_attr in attr_mapping.items():
            if field in update_data:
                value = update_data[field]
                if value is not None and value != "":
                    changes[ldap_attr] = ("replace", [value])
                else:
                    changes[ldap_attr] = ("delete", [])

        if changes:
            await self.ldap.modify(dn, changes)
            logger.info("department_updated", dn=dn, changes=list(changes.keys()))

        return await self.find_by_dn(dn)

    async def delete(self, dn: str, recursive: bool = False) -> bool:
        """
        Delete a department.

        Args:
            dn: Department DN
            recursive: If True, delete all children first

        Returns:
            True if deleted, False if not found

        Raises:
            LdapOperationError: If department has children and recursive=False
        """
        entry = await self.find_by_dn(dn)
        if not entry:
            return False

        # Check for children
        children = await self.ldap.search(
            search_base=dn,
            search_filter="(objectClass=*)",
            scope=SearchScope.ONELEVEL,
            attributes=["dn"],
        )

        if children and not recursive:
            raise LdapOperationError(
                f"Department has {len(children)} children. Use recursive=true to delete."
            )

        if recursive and children:
            # Delete children recursively (depth-first)
            await self._delete_subtree(dn)
        else:
            await self.ldap.delete(dn)

        logger.info("department_deleted", dn=dn, recursive=recursive)
        return True

    async def _delete_subtree(self, dn: str) -> None:
        """Recursively delete all entries under a DN."""
        # Get all children
        children = await self.ldap.search(
            search_base=dn,
            search_filter="(objectClass=*)",
            scope=SearchScope.ONELEVEL,
            attributes=["dn"],
        )

        # Delete children first (recursively)
        for child in children:
            await self._delete_subtree(child.dn)

        # Delete this entry
        await self.ldap.delete(dn)

    async def get_children_count(self, dn: str) -> int:
        """Get count of direct children (departments and other entries)."""
        children = await self.ldap.search(
            search_base=dn,
            search_filter="(objectClass=*)",
            scope=SearchScope.ONELEVEL,
            attributes=["dn"],
        )
        return len(children)

    async def has_children(self, dn: str) -> bool:
        """Check if department has any children."""
        return await self.get_children_count(dn) > 0
