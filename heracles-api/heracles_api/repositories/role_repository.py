"""
Role Repository
================

Data access layer for role LDAP operations.

Roles use the standard organizationalRole objectClass with
roleOccupant attribute for member tracking.
"""

from typing import Optional, List
from dataclasses import dataclass

from heracles_api.services.ldap_service import LdapService, LdapEntry, LdapOperationError
from heracles_api.schemas.role import RoleCreate, RoleUpdate
from heracles_api.config import settings
from heracles_api.core.ldap_config import (
    get_roles_rdn,
)

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class RoleSearchResult:
    """Role search result with pagination info."""
    roles: List[LdapEntry]
    total: int


class RoleRepository:
    """
    Repository for role LDAP operations.
    
    Provides a clean interface for CRUD operations on organizational roles.
    Uses the standard organizationalRole objectClass from core.schema.
    """
    
    OBJECT_CLASSES = ["organizationalRole"]
    ROLE_ATTRIBUTES = ["cn", "description", "roleOccupant", "telephoneNumber", "facsimileTelephoneNumber"]
    
    def __init__(self, ldap: LdapService):
        self.ldap = ldap
        self.base_dn = settings.LDAP_BASE_DN
    
    async def _get_roles_container(self) -> str:
        """
        Get the roles container OU from config.
        
        Returns:
            Roles OU (e.g., 'ou=roles')
        """
        rdn = await get_roles_rdn()
        # Ensure proper format
        if not rdn.startswith("ou="):
            return f"ou={rdn}"
        return rdn
    
    async def _build_role_dn(self, cn: str, department_dn: Optional[str] = None) -> str:
        """
        Build role DN from CN.

        Args:
            cn: Role common name
            department_dn: Optional department DN to create role within

        Returns:
            Role DN string
        """
        roles_container = await self._get_roles_container()
        
        if department_dn:
            # Create under roles container within the department
            # e.g., cn=sysadmin,ou=roles,ou=Engineering,dc=heracles,dc=local
            return f"cn={cn},{roles_container},{department_dn}"
        return f"cn={cn},{roles_container},{self.base_dn}"
    
    @staticmethod
    def _extract_uid_from_dn(dn: str) -> str:
        """Extract UID from user DN."""
        for part in dn.split(","):
            if part.strip().lower().startswith("uid="):
                return part.split("=", 1)[1]
        return dn
    
    def _get_occupants_list(self, entry: LdapEntry) -> List[str]:
        """Get roleOccupant list from entry, handling single value case."""
        occupants = entry.get("roleOccupant", [])
        if isinstance(occupants, str):
            return [occupants] if occupants else []
        return list(occupants) if occupants else []
    
    async def find_by_cn(self, cn: str) -> Optional[LdapEntry]:
        """Find role by CN."""
        entries = await self.ldap.search(
            search_filter=f"(&(objectClass=organizationalRole)(cn={self.ldap._escape_filter(cn)}))",
            attributes=self.ROLE_ATTRIBUTES,
        )
        return entries[0] if entries else None
    
    async def find_by_dn(self, dn: str) -> Optional[LdapEntry]:
        """Find role by DN."""
        return await self.ldap.get_by_dn(dn, attributes=self.ROLE_ATTRIBUTES)
    
    async def exists(self, cn: str) -> bool:
        """Check if role exists."""
        entries = await self.ldap.search(
            search_filter=f"(&(objectClass=organizationalRole)(cn={self.ldap._escape_filter(cn)}))",
            attributes=["cn"],
        )
        return len(entries) > 0
    
    async def search(
        self,
        search_term: Optional[str] = None,
        base_dn: Optional[str] = None,
        limit: int = 0,
    ) -> RoleSearchResult:
        """
        Search roles with optional filtering.

        Args:
            search_term: Search in cn, description
            base_dn: Base DN to search from (e.g., department DN for scoped search)
            limit: Maximum results (0 = unlimited)
        """
        base_filter = "(objectClass=organizationalRole)"

        if search_term:
            escaped = self.ldap._escape_filter(search_term)
            search_filter = f"(&{base_filter}(|(cn=*{escaped}*)(description=*{escaped}*)))"
        else:
            search_filter = base_filter

        # Determine search base
        roles_container = await self._get_roles_container()
        
        if base_dn:
            # Search within department's roles container
            # e.g., ou=roles,ou=Engineering,dc=heracles,dc=local
            search_base = f"{roles_container},{base_dn}"
        else:
            # Search only in root-level roles container
            # e.g., ou=roles,dc=heracles,dc=local
            search_base = f"{roles_container},{self.base_dn}"

        entries = await self.ldap.search(
            search_base=search_base,
            search_filter=search_filter,
            attributes=self.ROLE_ATTRIBUTES,
            size_limit=limit,
        )

        return RoleSearchResult(roles=entries, total=len(entries))
    
    async def create(
        self,
        role: RoleCreate,
        member_dns: List[str],
        department_dn: Optional[str] = None,
    ) -> LdapEntry:
        """
        Create a new role.

        Args:
            role: Role creation data
            member_dns: List of member DNs (resolved from UIDs)
            department_dn: Optional department DN (role will be created under ou=roles within this dept)

        Returns:
            Created role entry
        """
        role_dn = await self._build_role_dn(role.cn, department_dn=department_dn)
        
        attrs = {}
        
        if role.description:
            attrs["description"] = role.description
        
        # roleOccupant is optional for organizationalRole (unlike groupOfNames member)
        if member_dns:
            attrs["roleOccupant"] = member_dns
        
        await self.ldap.add(
            dn=role_dn,
            object_classes=self.OBJECT_CLASSES,
            attributes=attrs,
        )
        
        logger.info("role_created", cn=role.cn, dn=role_dn, member_count=len(member_dns))
        
        return await self.find_by_dn(role_dn)
    
    async def update(self, cn: str, updates: RoleUpdate) -> Optional[LdapEntry]:
        """
        Update role attributes.
        
        Args:
            cn: Role CN
            updates: Fields to update
            
        Returns:
            Updated role entry or None if not found
        """
        entry = await self.find_by_cn(cn)
        if not entry:
            return None
        
        changes = {}
        
        if updates.description is not None:
            if updates.description:
                changes["description"] = ("replace", [updates.description])
            else:
                changes["description"] = ("delete", [])
        
        if changes:
            await self.ldap.modify(entry.dn, changes)
            logger.info("role_updated", cn=cn, changes=list(changes.keys()))
        
        return await self.find_by_cn(cn)
    
    async def delete(self, cn: str) -> bool:
        """
        Delete a role.
        
        Args:
            cn: Role CN
            
        Returns:
            True if deleted, False if not found
        """
        entry = await self.find_by_cn(cn)
        if not entry:
            return False
        
        await self.ldap.delete(entry.dn)
        logger.info("role_deleted", cn=cn)
        
        return True
    
    async def add_member(self, cn: str, member_dn: str) -> bool:
        """
        Add a member to a role.
        
        Args:
            cn: Role CN
            member_dn: Member DN to add (roleOccupant)
            
        Returns:
            True if added, False if role not found
            
        Raises:
            LdapOperationError: If member already exists or operation fails
        """
        entry = await self.find_by_cn(cn)
        if not entry:
            return False
        
        # Check if already a member
        existing_members = self._get_occupants_list(entry)
        if member_dn in existing_members:
            raise LdapOperationError("Member already exists in role")
        
        await self.ldap.modify(
            entry.dn,
            {"roleOccupant": ("add", [member_dn])}
        )
        
        logger.info("role_member_added", cn=cn, member_dn=member_dn)
        return True
    
    async def remove_member(self, cn: str, member_dn: str) -> bool:
        """
        Remove a member from a role.
        
        Args:
            cn: Role CN
            member_dn: Member DN to remove
            
        Returns:
            True if removed, False if role not found
            
        Raises:
            LdapOperationError: If member not found
        """
        entry = await self.find_by_cn(cn)
        if not entry:
            return False
        
        existing_members = self._get_occupants_list(entry)
        
        if member_dn not in existing_members:
            raise LdapOperationError("Member not found in role")
        
        await self.ldap.modify(
            entry.dn,
            {"roleOccupant": ("delete", [member_dn])}
        )
        
        logger.info("role_member_removed", cn=cn, member_dn=member_dn)
        return True
    
    async def get_members(self, cn: str) -> List[str]:
        """
        Get role members as UIDs.
        
        Args:
            cn: Role CN
            
        Returns:
            List of member UIDs
        """
        entry = await self.find_by_cn(cn)
        if not entry:
            return []
        
        occupants = self._get_occupants_list(entry)
        return [self._extract_uid_from_dn(dn) for dn in occupants if dn]
    
    async def is_member(self, cn: str, member_dn: str) -> bool:
        """
        Check if DN is a member of the role.
        
        Args:
            cn: Role CN
            member_dn: Member DN to check
            
        Returns:
            True if member, False otherwise
        """
        entry = await self.find_by_cn(cn)
        if not entry:
            return False
        
        occupants = self._get_occupants_list(entry)
        return member_dn in occupants
    
    async def get_user_roles(self, user_dn: str) -> List[LdapEntry]:
        """
        Get all roles a user belongs to.
        
        Args:
            user_dn: User DN
            
        Returns:
            List of role entries
        """
        entries = await self.ldap.search(
            search_filter=f"(&(objectClass=organizationalRole)(roleOccupant={user_dn}))",
            attributes=self.ROLE_ATTRIBUTES,
        )
        return entries
    
    async def remove_user_from_all_roles(self, user_dn: str) -> int:
        """
        Remove user from all roles.
        
        Args:
            user_dn: User DN to remove
            
        Returns:
            Number of roles the user was removed from
        """
        roles = await self.get_user_roles(user_dn)
        count = 0
        
        for role in roles:
            try:
                await self.ldap.modify(
                    role.dn,
                    {"roleOccupant": ("delete", [user_dn])}
                )
                count += 1
            except LdapOperationError:
                pass
        
        if count > 0:
            logger.info("user_removed_from_roles", user_dn=user_dn, count=count)
        
        return count
