"""
POSIX Service
=============

Business logic for POSIX account management.
Handles UID/GID allocation, LDAP operations, and validation.
"""

import time
from typing import Any, Dict, List, Optional, Tuple

import structlog
from ldap3 import MODIFY_ADD, MODIFY_DELETE, MODIFY_REPLACE

from heracles_api.plugins.base import TabService
from heracles_api.services.ldap_service import LdapService, LdapOperationError

from .schemas import (
    PosixAccountCreate,
    PosixAccountRead,
    PosixAccountUpdate,
    PosixGroupCreate,
    PosixGroupRead,
    PosixGroupUpdate,
)

logger = structlog.get_logger(__name__)


class PosixValidationError(Exception):
    """Raised when POSIX validation fails."""
    pass


class PosixService(TabService):
    """
    Service for managing POSIX user accounts.
    
    Handles:
    - posixAccount objectClass
    - shadowAccount objectClass
    - UID number allocation and validation
    """
    
    OBJECT_CLASSES = ["posixAccount", "shadowAccount"]
    
    MANAGED_ATTRIBUTES = [
        "uidNumber",
        "gidNumber", 
        "homeDirectory",
        "loginShell",
        "gecos",
        "shadowLastChange",
        "shadowMin",
        "shadowMax",
        "shadowWarning",
        "shadowInactive",
        "shadowExpire",
    ]
    
    # Default shells configuration
    DEFAULT_SHELLS = [
        {"value": "/bin/bash", "label": "Bash"},
        {"value": "/bin/zsh", "label": "Zsh"},
        {"value": "/bin/sh", "label": "Sh"},
        {"value": "/bin/fish", "label": "Fish"},
        {"value": "/usr/sbin/nologin", "label": "No Login"},
        {"value": "/bin/false", "label": "False (disabled)"},
    ]
    
    def __init__(self, ldap_service: LdapService, config: Dict[str, Any]):
        super().__init__(ldap_service, config)
        
        # UID/GID allocation configuration
        self._uid_min = config.get("uid_min", 10000)
        self._uid_max = config.get("uid_max", 60000)
        self._gid_min = config.get("gid_min", 10000)
        self._gid_max = config.get("gid_max", 60000)
        
        # Default settings
        self._default_shell = config.get("default_shell", "/bin/bash")
        self._default_home_base = config.get("default_home_base", "/home")
        
        # Shells list (can be configured)
        self._shells = config.get("shells", self.DEFAULT_SHELLS)
    
    async def is_active(self, dn: str) -> bool:
        """Check if POSIX is active on the user."""
        try:
            entry = await self._ldap.get_by_dn(dn, attributes=["objectClass"])
            if entry is None:
                return False
            
            object_classes = entry.get("objectClass", [])
            if isinstance(object_classes, str):
                object_classes = [object_classes]
            
            return "posixAccount" in object_classes
            
        except LdapOperationError:
            return False
    
    async def read(self, dn: str) -> Optional[PosixAccountRead]:
        """Read POSIX attributes from a user."""
        if not await self.is_active(dn):
            return None
        
        try:
            entry = await self._ldap.get_by_dn(dn, attributes=self.MANAGED_ATTRIBUTES)
            if entry is None:
                return None
            
            return PosixAccountRead(
                uidNumber=self._get_int(entry, "uidNumber"),
                gidNumber=self._get_int(entry, "gidNumber"),
                homeDirectory=entry.get_first("homeDirectory", ""),
                loginShell=entry.get_first("loginShell", self._default_shell),
                gecos=entry.get_first("gecos"),
                shadowLastChange=self._get_int_optional(entry, "shadowLastChange"),
                shadowMin=self._get_int_optional(entry, "shadowMin"),
                shadowMax=self._get_int_optional(entry, "shadowMax"),
                shadowWarning=self._get_int_optional(entry, "shadowWarning"),
                shadowInactive=self._get_int_optional(entry, "shadowInactive"),
                shadowExpire=self._get_int_optional(entry, "shadowExpire"),
                is_active=True,
            )
            
        except LdapOperationError as e:
            logger.error("posix_read_failed", dn=dn, error=str(e))
            raise
    
    async def activate(
        self,
        dn: str,
        data: PosixAccountCreate,
        uid: Optional[str] = None,
    ) -> PosixAccountRead:
        """
        Activate POSIX on a user.
        
        Args:
            dn: User's DN
            data: POSIX account data
            uid: User's uid (for home directory generation)
        """
        if await self.is_active(dn):
            raise PosixValidationError("POSIX is already active on this user")
        
        # Allocate UID if not provided
        uid_number = data.uid_number
        if uid_number is None:
            uid_number = await self._allocate_next_uid()
        else:
            # Verify UID is not already in use
            if await self._uid_exists(uid_number):
                raise PosixValidationError(f"UID {uid_number} is already in use")
        
        # Verify GID exists
        if not await self._gid_exists(data.gid_number):
            raise PosixValidationError(
                f"GID {data.gid_number} does not exist. "
                "Please create a POSIX group first or use an existing GID."
            )
        
        # Generate home directory if not provided
        home_directory = data.home_directory
        if home_directory is None:
            if uid is None:
                # Try to get uid from LDAP
                entry = await self._ldap.get_by_dn(dn, attributes=["uid"])
                uid = entry.get_first("uid") if entry else None
            
            if uid:
                home_directory = f"{self._default_home_base}/{uid}"
            else:
                raise PosixValidationError(
                    "Cannot generate home directory: uid not provided"
                )
        
        # Generate GECOS if not provided
        gecos = data.gecos
        if gecos is None:
            entry = await self._ldap.get_by_dn(dn, attributes=["cn"])
            gecos = entry.get_first("cn") if entry else None
        
        # Build LDAP modifications
        changes = {
            "objectClass": [(MODIFY_ADD, ["posixAccount", "shadowAccount"])],
            "uidNumber": [(MODIFY_ADD, [str(uid_number)])],
            "gidNumber": [(MODIFY_ADD, [str(data.gid_number)])],
            "homeDirectory": [(MODIFY_ADD, [home_directory])],
            "loginShell": [(MODIFY_ADD, [data.login_shell or self._default_shell])],
        }
        
        if gecos:
            changes["gecos"] = [(MODIFY_ADD, [gecos])]
        
        # Initialize shadow account
        shadow_last_change = int(time.time() / 86400)  # Days since epoch
        changes["shadowLastChange"] = [(MODIFY_ADD, [str(shadow_last_change)])]
        changes["shadowMax"] = [(MODIFY_ADD, ["99999"])]
        
        # Apply changes
        try:
            await self._ldap.modify(dn, changes)
            logger.info(
                "posix_activated",
                dn=dn,
                uid_number=uid_number,
                gid_number=data.gid_number,
            )
        except LdapOperationError as e:
            logger.error("posix_activation_failed", dn=dn, error=str(e))
            raise PosixValidationError(f"Failed to activate POSIX: {e}")
        
        return await self.read(dn)
    
    async def update(self, dn: str, data: PosixAccountUpdate) -> PosixAccountRead:
        """Update POSIX attributes on a user."""
        if not await self.is_active(dn):
            raise PosixValidationError("POSIX is not active on this user")
        
        changes = {}
        
        if data.gid_number is not None:
            if not await self._gid_exists(data.gid_number):
                raise PosixValidationError(f"GID {data.gid_number} does not exist")
            changes["gidNumber"] = [(MODIFY_REPLACE, [str(data.gid_number)])]
        
        if data.home_directory is not None:
            changes["homeDirectory"] = [(MODIFY_REPLACE, [data.home_directory])]
        
        if data.login_shell is not None:
            changes["loginShell"] = [(MODIFY_REPLACE, [data.login_shell])]
        
        if data.gecos is not None:
            if data.gecos == "":
                changes["gecos"] = [(MODIFY_DELETE, [])]
            else:
                changes["gecos"] = [(MODIFY_REPLACE, [data.gecos])]
        
        # Shadow attributes
        if data.shadow_min is not None:
            changes["shadowMin"] = [(MODIFY_REPLACE, [str(data.shadow_min)])]
        
        if data.shadow_max is not None:
            changes["shadowMax"] = [(MODIFY_REPLACE, [str(data.shadow_max)])]
        
        if data.shadow_warning is not None:
            changes["shadowWarning"] = [(MODIFY_REPLACE, [str(data.shadow_warning)])]
        
        if data.shadow_inactive is not None:
            changes["shadowInactive"] = [(MODIFY_REPLACE, [str(data.shadow_inactive)])]
        
        if data.shadow_expire is not None:
            changes["shadowExpire"] = [(MODIFY_REPLACE, [str(data.shadow_expire)])]
        
        if changes:
            try:
                await self._ldap.modify(dn, changes)
                logger.info("posix_updated", dn=dn, changes=len(changes))
            except LdapOperationError as e:
                logger.error("posix_update_failed", dn=dn, error=str(e))
                raise PosixValidationError(f"Failed to update POSIX: {e}")
        
        return await self.read(dn)
    
    async def deactivate(self, dn: str) -> None:
        """Deactivate POSIX on a user."""
        if not await self.is_active(dn):
            raise PosixValidationError("POSIX is not active on this user")
        
        # Read current values to properly delete
        entry = await self._ldap.get_by_dn(dn, attributes=self.MANAGED_ATTRIBUTES)
        
        changes = {
            "objectClass": [(MODIFY_DELETE, ["posixAccount", "shadowAccount"])],
        }
        
        # Delete all managed attributes that have values
        for attr in self.MANAGED_ATTRIBUTES:
            value = entry.get(attr) if entry else None
            if value:
                changes[attr] = [(MODIFY_DELETE, [])]
        
        try:
            await self._ldap.modify(dn, changes)
            logger.info("posix_deactivated", dn=dn)
        except LdapOperationError as e:
            logger.error("posix_deactivation_failed", dn=dn, error=str(e))
            raise PosixValidationError(f"Failed to deactivate POSIX: {e}")
    
    # =========================================================================
    # UID/GID Allocation
    # =========================================================================
    
    async def _allocate_next_uid(self) -> int:
        """
        Allocate the next available UID number.
        
        Scans LDAP to find the highest used UID and returns the next one.
        """
        # Search for all used UIDs
        try:
            entries = await self._ldap.search(
                search_filter="(objectClass=posixAccount)",
                attributes=["uidNumber"],
            )
            
            used_uids = set()
            for entry in entries:
                uid = self._get_int_optional(entry, "uidNumber")
                if uid is not None:
                    used_uids.add(uid)
            
            # Find next available in range
            for uid in range(self._uid_min, self._uid_max + 1):
                if uid not in used_uids:
                    return uid
            
            raise PosixValidationError(
                f"No available UIDs in range {self._uid_min}-{self._uid_max}"
            )
            
        except LdapOperationError as e:
            logger.error("uid_allocation_failed", error=str(e))
            raise PosixValidationError(f"Failed to allocate UID: {e}")
    
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
            logger.error("gid_allocation_failed", error=str(e))
            raise PosixValidationError(f"Failed to allocate GID: {e}")
    
    async def _uid_exists(self, uid_number: int) -> bool:
        """Check if a UID number is already in use."""
        try:
            entries = await self._ldap.search(
                search_filter=f"(uidNumber={uid_number})",
                attributes=["uidNumber"],
            )
            return len(entries) > 0
        except LdapOperationError:
            return False
    
    async def _gid_exists(self, gid_number: int) -> bool:
        """Check if a GID number exists (as posixGroup)."""
        try:
            entries = await self._ldap.search(
                search_filter=f"(&(objectClass=posixGroup)(gidNumber={gid_number}))",
                attributes=["gidNumber"],
            )
            return len(entries) > 0
        except LdapOperationError:
            return False
    
    async def get_next_uid(self) -> int:
        """Get the next available UID (public method for API)."""
        return await self._allocate_next_uid()
    
    async def get_next_gid(self) -> int:
        """Get the next available GID (public method for API)."""
        return await self._allocate_next_gid()
    
    def get_shells(self) -> List[dict]:
        """Get available login shells."""
        return self._shells
    
    def get_default_shell(self) -> str:
        """Get the default shell."""
        return self._default_shell
    
    def get_id_ranges(self) -> dict:
        """Get UID/GID ranges."""
        return {
            "uid": {"min": self._uid_min, "max": self._uid_max},
            "gid": {"min": self._gid_min, "max": self._gid_max},
        }
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _get_int(self, entry: Any, attr: str) -> int:
        """Get integer attribute, raising if not present."""
        val = entry.get_first(attr) if hasattr(entry, 'get_first') else entry.get(attr, [None])[0]
        if val is None:
            raise PosixValidationError(f"Missing required attribute: {attr}")
        return int(val)
    
    def _get_int_optional(self, entry: Any, attr: str) -> Optional[int]:
        """Get optional integer attribute."""
        if hasattr(entry, 'get_first'):
            val = entry.get_first(attr)
        else:
            vals = entry.get(attr, [])
            val = vals[0] if vals else None
        return int(val) if val is not None else None


class PosixGroupService:
    """
    Service for managing standalone POSIX groups.
    
    Following FusionDirectory's model, posixGroup is a standalone structural
    objectClass, NOT something you add to groupOfNames.
    
    POSIX groups use:
    - cn: Group name
    - gidNumber: Group ID
    - memberUid: List of member user IDs
    - description: Optional description
    """
    
    OBJECT_CLASSES = ["posixGroup"]
    
    MANAGED_ATTRIBUTES = [
        "cn",
        "gidNumber",
        "memberUid",
        "description",
    ]
    
    def __init__(self, ldap_service: LdapService, config: Dict[str, Any]):
        self._ldap = ldap_service
        self._config = config
        
        self._gid_min = config.get("gid_min", 10000)
        self._gid_max = config.get("gid_max", 60000)
        self._groups_ou = config.get("posix_groups_ou", "ou=groups")
    
    def _get_groups_base_dn(self) -> str:
        """Get the base DN for POSIX groups."""
        from heracles_api.config import settings
        return f"{self._groups_ou},{settings.LDAP_BASE_DN}"
    
    def _get_group_dn(self, cn: str) -> str:
        """Get the DN for a POSIX group by cn."""
        return f"cn={cn},{self._get_groups_base_dn()}"
    
    # =========================================================================
    # CRUD Operations for Standalone POSIX Groups
    # =========================================================================
    
    async def list_all(self) -> List["PosixGroupListItem"]:
        """List all POSIX groups."""
        from .schemas import PosixGroupListItem
        
        try:
            entries = await self._ldap.search(
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
    
    async def get(self, cn: str) -> Optional["PosixGroupRead"]:
        """Get a POSIX group by cn."""
        from .schemas import PosixGroupRead
        
        dn = self._get_group_dn(cn)
        
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
            
            return PosixGroupRead(
                cn=entry.get_first("cn", cn),
                gidNumber=self._get_int(entry, "gidNumber"),
                description=entry.get_first("description"),
                memberUid=member_uid,
                is_active=True,
            )
            
        except LdapOperationError as e:
            logger.error("get_posix_group_failed", cn=cn, error=str(e))
            return None
    
    async def create(self, data: "PosixGroupFullCreate") -> "PosixGroupRead":
        """Create a new standalone POSIX group."""
        from .schemas import PosixGroupRead, PosixGroupFullCreate
        
        dn = self._get_group_dn(data.cn)
        
        # Check if group already exists
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing is not None:
            raise PosixValidationError(f"Group '{data.cn}' already exists")
        
        # Allocate GID if not provided
        gid_number = data.gid_number
        if gid_number is None:
            gid_number = await self._allocate_next_gid()
        else:
            # Verify GID is not already in use
            if await self._gid_exists(gid_number):
                raise PosixValidationError(f"GID {gid_number} is already in use")
        
        # Build attributes for the new entry
        attributes = {
            "cn": [data.cn],
            "gidNumber": [str(gid_number)],
        }
        
        if data.description:
            attributes["description"] = [data.description]
        
        if data.member_uid:
            attributes["memberUid"] = data.member_uid
        
        try:
            await self._ldap.add(dn, ["posixGroup"], attributes)
            logger.info("posix_group_created", cn=data.cn, gid_number=gid_number)
        except LdapOperationError as e:
            logger.error("create_posix_group_failed", cn=data.cn, error=str(e))
            raise PosixValidationError(f"Failed to create POSIX group: {e}")
        
        return await self.get(data.cn)
    
    async def update_group(self, cn: str, data: "PosixGroupUpdate") -> "PosixGroupRead":
        """Update a POSIX group."""
        from .schemas import PosixGroupUpdate
        
        dn = self._get_group_dn(cn)
        
        # Verify group exists
        existing = await self.get(cn)
        if existing is None:
            raise PosixValidationError(f"POSIX group '{cn}' not found")
        
        changes = {}
        
        if data.description is not None:
            if data.description:
                changes["description"] = [(MODIFY_REPLACE, [data.description])]
            else:
                # Remove description if empty
                changes["description"] = [(MODIFY_DELETE, [])]
        
        if data.member_uid is not None:
            if data.member_uid:
                changes["memberUid"] = [(MODIFY_REPLACE, data.member_uid)]
            else:
                # Remove all members
                if existing.member_uid:
                    changes["memberUid"] = [(MODIFY_DELETE, [])]
        
        if changes:
            try:
                await self._ldap.modify(dn, changes)
                logger.info("posix_group_updated", cn=cn)
            except LdapOperationError as e:
                logger.error("update_posix_group_failed", cn=cn, error=str(e))
                raise PosixValidationError(f"Failed to update POSIX group: {e}")
        
        return await self.get(cn)
    
    async def delete(self, cn: str) -> None:
        """Delete a POSIX group."""
        dn = self._get_group_dn(cn)
        
        # Verify group exists
        existing = await self.get(cn)
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
    
    async def add_member_by_cn(self, cn: str, uid: str) -> "PosixGroupRead":
        """Add a member (by uid) to a POSIX group (by cn)."""
        dn = self._get_group_dn(cn)
        
        group = await self.get(cn)
        if group is None:
            raise PosixValidationError(f"POSIX group '{cn}' not found")
        
        if uid in group.member_uid:
            return group  # Already a member
        
        try:
            await self._ldap.modify(dn, {"memberUid": [(MODIFY_ADD, [uid])]})
            logger.info("posix_group_member_added", cn=cn, uid=uid)
        except LdapOperationError as e:
            raise PosixValidationError(f"Failed to add member: {e}")
        
        return await self.get(cn)
    
    async def remove_member_by_cn(self, cn: str, uid: str) -> "PosixGroupRead":
        """Remove a member (by uid) from a POSIX group (by cn)."""
        dn = self._get_group_dn(cn)
        
        group = await self.get(cn)
        if group is None:
            raise PosixValidationError(f"POSIX group '{cn}' not found")
        
        if uid not in group.member_uid:
            return group  # Not a member
        
        try:
            await self._ldap.modify(dn, {"memberUid": [(MODIFY_DELETE, [uid])]})
            logger.info("posix_group_member_removed", cn=cn, uid=uid)
        except LdapOperationError as e:
            raise PosixValidationError(f"Failed to remove member: {e}")
        
        return await self.get(cn)
    
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
    
    async def read(self, dn: str) -> Optional["PosixGroupRead"]:
        """Read POSIX attributes from a group (by DN) - legacy method."""
        from .schemas import PosixGroupRead
        
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
        val = entry.get_first(attr) if hasattr(entry, 'get_first') else entry.get(attr, [None])[0]
        if val is None:
            raise PosixValidationError(f"Missing required attribute: {attr}")
        return int(val)
    
    def _get_int_optional(self, entry: Any, attr: str) -> Optional[int]:
        """Get optional integer attribute."""
        if hasattr(entry, 'get_first'):
            val = entry.get_first(attr)
        else:
            vals = entry.get(attr, [])
            val = vals[0] if vals else None
        return int(val) if val is not None else None
