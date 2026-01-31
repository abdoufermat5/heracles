"""
Group Repository
================

Data access layer for group LDAP operations.
"""

from typing import Optional, List
from dataclasses import dataclass

from heracles_api.services.ldap_service import LdapService, LdapEntry, LdapOperationError
from heracles_api.schemas.group import GroupCreate, GroupUpdate
from heracles_api.config import settings

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class GroupSearchResult:
    """Group search result with pagination info."""
    groups: List[LdapEntry]
    total: int


class GroupRepository:
    """
    Repository for group LDAP operations.
    
    Provides a clean interface for CRUD operations on groups.
    """
    
    OBJECT_CLASSES = ["groupOfNames"]
    GROUP_ATTRIBUTES = ["cn", "description", "member"]
    
    def __init__(self, ldap: LdapService):
        self.ldap = ldap
        self.base_dn = settings.LDAP_BASE_DN
    
    def _build_group_dn(self, cn: str, ou: str = "groups", department_dn: Optional[str] = None) -> str:
        """
        Build group DN from CN.

        Args:
            cn: Group common name
            ou: Container OU name (default: "groups")
            department_dn: Optional department DN to create group within

        Returns:
            Group DN string
        """
        if department_dn:
            # Create under ou=groups within the department
            # e.g., cn=dev-team,ou=groups,ou=Engineering,dc=heracles,dc=local
            return f"cn={cn},ou={ou},{department_dn}"
        return f"cn={cn},ou={ou},{self.base_dn}"
    
    @staticmethod
    def _extract_uid_from_dn(dn: str) -> str:
        """Extract UID from user DN."""
        for part in dn.split(","):
            if part.strip().lower().startswith("uid="):
                return part.split("=", 1)[1]
        return dn
    
    def _get_members_list(self, entry: LdapEntry) -> List[str]:
        """Get members list from entry, handling single value case."""
        members = entry.get("member", [])
        if isinstance(members, str):
            return [members] if members else []
        return list(members) if members else []
    
    async def find_by_cn(self, cn: str) -> Optional[LdapEntry]:
        """Find group by CN."""
        entries = await self.ldap.search(
            search_filter=f"(&(objectClass=groupOfNames)(cn={self.ldap._escape_filter(cn)}))",
            attributes=self.GROUP_ATTRIBUTES,
        )
        return entries[0] if entries else None
    
    async def find_by_dn(self, dn: str) -> Optional[LdapEntry]:
        """Find group by DN."""
        return await self.ldap.get_by_dn(dn, attributes=self.GROUP_ATTRIBUTES)
    
    async def exists(self, cn: str) -> bool:
        """Check if group exists."""
        entries = await self.ldap.search(
            search_filter=f"(cn={self.ldap._escape_filter(cn)})",
            attributes=["cn"],
        )
        return len(entries) > 0
    
    async def search(
        self,
        search_term: Optional[str] = None,
        ou: Optional[str] = None,
        base_dn: Optional[str] = None,
        limit: int = 0,
    ) -> GroupSearchResult:
        """
        Search groups with optional filtering.

        Args:
            search_term: Search in cn, description
            ou: Filter by organizational unit (legacy, use base_dn for departments)
            base_dn: Base DN to search from (e.g., department DN for scoped search)
            limit: Maximum results (0 = unlimited)
        """
        base_filter = "(objectClass=groupOfNames)"

        if search_term:
            escaped = self.ldap._escape_filter(search_term)
            search_filter = f"(&{base_filter}(|(cn=*{escaped}*)(description=*{escaped}*)))"
        else:
            search_filter = base_filter

        # Determine search base
        # We always search from ou=groups within the specified context
        # to avoid returning groups from all departments when at root level
        groups_ou = ou or "groups"
        if base_dn:
            # Search within department's groups container
            # e.g., ou=groups,ou=Test,dc=heracles,dc=local
            search_base = f"ou={groups_ou},{base_dn}"
        else:
            # Search only in root-level groups container
            # e.g., ou=groups,dc=heracles,dc=local
            search_base = f"ou={groups_ou},{self.base_dn}"

        entries = await self.ldap.search(
            search_base=search_base,
            search_filter=search_filter,
            attributes=self.GROUP_ATTRIBUTES,
            size_limit=limit,
        )

        return GroupSearchResult(groups=entries, total=len(entries))
    
    async def create(
        self,
        group: GroupCreate,
        member_dns: List[str],
        default_member_dn: str,
        department_dn: Optional[str] = None,
    ) -> LdapEntry:
        """
        Create a new group.

        Args:
            group: Group creation data
            member_dns: List of member DNs (resolved from UIDs)
            default_member_dn: DN to use if no members provided (groupOfNames requires at least one)
            department_dn: Optional department DN (group will be created under ou=groups within this dept)

        Returns:
            Created group entry
        """
        group_dn = self._build_group_dn(group.cn, group.ou, department_dn)
        
        # groupOfNames requires at least one member
        members = member_dns if member_dns else [default_member_dn]
        
        attrs = {
            "member": members,
        }
        
        if group.description:
            attrs["description"] = group.description
        
        await self.ldap.add(
            dn=group_dn,
            object_classes=self.OBJECT_CLASSES,
            attributes=attrs,
        )
        
        logger.info("group_created", cn=group.cn, dn=group_dn)
        
        return await self.find_by_dn(group_dn)
    
    async def update(self, cn: str, updates: GroupUpdate) -> Optional[LdapEntry]:
        """
        Update group attributes.
        
        Args:
            cn: Group CN
            updates: Fields to update
            
        Returns:
            Updated group entry or None if not found
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
            logger.info("group_updated", cn=cn, changes=list(changes.keys()))
        
        return await self.find_by_cn(cn)
    
    async def delete(self, cn: str) -> bool:
        """
        Delete a group.
        
        Args:
            cn: Group CN
            
        Returns:
            True if deleted, False if not found
        """
        entry = await self.find_by_cn(cn)
        if not entry:
            return False
        
        await self.ldap.delete(entry.dn)
        logger.info("group_deleted", cn=cn)
        
        return True
    
    async def add_member(self, cn: str, member_dn: str) -> bool:
        """
        Add a member to a group.
        
        Args:
            cn: Group CN
            member_dn: Member DN to add
            
        Returns:
            True if added, False if group not found
            
        Raises:
            LdapOperationError: If member already exists or operation fails
        """
        entry = await self.find_by_cn(cn)
        if not entry:
            return False
        
        # Check if already a member
        existing_members = self._get_members_list(entry)
        if member_dn in existing_members:
            raise LdapOperationError(f"Member already exists in group")
        
        await self.ldap.modify(
            entry.dn,
            {"member": ("add", [member_dn])}
        )
        
        logger.info("group_member_added", cn=cn, member_dn=member_dn)
        return True
    
    async def remove_member(self, cn: str, member_dn: str) -> bool:
        """
        Remove a member from a group.
        
        Args:
            cn: Group CN
            member_dn: Member DN to remove
            
        Returns:
            True if removed, False if group not found
            
        Raises:
            LdapOperationError: If member not found or is last member
        """
        entry = await self.find_by_cn(cn)
        if not entry:
            return False
        
        existing_members = self._get_members_list(entry)
        
        if member_dn not in existing_members:
            raise LdapOperationError("Member not found in group")
        
        if len(existing_members) <= 1:
            raise LdapOperationError("Cannot remove the last member of a group")
        
        await self.ldap.modify(
            entry.dn,
            {"member": ("delete", [member_dn])}
        )
        
        logger.info("group_member_removed", cn=cn, member_dn=member_dn)
        return True
    
    async def get_members(self, cn: str) -> List[str]:
        """
        Get group members as UIDs.
        
        Args:
            cn: Group CN
            
        Returns:
            List of member UIDs
        """
        entry = await self.find_by_cn(cn)
        if not entry:
            return []
        
        members = self._get_members_list(entry)
        return [self._extract_uid_from_dn(dn) for dn in members if dn]
    
    async def is_member(self, cn: str, member_dn: str) -> bool:
        """
        Check if DN is a member of the group.
        
        Args:
            cn: Group CN
            member_dn: Member DN to check
            
        Returns:
            True if member, False otherwise
        """
        entry = await self.find_by_cn(cn)
        if not entry:
            return False
        
        members = self._get_members_list(entry)
        return member_dn in members
    
    async def get_user_groups(self, user_dn: str) -> List[LdapEntry]:
        """
        Get all groups a user belongs to.
        
        Args:
            user_dn: User DN
            
        Returns:
            List of group entries
        """
        entries = await self.ldap.search(
            search_filter=f"(&(objectClass=groupOfNames)(member={user_dn}))",
            attributes=self.GROUP_ATTRIBUTES,
        )
        return entries
    
    async def remove_user_from_all_groups(self, user_dn: str) -> int:
        """
        Remove user from all groups.
        
        Args:
            user_dn: User DN to remove
            
        Returns:
            Number of groups the user was removed from
        """
        groups = await self.get_user_groups(user_dn)
        count = 0
        
        for group in groups:
            try:
                members = self._get_members_list(group)
                # Don't remove if last member
                if len(members) > 1:
                    await self.ldap.modify(
                        group.dn,
                        {"member": ("delete", [user_dn])}
                    )
                    count += 1
            except LdapOperationError:
                pass
        
        if count > 0:
            logger.info("user_removed_from_groups", user_dn=user_dn, count=count)
        
        return count
