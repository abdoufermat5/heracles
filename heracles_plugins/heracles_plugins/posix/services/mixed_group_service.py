"""
Mixed Group Service
===================

Business logic for managing MixedGroups that combine groupOfNames 
with posixGroupAux for dual LDAP/POSIX functionality.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

import structlog

from heracles_api.services.ldap_service import LdapService, LdapOperationError

from .base import PosixValidationError, get_int, get_int_optional
from ..schemas import (
    MixedGroupCreate,
    MixedGroupRead,
    MixedGroupUpdate,
    MixedGroupListItem,
    TrustMode,
)

logger = structlog.get_logger(__name__)


class MixedGroupService:
    """
    Service for managing MixedGroups.
    
    MixedGroups combine groupOfNames (LDAP organizational group)
    with posixGroup (UNIX group) in a single entry.
    
    This allows a group to be used both for:
    - LDAP-based access control (member attribute with DNs)
    - UNIX/POSIX permissions (memberUid attribute with UIDs)
    
    Object classes used:
    - groupOfNames (structural): member attribute
    - posixGroupAux (auxiliary): gidNumber, memberUid - custom auxiliary version
    - hostObject (auxiliary): host attribute for system trust
    
    NOTE: posixGroupAux is an auxiliary version of posixGroup that allows
    combining with groupOfNames. The standard posixGroup is structural and
    cannot be combined with other structural classes like groupOfNames.
    
    Host validation is performed against the systems plugin when available.
    If the systems plugin is not loaded, host values are accepted without validation.
    """
    
    # Use posixGroupAux (auxiliary) instead of posixGroup (structural)
    # This allows combining with groupOfNames in a single entry
    OBJECT_CLASSES = ["groupOfNames", "posixGroupAux"]
    
    MANAGED_ATTRIBUTES = [
        "cn",
        "gidNumber",
        "member",
        "memberUid",
        "description",
        "host",  # hostObject attribute for system trust
    ]
    
    def __init__(self, ldap_service: LdapService, config: Dict[str, Any]):
        self._ldap = ldap_service
        self._config = config
        
        self._gid_min = config.get("gid_min", 10000)
        self._gid_max = config.get("gid_max", 60000)
        self._groups_ou = config.get("mixed_groups_ou", "ou=groups")
    
    def _get_groups_container(self, base_dn: Optional[str] = None) -> str:
        """Get the groups container DN for the given context.
        
        If base_dn is provided (department context), returns ou=groups,{base_dn}.
        Otherwise returns the default ou=groups,{root_base_dn}.
        """
        if base_dn:
            return f"{self._groups_ou},{base_dn}"
        from heracles_api.config import settings
        return f"{self._groups_ou},{settings.LDAP_BASE_DN}"
    
    # Keep legacy method for backward compatibility
    def _get_groups_base_dn(self) -> str:
        """Get the base DN for MixedGroups (legacy, use _get_groups_container)."""
        return self._get_groups_container()
    
    async def _validate_hosts(self, hosts: List[str]) -> List[str]:
        """
        Validate hosts against the systems plugin.
        
        If the systems plugin is available, validates that all hostnames
        correspond to registered systems. Raises PosixValidationError if
        any hosts are invalid.
        
        If the systems plugin is not loaded, accepts all hosts without validation.
        
        Args:
            hosts: List of hostnames to validate
            
        Returns:
            The validated list of hosts (unchanged if valid)
            
        Raises:
            PosixValidationError: If any hosts are not registered in systems
        """
        if not hosts:
            return hosts
        
        try:
            from heracles_api.plugins.registry import plugin_registry
            systems_service = plugin_registry.get_service("systems")
            
            if systems_service is None:
                # Systems plugin not loaded, skip validation
                logger.debug("systems_plugin_not_loaded", action="skipping_host_validation")
                return hosts
            
            # Validate hosts
            result = await systems_service.validate_hosts(hosts)
            
            if result.invalid_hosts:
                raise PosixValidationError(
                    f"Invalid hosts (not registered in systems): {', '.join(result.invalid_hosts)}"
                )
            
            return hosts
            
        except ImportError:
            # Plugin registry not available (e.g., during testing)
            logger.debug("plugin_registry_not_available", action="skipping_host_validation")
            return hosts
    
    def _get_group_dn(self, cn: str, base_dn: Optional[str] = None) -> str:
        """Get the DN for a MixedGroup by cn."""
        container = self._get_groups_container(base_dn)
        return f"cn={cn},{container}"
    
    # =========================================================================
    # CRUD Operations
    # =========================================================================
    
    async def list_all(self, base_dn: Optional[str] = None) -> List[MixedGroupListItem]:
        """List all MixedGroups."""
        try:
            # Get the groups container for the given context
            search_base = self._get_groups_container(base_dn)
            
            # Search for entries that have both groupOfNames and posixGroupAux
            entries = await self._ldap.search(
                search_base=search_base,
                search_filter="(&(objectClass=groupOfNames)(objectClass=posixGroupAux))",
                attributes=["cn", "gidNumber", "description", "member", "memberUid"],
            )
            
            groups = []
            for entry in entries:
                member = entry.get("member", [])
                if isinstance(member, str):
                    member = [member]
                
                member_uid = entry.get("memberUid", [])
                if isinstance(member_uid, str):
                    member_uid = [member_uid]
                
                groups.append(MixedGroupListItem(
                    cn=entry.get_first("cn", ""),
                    gidNumber=self._get_int(entry, "gidNumber"),
                    description=entry.get_first("description"),
                    memberCount=len(member),
                    memberUidCount=len(member_uid),
                ))
            
            groups.sort(key=lambda g: g.cn)
            return groups
            
        except LdapOperationError as e:
            logger.error("list_mixed_groups_failed", error=str(e))
            raise PosixValidationError(f"Failed to list MixedGroups: {e}")
    
    async def get(
        self, 
        cn: str,
        base_dn: Optional[str] = None
    ) -> Optional[MixedGroupRead]:
        """Get a MixedGroup by cn."""
        dn = self._get_group_dn(cn, base_dn=base_dn)
        
        try:
            entry = await self._ldap.get_by_dn(
                dn, 
                attributes=self.MANAGED_ATTRIBUTES + ["objectClass"]
            )
            if entry is None:
                return None
            
            # Verify it's a MixedGroup (groupOfNames + posixGroupAux)
            object_classes = entry.get("objectClass", [])
            if isinstance(object_classes, str):
                object_classes = [object_classes]
            
            if "groupOfNames" not in object_classes or "posixGroupAux" not in object_classes:
                return None
            
            member = entry.get("member", [])
            if isinstance(member, str):
                member = [member]
            
            member_uid = entry.get("memberUid", [])
            if isinstance(member_uid, str):
                member_uid = [member_uid]
            
            # Parse host attribute for trust mode
            host_list = entry.get("host", [])
            if isinstance(host_list, str):
                host_list = [host_list]
            
            trust_mode = None
            filtered_hosts = []
            if host_list:
                # Check for full access marker
                if "*" in host_list or any(h == "*" for h in host_list):
                    trust_mode = TrustMode.FULL_ACCESS
                else:
                    trust_mode = TrustMode.BY_HOST
                    filtered_hosts = [h for h in host_list if h != "*"]
            
            return MixedGroupRead(
                cn=entry.get_first("cn", cn),
                gidNumber=self._get_int(entry, "gidNumber"),
                description=entry.get_first("description"),
                member=member,
                memberUid=member_uid,
                trustMode=trust_mode,
                host=filtered_hosts if filtered_hosts else None,
                isMixedGroup=True,
            )
            
        except LdapOperationError as e:
            logger.error("get_mixed_group_failed", cn=cn, error=str(e))
            return None
    
    async def create(
        self, 
        data: MixedGroupCreate,
        base_dn: Optional[str] = None
    ) -> MixedGroupRead:
        """Create a new MixedGroup."""
        dn = self._get_group_dn(data.cn, base_dn=base_dn)
        
        # Check if group already exists
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing is not None:
            raise PosixValidationError(f"Group '{data.cn}' already exists")
        
        # Allocate GID if not provided
        gid_number = data.gid_number
        if gid_number is None:
            gid_number = await self._allocate_next_gid()
        else:
            # Verify GID is not already in use (unless force_gid is set)
            if not data.force_gid and await self._gid_exists(gid_number):
                raise PosixValidationError(f"GID {gid_number} is already in use")
        
        # Determine object classes
        object_classes = list(self.OBJECT_CLASSES)
        if data.trust_mode is not None:
            object_classes.append("hostObject")
        
        # Build attributes
        attributes = {
            "cn": [data.cn],
            "gidNumber": [str(gid_number)],
        }
        
        if data.description:
            attributes["description"] = [data.description]
        
        # groupOfNames requires at least one member
        # Convert UIDs to DNs if needed and validate members
        if data.member:
            member_dns = await self._resolve_members_to_dns(data.member)
            if member_dns:
                attributes["member"] = member_dns
            else:
                # No valid members resolved, use group's own DN as placeholder
                attributes["member"] = [dn]
        else:
            # Some LDAP implementations require at least one member
            # Use the group's own DN as a placeholder
            attributes["member"] = [dn]
        
        if data.member_uid:
            attributes["memberUid"] = data.member_uid
        
        # Handle system trust (hostObject)
        if data.trust_mode is not None:
            if data.trust_mode == TrustMode.FULL_ACCESS:
                attributes["host"] = ["*"]
            elif data.trust_mode == TrustMode.BY_HOST and data.host:
                # Validate hosts against systems plugin
                await self._validate_hosts(data.host)
                attributes["host"] = data.host
        
        try:
            await self._ldap.add(dn, object_classes, attributes)
            logger.info("mixed_group_created", cn=data.cn, gid_number=gid_number)
        except LdapOperationError as e:
            logger.error("create_mixed_group_failed", cn=data.cn, error=str(e))
            raise PosixValidationError(f"Failed to create MixedGroup: {e}")
        
        return await self.get(data.cn, base_dn=base_dn)
    
    async def update_group(
        self, 
        cn: str, 
        data: MixedGroupUpdate,
        base_dn: Optional[str] = None
    ) -> MixedGroupRead:
        """Update a MixedGroup."""
        dn = self._get_group_dn(cn, base_dn=base_dn)
        
        existing = await self.get(cn, base_dn=base_dn)
        if existing is None:
            raise PosixValidationError(f"MixedGroup '{cn}' not found")
        
        changes = {}
        
        if data.description is not None:
            if data.description:
                changes["description"] = ("replace", [data.description])
            else:
                changes["description"] = ("delete", [])
        
        if data.member is not None:
            if data.member:
                # Resolve UIDs/CNs to full DNs
                resolved_members = await self._resolve_members_to_dns(data.member)
                if resolved_members:
                    changes["member"] = ("replace", resolved_members)
                else:
                    # No valid members, use group's own DN as placeholder
                    changes["member"] = ("replace", [dn])
            else:
                # Keep at least one member (the group itself)
                changes["member"] = ("replace", [dn])
        
        if data.member_uid is not None:
            if data.member_uid:
                changes["memberUid"] = ("replace", data.member_uid)
            else:
                if existing.member_uid:
                    changes["memberUid"] = ("delete", [])
        
        # Handle system trust (hostObject) updates
        if data.trust_mode is not None:
            # Check if hostObject is in objectClasses
            entry = await self._ldap.get_by_dn(dn, attributes=["objectClass", "host"])
            object_classes = entry.get("objectClass", []) if entry else []
            if isinstance(object_classes, str):
                object_classes = [object_classes]
            
            has_host_object = "hostObject" in object_classes
            
            if data.trust_mode == TrustMode.FULL_ACCESS:
                if not has_host_object:
                    changes["objectClass"] = ("add", ["hostObject"])
                changes["host"] = ("replace", ["*"])
            elif data.trust_mode == TrustMode.BY_HOST:
                if not data.host:
                    raise PosixValidationError("host list is required when trustMode is byhost")
                if not has_host_object:
                    changes["objectClass"] = ("add", ["hostObject"])
                # Validate hosts against systems plugin
                await self._validate_hosts(data.host)
                changes["host"] = ("replace", data.host)
        elif data.host is not None:
            # Just update hosts without changing trust mode
            entry = await self._ldap.get_by_dn(dn, attributes=["objectClass"])
            object_classes = entry.get("objectClass", []) if entry else []
            if isinstance(object_classes, str):
                object_classes = [object_classes]
            
            if "hostObject" in object_classes:
                if data.host:
                    changes["host"] = ("replace", data.host)
                else:
                    changes["host"] = ("delete", [])
        
        if changes:
            try:
                await self._ldap.modify(dn, changes)
                logger.info("mixed_group_updated", cn=cn)
            except LdapOperationError as e:
                logger.error("update_mixed_group_failed", cn=cn, error=str(e))
                raise PosixValidationError(f"Failed to update MixedGroup: {e}")
        
        return await self.get(cn, base_dn=base_dn)
    
    async def delete(
        self, 
        cn: str,
        base_dn: Optional[str] = None
    ) -> None:
        """Delete a MixedGroup."""
        dn = self._get_group_dn(cn, base_dn=base_dn)
        
        existing = await self.get(cn, base_dn=base_dn)
        if existing is None:
            raise PosixValidationError(f"MixedGroup '{cn}' not found")
        
        try:
            await self._ldap.delete(dn)
            logger.info("mixed_group_deleted", cn=cn)
        except LdapOperationError as e:
            logger.error("delete_mixed_group_failed", cn=cn, error=str(e))
            raise PosixValidationError(f"Failed to delete MixedGroup: {e}")
    
    # =========================================================================
    # Member Management
    # =========================================================================
    
    async def add_member(
        self, 
        cn: str, 
        member_dn: str,
        base_dn: Optional[str] = None
    ) -> MixedGroupRead:
        """Add a member (by DN) to a MixedGroup."""
        dn = self._get_group_dn(cn, base_dn=base_dn)
        
        group = await self.get(cn, base_dn=base_dn)
        if group is None:
            raise PosixValidationError(f"MixedGroup '{cn}' not found")
        
        if member_dn in group.member:
            return group
        
        try:
            await self._ldap.modify(dn, {"member": ("add", [member_dn])})
            logger.info("mixed_group_member_added", cn=cn, member_dn=member_dn)
        except LdapOperationError as e:
            raise PosixValidationError(f"Failed to add member: {e}")
        
        return await self.get(cn, base_dn=base_dn)
    
    async def remove_member(
        self, 
        cn: str, 
        member_dn: str,
        base_dn: Optional[str] = None
    ) -> MixedGroupRead:
        """Remove a member (by DN) from a MixedGroup."""
        dn = self._get_group_dn(cn, base_dn=base_dn)
        
        group = await self.get(cn, base_dn=base_dn)
        if group is None:
            raise PosixValidationError(f"MixedGroup '{cn}' not found")
        
        if member_dn not in group.member:
            return group
        
        # Ensure at least one member remains
        if len(group.member) <= 1:
            raise PosixValidationError("Cannot remove the last member from a groupOfNames")
        
        try:
            await self._ldap.modify(dn, {"member": ("delete", [member_dn])})
            logger.info("mixed_group_member_removed", cn=cn, member_dn=member_dn)
        except LdapOperationError as e:
            raise PosixValidationError(f"Failed to remove member: {e}")
        
        return await self.get(cn, base_dn=base_dn)
    
    async def add_member_uid(
        self, 
        cn: str, 
        uid: str,
        base_dn: Optional[str] = None
    ) -> MixedGroupRead:
        """Add a memberUid to a MixedGroup."""
        dn = self._get_group_dn(cn, base_dn=base_dn)
        
        group = await self.get(cn, base_dn=base_dn)
        if group is None:
            raise PosixValidationError(f"MixedGroup '{cn}' not found")
        
        if uid in group.member_uid:
            return group
        
        try:
            await self._ldap.modify(dn, {"memberUid": ("add", [uid])})
            logger.info("mixed_group_member_uid_added", cn=cn, uid=uid)
        except LdapOperationError as e:
            raise PosixValidationError(f"Failed to add memberUid: {e}")
        
        return await self.get(cn, base_dn=base_dn)
    
    async def remove_member_uid(
        self, 
        cn: str, 
        uid: str,
        base_dn: Optional[str] = None
    ) -> MixedGroupRead:
        """Remove a memberUid from a MixedGroup."""
        dn = self._get_group_dn(cn, base_dn=base_dn)
        
        group = await self.get(cn, base_dn=base_dn)
        if group is None:
            raise PosixValidationError(f"MixedGroup '{cn}' not found")
        
        if uid not in group.member_uid:
            return group
        
        try:
            await self._ldap.modify(dn, {"memberUid": ("delete", [uid])})
            logger.info("mixed_group_member_uid_removed", cn=cn, uid=uid)
        except LdapOperationError as e:
            raise PosixValidationError(f"Failed to remove memberUid: {e}")
        
        return await self.get(cn, base_dn=base_dn)
    
    # =========================================================================
    # GID Allocation (shared logic with PosixGroupService)
    # =========================================================================
    
    async def _allocate_next_gid(self) -> int:
        """Allocate the next available GID number."""
        try:
            # Search for both posixGroup and MixedGroups
            entries = await self._ldap.search(
                search_filter="(gidNumber=*)",
                attributes=["gidNumber"],
            )
            
            used_gids = set()
            for entry in entries:
                gid = self._get_int_optional(entry, "gidNumber")
                if gid is not None:
                    used_gids.add(gid)
            
            for gid in range(self._gid_min, self._gid_max + 1):
                if gid not in used_gids:
                    return gid
            
            raise PosixValidationError(
                f"No available GIDs in range {self._gid_min}-{self._gid_max}"
            )
            
        except LdapOperationError as e:
            raise PosixValidationError(f"Failed to allocate GID: {e}")
    
    async def _gid_exists(self, gid_number: int) -> bool:
        """Check if a GID number is already in use."""
        try:
            entries = await self._ldap.search(
                search_filter=f"(gidNumber={gid_number})",
                attributes=["gidNumber"],
            )
            return len(entries) > 0
        except LdapOperationError:
            return False
    
    async def get_next_gid(self) -> int:
        """Get the next available GID."""
        return await self._allocate_next_gid()
    
    # =========================================================================
    # Helpers
    # =========================================================================
    
    def _get_int(self, entry: Any, attr: str) -> int:
        """Get integer attribute."""
        return get_int(entry, attr)
    
    def _get_int_optional(self, entry: Any, attr: str) -> Optional[int]:
        """Get optional integer attribute."""
        return get_int_optional(entry, attr)

    async def _resolve_members_to_dns(self, members: List[str]) -> List[str]:
        """
        Resolve member identifiers to full DNs.
        
        Accepts:
        - Full DNs (uid=user,ou=people,dc=... or cn=group,ou=groups,dc=...)
        - UIDs (testuser) - will be resolved to user DN
        - Group CNs (admins) - will be resolved to group DN
        
        Returns list of valid DNs, filtering out unresolved identifiers.
        """
        from heracles_api.config import settings
        
        resolved_dns = []
        
        for member in members:
            # Already a DN
            if "=" in member and "," in member:
                resolved_dns.append(member)
                continue
            
            # Try to resolve as a user UID
            try:
                user_dn = f"uid={member},ou=people,{settings.LDAP_BASE_DN}"
                user_entry = await self._ldap.get_by_dn(user_dn, attributes=["uid"])
                if user_entry is not None:
                    resolved_dns.append(user_dn)
                    continue
            except LdapOperationError:
                pass
            
            # Try to resolve as a group CN
            try:
                group_dn = f"cn={member},ou=groups,{settings.LDAP_BASE_DN}"
                group_entry = await self._ldap.get_by_dn(group_dn, attributes=["cn"])
                if group_entry is not None:
                    resolved_dns.append(group_dn)
                    continue
            except LdapOperationError:
                pass
            
            # Log warning for unresolved member
            logger.warning("member_not_resolved", member=member)
        
        return resolved_dns
