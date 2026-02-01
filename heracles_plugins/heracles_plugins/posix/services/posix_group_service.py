"""
POSIX Group Service
===================

Business logic for standalone POSIX group management.
Handles GID allocation, memberUid, and group CRUD operations.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

import structlog

from heracles_api.services.ldap_service import LdapService, LdapOperationError

from .base import PosixValidationError, get_int, get_int_optional
from ..schemas import (
    PosixGroupCreate,
    PosixGroupRead,
    PosixGroupUpdate,
    PosixGroupFullCreate,
    PosixGroupListItem,
    TrustMode,
)

logger = structlog.get_logger(__name__)


class PosixGroupService:
    """
    Service for managing standalone POSIX groups.
    
    In standard LDAP, posixGroup is a standalone structural objectClass,
    NOT something you add to groupOfNames.
    
    POSIX groups use:
    - cn: Group name
    - gidNumber: Group ID
    - memberUid: List of member user IDs
    - description: Optional description
    - host: List of hosts (hostObject) for system trust
    
    Host validation is performed against the systems plugin when available.
    If the systems plugin is not loaded, host values are accepted without validation.
    """
    
    OBJECT_CLASSES = ["posixGroup"]
    
    MANAGED_ATTRIBUTES = [
        "cn",
        "gidNumber",
        "memberUid",
        "description",
        "host",  # hostObject attribute for system trust
    ]
    
    def __init__(self, ldap_service: LdapService, config: Dict[str, Any]):
        self._ldap = ldap_service
        self._config = config
        
        self._gid_min = config.get("gid_min", 10000)
        self._gid_max = config.get("gid_max", 60000)
        # Note: posix_groups_ou in plugin config takes precedence over global groups_rdn
        # If not set, we'll use the global groups_rdn at runtime
        self._groups_ou_override = config.get("posix_groups_ou")
    
    async def _get_groups_ou(self) -> str:
        """Get the groups OU, using global config if not overridden."""
        if self._groups_ou_override:
            return self._groups_ou_override
        # Use global groups_rdn setting
        from heracles_api.core.ldap_config import get_groups_rdn
        return await get_groups_rdn()
    
    async def _get_groups_container(self, base_dn: Optional[str] = None) -> str:
        """Get the groups container DN for the given context.
        
        If base_dn is provided (department context), returns ou=groups,{base_dn}.
        Otherwise returns the default ou=groups,{root_base_dn}.
        """
        groups_ou = await self._get_groups_ou()
        if base_dn:
            return f"{groups_ou},{base_dn}"
        from heracles_api.config import settings
        return f"{groups_ou},{settings.LDAP_BASE_DN}"
    
    # Keep legacy method for backward compatibility
    async def _get_groups_base_dn(self) -> str:
        """Get the base DN for POSIX groups (legacy, use _get_groups_container)."""
        return await self._get_groups_container()
    
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
    
    async def _get_group_dn(self, cn: str, base_dn: Optional[str] = None) -> str:
        """Get the DN for a POSIX group by cn."""
        container = await self._get_groups_container(base_dn)
        return f"cn={cn},{container}"
    
    # =========================================================================
    # CRUD Operations for Standalone POSIX Groups
    # =========================================================================
    
    async def list_all(self, base_dn: Optional[str] = None) -> List[PosixGroupListItem]:
        """List all POSIX groups."""
        try:
            # Get the groups container for the given context
            search_base = await self._get_groups_container(base_dn)
            
            entries = await self._ldap.search(
                search_base=search_base,
                search_filter="(objectClass=posixGroup)",
                attributes=["cn", "gidNumber", "description", "memberUid"],
            )
            
            groups = []
            for entry in entries:
                member_uid = entry.get("memberUid", [])
                if isinstance(member_uid, str):
                    member_uid = [member_uid]
                
                groups.append(PosixGroupListItem(
                    cn=entry.get_first("cn", ""),
                    gidNumber=self._get_int(entry, "gidNumber"),
                    description=entry.get_first("description"),
                    memberCount=len(member_uid),
                ))
            
            # Sort by cn
            groups.sort(key=lambda g: g.cn)
            return groups
            
        except LdapOperationError as e:
            logger.error("list_posix_groups_failed", error=str(e))
            raise PosixValidationError(f"Failed to list POSIX groups: {e}")
    
    async def get(
        self, 
        cn: str,
        base_dn: Optional[str] = None
    ) -> Optional[PosixGroupRead]:
        """Get a POSIX group by cn."""
        dn = await self._get_group_dn(cn, base_dn=base_dn)
        
        try:
            # Include objectClass to verify it's a posixGroup
            entry = await self._ldap.get_by_dn(dn, attributes=self.MANAGED_ATTRIBUTES + ["objectClass"])
            if entry is None:
                return None
            
            # Verify it's actually a posixGroup
            object_classes = entry.get("objectClass", [])
            if isinstance(object_classes, str):
                object_classes = [object_classes]
            if "posixGroup" not in object_classes:
                return None
            
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
            
            return PosixGroupRead(
                cn=entry.get_first("cn", cn),
                gidNumber=self._get_int(entry, "gidNumber"),
                description=entry.get_first("description"),
                memberUid=member_uid,
                trustMode=trust_mode,
                host=filtered_hosts if filtered_hosts else None,
                is_active=True,
            )
            
        except LdapOperationError as e:
            logger.error("get_posix_group_failed", cn=cn, error=str(e))
            return None
    
    async def create(
        self, 
        data: PosixGroupFullCreate,
        base_dn: Optional[str] = None
    ) -> PosixGroupRead:
        """Create a new standalone POSIX group."""
        dn = await self._get_group_dn(data.cn, base_dn=base_dn)
        
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
        object_classes = ["posixGroup"]
        if data.trust_mode is not None:
            object_classes.append("hostObject")
        
        # Build attributes for the new entry
        attributes = {
            "cn": [data.cn],
            "gidNumber": [str(gid_number)],
        }
        
        if data.description:
            attributes["description"] = [data.description]
        
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
            logger.info("posix_group_created", cn=data.cn, gid_number=gid_number)
        except LdapOperationError as e:
            logger.error("create_posix_group_failed", cn=data.cn, error=str(e))
            raise PosixValidationError(f"Failed to create POSIX group: {e}")
        
        return await self.get(data.cn, base_dn=base_dn)
    
    async def update_group(
        self, 
        cn: str, 
        data: PosixGroupUpdate,
        base_dn: Optional[str] = None
    ) -> PosixGroupRead:
        """Update a POSIX group."""
        dn = await self._get_group_dn(cn, base_dn=base_dn)
        
        # Verify group exists
        existing = await self.get(cn, base_dn=base_dn)
        if existing is None:
            raise PosixValidationError(f"POSIX group '{cn}' not found")
        
        changes = {}
        
        if data.description is not None:
            if data.description:
                changes["description"] = ("replace", [data.description])
            else:
                # Remove description if empty
                changes["description"] = ("delete", [])
        
        if data.member_uid is not None:
            if data.member_uid:
                changes["memberUid"] = ("replace", data.member_uid)
            else:
                # Remove all members
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
                logger.info("posix_group_updated", cn=cn)
            except LdapOperationError as e:
                logger.error("update_posix_group_failed", cn=cn, error=str(e))
                raise PosixValidationError(f"Failed to update POSIX group: {e}")
        
        return await self.get(cn, base_dn=base_dn)
    
    async def delete(
        self, 
        cn: str,
        base_dn: Optional[str] = None
    ) -> None:
        """Delete a POSIX group."""
        dn = await self._get_group_dn(cn, base_dn=base_dn)
        
        # Verify group exists
        existing = await self.get(cn, base_dn=base_dn)
        if existing is None:
            raise PosixValidationError(f"POSIX group '{cn}' not found")
        
        try:
            await self._ldap.delete(dn)
            logger.info("posix_group_deleted", cn=cn)
        except LdapOperationError as e:
            logger.error("delete_posix_group_failed", cn=cn, error=str(e))
            raise PosixValidationError(f"Failed to delete POSIX group: {e}")
    
    # =========================================================================
    # Member Management (by cn)
    # =========================================================================
    
    async def add_member_by_cn(
        self, 
        cn: str, 
        uid: str,
        base_dn: Optional[str] = None
    ) -> PosixGroupRead:
        """Add a member (by uid) to a POSIX group (by cn)."""
        dn = await self._get_group_dn(cn, base_dn=base_dn)
        
        group = await self.get(cn, base_dn=base_dn)
        if group is None:
            raise PosixValidationError(f"POSIX group '{cn}' not found")
        
        if uid in group.member_uid:
            return group  # Already a member
        
        try:
            await self._ldap.modify(dn, {"memberUid": ("add", [uid])})
            logger.info("posix_group_member_added", cn=cn, uid=uid)
        except LdapOperationError as e:
            raise PosixValidationError(f"Failed to add member: {e}")
        
        return await self.get(cn, base_dn=base_dn)
    
    async def remove_member_by_cn(
        self, 
        cn: str, 
        uid: str,
        base_dn: Optional[str] = None
    ) -> PosixGroupRead:
        """Remove a member (by uid) from a POSIX group (by cn)."""
        dn = await self._get_group_dn(cn, base_dn=base_dn)
        
        group = await self.get(cn, base_dn=base_dn)
        if group is None:
            raise PosixValidationError(f"POSIX group '{cn}' not found")
        
        if uid not in group.member_uid:
            return group  # Not a member
        
        try:
            await self._ldap.modify(dn, {"memberUid": ("delete", [uid])})
            logger.info("posix_group_member_removed", cn=cn, uid=uid)
        except LdapOperationError as e:
            raise PosixValidationError(f"Failed to remove member: {e}")
        
        return await self.get(cn, base_dn=base_dn)
    
    # =========================================================================
    # Legacy methods (for backward compatibility)
    # =========================================================================
    
    async def is_active(self, dn: str) -> bool:
        """Check if POSIX is active on the group (by DN)."""
        try:
            entry = await self._ldap.get_by_dn(dn, attributes=["objectClass"])
            if entry is None:
                return False
            
            object_classes = entry.get("objectClass", [])
            if isinstance(object_classes, str):
                object_classes = [object_classes]
            
            return "posixGroup" in object_classes
            
        except LdapOperationError:
            return False
    
    async def read(self, dn: str) -> Optional[PosixGroupRead]:
        """Read POSIX attributes from a group (by DN) - legacy method."""
        if not await self.is_active(dn):
            return None
        
        try:
            entry = await self._ldap.get_by_dn(dn, attributes=self.MANAGED_ATTRIBUTES)
            if entry is None:
                return None
            
            member_uid = entry.get("memberUid", [])
            if isinstance(member_uid, str):
                member_uid = [member_uid]
            
            return PosixGroupRead(
                cn=entry.get_first("cn", ""),
                gidNumber=self._get_int(entry, "gidNumber"),
                description=entry.get_first("description"),
                memberUid=member_uid,
                is_active=True,
            )
            
        except LdapOperationError as e:
            logger.error("posix_group_read_failed", dn=dn, error=str(e))
            raise
    
    # =========================================================================
    # GID Allocation
    # =========================================================================
    
    async def _allocate_next_gid(self) -> int:
        """Allocate the next available GID number."""
        try:
            entries = await self._ldap.search(
                search_filter="(objectClass=posixGroup)",
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
