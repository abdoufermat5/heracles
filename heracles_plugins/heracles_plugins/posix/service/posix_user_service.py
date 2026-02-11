"""
POSIX User Service
==================

Business logic for POSIX user account management.
Handles UID allocation, posixAccount/shadowAccount attributes, and system trust.
"""

import time
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import structlog

from heracles_api.plugins.base import TabService
from heracles_api.plugins.base import PluginFieldDefinition, PluginTemplateField
from heracles_api.services.ldap_service import LdapService, LdapOperationError

from .base import PosixValidationError, get_int, get_int_optional
from ..schemas import (
    PosixAccountCreate,
    PosixAccountRead,
    PosixAccountUpdate,
    PrimaryGroupMode,
    TrustMode,
    AccountStatus,
)

if TYPE_CHECKING:
    from .posix_group_service import PosixGroupService

logger = structlog.get_logger(__name__)


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

    # ------------------------------------------------------------------
    # Import / Export / Template extension points
    # ------------------------------------------------------------------

    @classmethod
    def get_import_fields(cls) -> list[PluginFieldDefinition]:
        return [
            PluginFieldDefinition(name="uidNumber", label="UID Number", description="POSIX user ID"),
            PluginFieldDefinition(name="gidNumber", label="GID Number", required=True, description="Primary group ID"),
            PluginFieldDefinition(name="homeDirectory", label="Home Directory", description="Auto-generated if omitted"),
            PluginFieldDefinition(name="loginShell", label="Login Shell", description="Default: /bin/bash"),
            PluginFieldDefinition(name="gecos", label="GECOS", description="Real name / comment"),
        ]

    @classmethod
    def get_export_fields(cls) -> list[PluginFieldDefinition]:
        return [
            PluginFieldDefinition(name="uidNumber", label="UID Number"),
            PluginFieldDefinition(name="gidNumber", label="GID Number"),
            PluginFieldDefinition(name="homeDirectory", label="Home Directory"),
            PluginFieldDefinition(name="loginShell", label="Login Shell"),
            PluginFieldDefinition(name="gecos", label="GECOS"),
            PluginFieldDefinition(name="shadowLastChange", label="Shadow Last Change"),
            PluginFieldDefinition(name="shadowMin", label="Shadow Min Days"),
            PluginFieldDefinition(name="shadowMax", label="Shadow Max Days"),
            PluginFieldDefinition(name="shadowWarning", label="Shadow Warning"),
            PluginFieldDefinition(name="shadowInactive", label="Shadow Inactive"),
            PluginFieldDefinition(name="shadowExpire", label="Shadow Expire"),
        ]

    @classmethod
    def get_template_fields(cls) -> list[PluginTemplateField]:
        return [
            PluginTemplateField(
                key="loginShell", label="Login Shell",
                field_type="select", default_value="/bin/bash",
                options=cls.DEFAULT_SHELLS,
            ),
            PluginTemplateField(
                key="gidNumber", label="Primary Group GID",
                field_type="integer",
                description="Leave empty for auto-allocation",
            ),
            PluginTemplateField(
                key="homeDirectory", label="Home Directory Pattern",
                field_type="string", default_value="/home/{{uid}}",
                description="Supports {{uid}} placeholder",
            ),
            PluginTemplateField(
                key="gecos", label="GECOS",
                field_type="string",
                description="Supports {{cn}} placeholder",
            ),
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

    def get_base_dn(self) -> str:
        """Get the LDAP base DN for scope-based ACL checks."""
        return self._ldap.base_dn

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
        data: Any = None,
        uid: Optional[str] = None,
        group_service: Optional["PosixGroupService"] = None,
        base_dn: Optional[str] = None,
    ) -> PosixAccountRead:
        """
        Activate POSIX on a user.
        
        Args:
            dn: User's DN
            data: POSIX account data (PosixAccountCreate, dict, or None for defaults)
            uid: User's uid (for home directory generation and personal group).
                 Auto-extracted from DN if not provided.
            group_service: PosixGroupService instance (for auto-creating personal groups).
                           Auto-resolved from plugin registry if not provided.
            base_dn: Base DN for creating personal groups in department context.
                     Auto-extracted from user DN if not provided.
        """
        import re

        # Normalise data to PosixAccountCreate
        if data is None:
            data = PosixAccountCreate()
        elif isinstance(data, dict):
            # Resolve {{uid}} placeholders in template values
            if uid is None:
                m = re.search(r"uid=([^,]+)", dn)
                if m:
                    uid = m.group(1)
            if uid:
                data = {
                    k: (v.replace("{{uid}}", uid) if isinstance(v, str) else v)
                    for k, v in data.items()
                }
            # Default to create_personal when no gidNumber or mode specified
            if "primaryGroupMode" not in data and "gidNumber" not in data:
                data["primaryGroupMode"] = PrimaryGroupMode.CREATE_PERSONAL.value
            data = PosixAccountCreate(**data)
        elif not isinstance(data, PosixAccountCreate):
            raise PosixValidationError("Invalid activation data type")

        # Auto-resolve uid from DN when not supplied
        if uid is None:
            match = re.search(r"uid=([^,]+)", dn)
            if match:
                uid = match.group(1)

        # Auto-resolve group_service from plugin registry when not supplied
        if group_service is None:
            try:
                from heracles_api.plugins.registry import plugin_registry
                group_service = plugin_registry.get_service("posix-group")
            except Exception:
                pass  # Will fail later if CREATE_PERSONAL mode is used

        # Auto-resolve base_dn from user DN when not supplied
        if base_dn is None:
            dn_lower = dn.lower()
            ou_people_idx = dn_lower.find(",ou=people,")
            if ou_people_idx != -1:
                base_dn = dn[ou_people_idx + len(",ou=people,"):]

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
                gid_number = existing_group.gid_number
                logger.info(
                    "using_existing_personal_group",
                    cn=uid,
                    gid_number=gid_number,
                )
            else:
                # Create new personal group
                from ..schemas import PosixGroupFullCreate
                
                # Allocate GID for the personal group
                personal_gid = data.gid_number if data.force_gid and data.gid_number else None
                
                personal_group_data = PosixGroupFullCreate(
                    cn=uid,
                    gidNumber=personal_gid,
                    description=f"Personal group for {uid}",
                )
                
                created_group = await group_service.create(personal_group_data, base_dn=base_dn)
                gid_number = created_group.gid_number
                created_personal_group = True
                
                logger.info(
                    "personal_group_created",
                    cn=uid,
                    gid_number=gid_number,
                    base_dn=base_dn,
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
            if personal_group and personal_group.gid_number == gid_number:
                # It's a personal group if it has the same name as the user
                # Only delete if empty (no other members)
                if not personal_group.member_uid or personal_group.member_uid == [uid]:
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
        return get_int(entry, attr)
    
    def _get_int_optional(self, entry: Any, attr: str) -> Optional[int]:
        """Get optional integer attribute."""
        return get_int_optional(entry, attr)
    
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
