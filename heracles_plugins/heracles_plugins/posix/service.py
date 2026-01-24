"""
POSIX Service
=============

Business logic for POSIX account management.
Handles UID/GID allocation, LDAP operations, and validation.
"""

import time
from typing import Any, Dict, List, Optional, Tuple

import structlog

from heracles_api.plugins.base import TabService
from heracles_api.services.ldap_service import LdapService, LdapOperationError

from .schemas import (
    PosixAccountCreate,
    PosixAccountRead,
    PosixAccountUpdate,
    PosixGroupCreate,
    PosixGroupRead,
    PosixGroupUpdate,
    PosixGroupFullCreate,
    PrimaryGroupMode,
    TrustMode,
    AccountStatus,
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
    - System trust (hostObject)
    - Account status computation
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
        "host",  # hostObject attribute for system trust
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
            entry = await self._ldap.get_by_dn(dn, attributes=self.MANAGED_ATTRIBUTES + ["uid"])
            if entry is None:
                return None
            
            uid = entry.get_first("uid", "")
            gid_number = self._get_int(entry, "gidNumber")
            
            # Get primary group CN by GID
            primary_group_cn = await self._get_group_cn_by_gid(gid_number)
            
            # Get group memberships (groups this user belongs to via memberUid)
            group_memberships = await self._get_user_group_memberships(uid)
            
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
            
            # Get shadow attributes
            shadow_last_change = self._get_int_optional(entry, "shadowLastChange")
            shadow_min = self._get_int_optional(entry, "shadowMin")
            shadow_max = self._get_int_optional(entry, "shadowMax")
            shadow_warning = self._get_int_optional(entry, "shadowWarning")
            shadow_inactive = self._get_int_optional(entry, "shadowInactive")
            shadow_expire = self._get_int_optional(entry, "shadowExpire")
            
            # Compute account status
            account_status = self._compute_account_status(
                shadow_last_change=shadow_last_change,
                shadow_max=shadow_max,
                shadow_inactive=shadow_inactive,
                shadow_expire=shadow_expire,
            )
            
            return PosixAccountRead(
                uidNumber=self._get_int(entry, "uidNumber"),
                gidNumber=gid_number,
                homeDirectory=entry.get_first("homeDirectory", ""),
                loginShell=entry.get_first("loginShell", self._default_shell),
                gecos=entry.get_first("gecos"),
                shadowLastChange=shadow_last_change,
                shadowMin=shadow_min,
                shadowMax=shadow_max,
                shadowWarning=shadow_warning,
                shadowInactive=shadow_inactive,
                shadowExpire=shadow_expire,
                trustMode=trust_mode,
                host=filtered_hosts if filtered_hosts else None,
                primaryGroupCn=primary_group_cn,
                groupMemberships=group_memberships,
                is_active=True,
                accountStatus=account_status,
            )
            
        except LdapOperationError as e:
            logger.error("posix_read_failed", dn=dn, error=str(e))
            raise
    
    async def activate(
        self,
        dn: str,
        data: PosixAccountCreate,
        uid: Optional[str] = None,
        group_service: Optional["PosixGroupService"] = None,
    ) -> PosixAccountRead:
        """
        Activate POSIX on a user.
        
        Args:
            dn: User's DN
            data: POSIX account data
            uid: User's uid (for home directory generation and personal group)
            group_service: PosixGroupService instance (for auto-creating personal groups)
        """
        if await self.is_active(dn):
            raise PosixValidationError("POSIX is already active on this user")
        
        # Allocate UID if not provided
        uid_number = data.uid_number
        if uid_number is None:
            uid_number = await self._allocate_next_uid()
        else:
            # Verify UID is not already in use (unless force_uid is set)
            if not data.force_uid and await self._uid_exists(uid_number):
                raise PosixValidationError(f"UID {uid_number} is already in use")
        
        # Handle primary group
        gid_number: int
        created_personal_group = False
        
        if data.primary_group_mode == PrimaryGroupMode.CREATE_PERSONAL:
            # Auto-create a personal group with the same name as the user
            if uid is None:
                entry = await self._ldap.get_by_dn(dn, attributes=["uid"])
                uid = entry.get_first("uid") if entry else None
            
            if uid is None:
                raise PosixValidationError(
                    "Cannot create personal group: uid not available"
                )
            
            if group_service is None:
                raise PosixValidationError(
                    "Cannot create personal group: group service not available"
                )
            
            # Check if group with this name already exists
            existing_group = await group_service.get(uid)
            if existing_group:
                # Use the existing group
                gid_number = existing_group.gidNumber
                logger.info(
                    "using_existing_personal_group",
                    cn=uid,
                    gid_number=gid_number,
                )
            else:
                # Create new personal group
                from .schemas import PosixGroupFullCreate
                
                # Allocate GID for the personal group
                personal_gid = data.gid_number if data.force_gid and data.gid_number else None
                
                personal_group_data = PosixGroupFullCreate(
                    cn=uid,
                    gidNumber=personal_gid,
                    description=f"Personal group for {uid}",
                )
                
                created_group = await group_service.create(personal_group_data)
                gid_number = created_group.gidNumber
                created_personal_group = True
                
                logger.info(
                    "personal_group_created",
                    cn=uid,
                    gid_number=gid_number,
                )
        else:
            # Use selected existing group
            if data.gid_number is None:
                raise PosixValidationError(
                    "GID number is required when using select_existing mode"
                )
            gid_number = data.gid_number
            
            # Verify GID exists
            if not await self._gid_exists(gid_number):
                raise PosixValidationError(
                    f"GID {gid_number} does not exist. "
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
        object_classes_to_add = ["posixAccount", "shadowAccount"]
        
        # Add hostObject if trust mode is specified
        if data.trust_mode is not None:
            object_classes_to_add.append("hostObject")
        
        changes = {
            "objectClass": ("add", object_classes_to_add),
            "uidNumber": ("add", [str(uid_number)]),
            "gidNumber": ("add", [str(gid_number)]),
            "homeDirectory": ("add", [home_directory]),
            "loginShell": ("add", [data.login_shell or self._default_shell]),
        }
        
        if gecos:
            changes["gecos"] = ("add", [gecos])
        
        # Initialize shadow account
        shadow_last_change = int(time.time() / 86400)  # Days since epoch
        changes["shadowLastChange"] = ("add", [str(shadow_last_change)])
        changes["shadowMax"] = ("add", ["99999"])
        
        # Handle system trust (hostObject)
        if data.trust_mode is not None:
            if data.trust_mode == TrustMode.FULL_ACCESS:
                changes["host"] = ("add", ["*"])
            elif data.trust_mode == TrustMode.BY_HOST and data.host:
                changes["host"] = ("add", data.host)
        
        # Apply changes
        try:
            await self._ldap.modify(dn, changes)
            logger.info(
                "posix_activated",
                dn=dn,
                uid_number=uid_number,
                gid_number=gid_number,
                personal_group_created=created_personal_group,
            )
        except LdapOperationError as e:
            # Rollback personal group creation if it was created
            if created_personal_group and group_service and uid:
                try:
                    await group_service.delete(uid)
                    logger.info("personal_group_rolled_back", cn=uid)
                except Exception as rollback_error:
                    logger.error(
                        "personal_group_rollback_failed",
                        cn=uid,
                        error=str(rollback_error),
                    )
            
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
            changes["gidNumber"] = ("replace", [str(data.gid_number)])
        
        if data.home_directory is not None:
            changes["homeDirectory"] = ("replace", [data.home_directory])
        
        if data.login_shell is not None:
            changes["loginShell"] = ("replace", [data.login_shell])
        
        if data.gecos is not None:
            if data.gecos == "":
                changes["gecos"] = ("delete", [])
            else:
                changes["gecos"] = ("replace", [data.gecos])
        
        # Shadow attributes
        if data.shadow_min is not None:
            changes["shadowMin"] = ("replace", [str(data.shadow_min)])
        
        if data.shadow_max is not None:
            changes["shadowMax"] = ("replace", [str(data.shadow_max)])
        
        if data.shadow_warning is not None:
            changes["shadowWarning"] = ("replace", [str(data.shadow_warning)])
        
        if data.shadow_inactive is not None:
            changes["shadowInactive"] = ("replace", [str(data.shadow_inactive)])
        
        if data.shadow_expire is not None:
            changes["shadowExpire"] = ("replace", [str(data.shadow_expire)])
        
        # Handle must_change_password by setting shadowLastChange to 0
        if data.must_change_password is not None:
            if data.must_change_password:
                # Set shadowLastChange to 0 to force password change
                changes["shadowLastChange"] = ("replace", ["0"])
            else:
                # Reset to current date
                shadow_last_change = int(time.time() / 86400)
                changes["shadowLastChange"] = ("replace", [str(shadow_last_change)])
        
        # Handle system trust (hostObject)
        if data.trust_mode is not None:
            # First check if hostObject is in the objectClasses
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
                logger.info("posix_updated", dn=dn, changes=len(changes))
            except LdapOperationError as e:
                logger.error("posix_update_failed", dn=dn, error=str(e))
                raise PosixValidationError(f"Failed to update POSIX: {e}")
        
        return await self.read(dn)
    
    async def deactivate(
        self,
        dn: str,
        group_service: Optional["PosixGroupService"] = None,
        delete_personal_group: bool = True,
    ) -> None:
        """
        Deactivate POSIX on a user.
        
        Args:
            dn: User's DN
            group_service: PosixGroupService instance (for deleting personal groups)
            delete_personal_group: If True, delete the personal group if it exists and is empty
        """
        if not await self.is_active(dn):
            raise PosixValidationError("POSIX is not active on this user")
        
        # Read current values to properly delete
        entry = await self._ldap.get_by_dn(
            dn, 
            attributes=self.MANAGED_ATTRIBUTES + ["uid", "objectClass"]
        )
        
        uid = entry.get_first("uid") if entry else None
        gid_number = self._get_int_optional(entry, "gidNumber") if entry else None
        
        # Check if user has a personal group to delete
        personal_group_to_delete = None
        if delete_personal_group and uid and gid_number and group_service:
            # Check if there's a group with the same name as the user
            personal_group = await group_service.get(uid)
            if personal_group and personal_group.gidNumber == gid_number:
                # It's a personal group if it has the same name as the user
                # Only delete if empty (no other members)
                if not personal_group.memberUid or personal_group.memberUid == [uid]:
                    personal_group_to_delete = uid
        
        # Check if hostObject is present
        object_classes = entry.get("objectClass", []) if entry else []
        if isinstance(object_classes, str):
            object_classes = [object_classes]
        
        classes_to_remove = ["posixAccount", "shadowAccount"]
        if "hostObject" in object_classes:
            classes_to_remove.append("hostObject")
        
        changes = {
            "objectClass": ("delete", classes_to_remove),
        }
        
        # Delete all managed attributes that have values
        for attr in self.MANAGED_ATTRIBUTES:
            value = entry.get(attr) if entry else None
            if value:
                changes[attr] = ("delete", [])
        
        try:
            await self._ldap.modify(dn, changes)
            logger.info("posix_deactivated", dn=dn)
        except LdapOperationError as e:
            logger.error("posix_deactivation_failed", dn=dn, error=str(e))
            raise PosixValidationError(f"Failed to deactivate POSIX: {e}")
        
        # Delete personal group if applicable
        if personal_group_to_delete and group_service:
            try:
                await group_service.delete(personal_group_to_delete)
                logger.info(
                    "personal_group_deleted_on_deactivate",
                    cn=personal_group_to_delete,
                )
            except Exception as e:
                # Log but don't fail - the main operation succeeded
                logger.warning(
                    "personal_group_deletion_failed",
                    cn=personal_group_to_delete,
                    error=str(e),
                )
    
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
    
    # =========================================================================
    # Account Status and Group Lookup Helpers
    # =========================================================================
    
    def _compute_account_status(
        self,
        shadow_last_change: Optional[int],
        shadow_max: Optional[int],
        shadow_inactive: Optional[int],
        shadow_expire: Optional[int],
    ) -> AccountStatus:
        """
        Compute account status based on shadow attributes.
        
        Implements standard POSIX shadow password expiration logic.
        
        Returns:
            AccountStatus enum value
        """
        today = int(time.time() / 86400)  # Days since epoch
        
        # Check if account has expired
        if shadow_expire is not None and shadow_expire > 0:
            if today >= shadow_expire:
                return AccountStatus.EXPIRED
        
        # Check if password has expired
        if shadow_last_change is not None and shadow_max is not None:
            password_expire_date = shadow_last_change + shadow_max
            
            if today >= password_expire_date:
                # Password expired, check for grace time
                if shadow_inactive is not None and shadow_inactive > 0:
                    grace_end = password_expire_date + shadow_inactive
                    if today < grace_end:
                        return AccountStatus.GRACE_TIME
                    else:
                        return AccountStatus.LOCKED
                return AccountStatus.PASSWORD_EXPIRED
        
        # Check if password change is forced (shadowLastChange = 0)
        if shadow_last_change == 0:
            return AccountStatus.PASSWORD_EXPIRED
        
        return AccountStatus.ACTIVE
    
    async def _get_group_cn_by_gid(self, gid_number: int) -> Optional[str]:
        """Get the CN of a POSIX group by its GID number."""
        try:
            entries = await self._ldap.search(
                search_filter=f"(&(objectClass=posixGroup)(gidNumber={gid_number}))",
                attributes=["cn"],
            )
            if entries:
                return entries[0].get_first("cn") if hasattr(entries[0], 'get_first') else entries[0].get("cn", [""])[0]
            return None
        except LdapOperationError:
            return None
    
    async def _get_user_group_memberships(self, uid: str) -> List[str]:
        """
        Get all POSIX groups that a user belongs to (via memberUid).
        
        Args:
            uid: The user's uid
            
        Returns:
            List of group CNs the user belongs to
        """
        try:
            entries = await self._ldap.search(
                search_filter=f"(&(objectClass=posixGroup)(memberUid={uid}))",
                attributes=["cn"],
            )
            
            groups = []
            for entry in entries:
                cn = entry.get_first("cn") if hasattr(entry, 'get_first') else entry.get("cn", [""])[0]
                if cn:
                    groups.append(cn)
            
            return sorted(groups)
        except LdapOperationError:
            return []


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
    
    NOTE: System trust (hostObject) is implemented but full host validation
    requires the systems plugin. Currently accepts any host string.
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
        # NOTE: Full host validation requires the systems plugin
        if data.trust_mode is not None:
            if data.trust_mode == TrustMode.FULL_ACCESS:
                attributes["host"] = ["*"]
            elif data.trust_mode == TrustMode.BY_HOST and data.host:
                # TODO: Validate hosts against systems plugin when available
                attributes["host"] = data.host
        
        try:
            await self._ldap.add(dn, object_classes, attributes)
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
        # NOTE: Full host validation requires the systems plugin
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
                # TODO: Validate hosts against systems plugin when available
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
            await self._ldap.modify(dn, {"memberUid": ("add", [uid])})
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
            await self._ldap.modify(dn, {"memberUid": ("delete", [uid])})
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
    
    NOTE: System trust (hostObject) is implemented but full host validation
    requires the systems plugin. Currently accepts any host string.
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
    
    def _get_groups_base_dn(self) -> str:
        """Get the base DN for MixedGroups."""
        from heracles_api.config import settings
        return f"{self._groups_ou},{settings.LDAP_BASE_DN}"
    
    def _get_group_dn(self, cn: str) -> str:
        """Get the DN for a MixedGroup by cn."""
        return f"cn={cn},{self._get_groups_base_dn()}"
    
    # =========================================================================
    # CRUD Operations
    # =========================================================================
    
    async def list_all(self) -> List["MixedGroupListItem"]:
        """List all MixedGroups."""
        from .schemas import MixedGroupListItem
        
        try:
            # Search for entries that have both groupOfNames and posixGroupAux
            entries = await self._ldap.search(
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
    
    async def get(self, cn: str) -> Optional["MixedGroupRead"]:
        """Get a MixedGroup by cn."""
        from .schemas import MixedGroupRead
        
        dn = self._get_group_dn(cn)
        
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
            return None
    
    async def create(self, data: "MixedGroupCreate") -> "MixedGroupRead":
        """Create a new MixedGroup."""
        from .schemas import MixedGroupRead, MixedGroupCreate
        
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
        # NOTE: Full host validation requires the systems plugin
        if data.trust_mode is not None:
            if data.trust_mode == TrustMode.FULL_ACCESS:
                attributes["host"] = ["*"]
            elif data.trust_mode == TrustMode.BY_HOST and data.host:
                # TODO: Validate hosts against systems plugin when available
                attributes["host"] = data.host
        
        try:
            await self._ldap.add(dn, object_classes, attributes)
            logger.info("mixed_group_created", cn=data.cn, gid_number=gid_number)
        except LdapOperationError as e:
            logger.error("create_mixed_group_failed", cn=data.cn, error=str(e))
            raise PosixValidationError(f"Failed to create MixedGroup: {e}")
        
        return await self.get(data.cn)
    
    async def update_group(self, cn: str, data: "MixedGroupUpdate") -> "MixedGroupRead":
        """Update a MixedGroup."""
        from .schemas import MixedGroupUpdate
        
        dn = self._get_group_dn(cn)
        
        existing = await self.get(cn)
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
        # NOTE: Full host validation requires the systems plugin
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
                # TODO: Validate hosts against systems plugin when available
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
        
        return await self.get(cn)
    
    async def delete(self, cn: str) -> None:
        """Delete a MixedGroup."""
        dn = self._get_group_dn(cn)
        
        existing = await self.get(cn)
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
    
    async def add_member(self, cn: str, member_dn: str) -> "MixedGroupRead":
        """Add a member (by DN) to a MixedGroup."""
        dn = self._get_group_dn(cn)
        
        group = await self.get(cn)
        if group is None:
            raise PosixValidationError(f"MixedGroup '{cn}' not found")
        
        if member_dn in group.member:
            return group
        
        try:
            await self._ldap.modify(dn, {"member": ("add", [member_dn])})
            logger.info("mixed_group_member_added", cn=cn, member_dn=member_dn)
        except LdapOperationError as e:
            raise PosixValidationError(f"Failed to add member: {e}")
        
        return await self.get(cn)
    
    async def remove_member(self, cn: str, member_dn: str) -> "MixedGroupRead":
        """Remove a member (by DN) from a MixedGroup."""
        dn = self._get_group_dn(cn)
        
        group = await self.get(cn)
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
        
        return await self.get(cn)
    
    async def add_member_uid(self, cn: str, uid: str) -> "MixedGroupRead":
        """Add a memberUid to a MixedGroup."""
        dn = self._get_group_dn(cn)
        
        group = await self.get(cn)
        if group is None:
            raise PosixValidationError(f"MixedGroup '{cn}' not found")
        
        if uid in group.member_uid:
            return group
        
        try:
            await self._ldap.modify(dn, {"memberUid": ("add", [uid])})
            logger.info("mixed_group_member_uid_added", cn=cn, uid=uid)
        except LdapOperationError as e:
            raise PosixValidationError(f"Failed to add memberUid: {e}")
        
        return await self.get(cn)
    
    async def remove_member_uid(self, cn: str, uid: str) -> "MixedGroupRead":
        """Remove a memberUid from a MixedGroup."""
        dn = self._get_group_dn(cn)
        
        group = await self.get(cn)
        if group is None:
            raise PosixValidationError(f"MixedGroup '{cn}' not found")
        
        if uid not in group.member_uid:
            return group
        
        try:
            await self._ldap.modify(dn, {"memberUid": ("delete", [uid])})
            logger.info("mixed_group_member_uid_removed", cn=cn, uid=uid)
        except LdapOperationError as e:
            raise PosixValidationError(f"Failed to remove memberUid: {e}")
        
        return await self.get(cn)
    
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
