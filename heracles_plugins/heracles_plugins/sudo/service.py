"""
Sudo Service
============

Business logic for sudo role management.
Handles LDAP operations for sudoRole entries.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog

from heracles_api.plugins.base import TabService
from heracles_api.services.ldap_service import (
    LdapService,
    LdapEntry,
    LdapOperationError,
    LdapNotFoundError,
)

from .schemas import (
    SudoRoleCreate,
    SudoRoleRead,
    SudoRoleUpdate,
    SudoRoleListResponse,
)

logger = structlog.get_logger(__name__)


class SudoValidationError(Exception):
    """Raised when sudo validation fails."""
    pass


class SudoService(TabService):
    """
    Service for managing sudo roles.
    
    Handles:
    - sudoRole objectClass
    - CRUD operations for sudo rules
    - Time-based validity checking
    """
    
    OBJECT_CLASSES = ["sudoRole"]
    
    MANAGED_ATTRIBUTES = [
        "cn",
        "description",
        "sudoUser",
        "sudoHost",
        "sudoCommand",
        "sudoRunAs",  # deprecated but still read
        "sudoRunAsUser",
        "sudoRunAsGroup",
        "sudoOption",
        "sudoOrder",
        "sudoNotBefore",
        "sudoNotAfter",
    ]
    
    def __init__(self, ldap_service: LdapService, config: Dict[str, Any]):
        super().__init__(ldap_service, config)
        
        # Configuration
        self._sudoers_rdn = config.get("sudoers_rdn", "ou=sudoers")
        self._base_dn = config.get("base_dn", ldap_service.base_dn)
        self._sudoers_dn = f"{self._sudoers_rdn},{self._base_dn}"
    
    # ========================================================================
    # CRUD Operations
    # ========================================================================
    
    async def list_roles(
        self,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> SudoRoleListResponse:
        """List all sudo roles with optional filtering."""
        
        # Build search filter
        if search:
            escaped_search = self._ldap._escape_filter(search)
            search_filter = f"(&(objectClass=sudoRole)(|(cn=*{escaped_search}*)(description=*{escaped_search}*)(sudoUser=*{escaped_search}*)))"
        else:
            search_filter = "(objectClass=sudoRole)"
        
        try:
            entries = await self._ldap.search(
                search_base=self._sudoers_dn,
                search_filter=search_filter,
                attributes=self.MANAGED_ATTRIBUTES,
            )
            
            # Convert to schema objects
            roles = [self._entry_to_read(entry) for entry in entries]
            
            # Sort by order, then by cn
            roles.sort(key=lambda r: (r.sudo_order or 0, r.cn))
            
            # Pagination
            total = len(roles)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_roles = roles[start_idx:end_idx]
            
            return SudoRoleListResponse(
                roles=paginated_roles,
                total=total,
                page=page,
                page_size=page_size,
                has_more=end_idx < total,
            )
            
        except LdapOperationError as e:
            logger.error("sudo_list_failed", error=str(e))
            raise
    
    async def get_role(self, cn: str) -> Optional[SudoRoleRead]:
        """Get a single sudo role by CN."""
        dn = f"cn={cn},{self._sudoers_dn}"
        
        try:
            entry = await self._ldap.get_by_dn(dn, attributes=self.MANAGED_ATTRIBUTES)
            if entry is None:
                return None
            return self._entry_to_read(entry)
        except LdapOperationError:
            return None
    
    async def create_role(self, data: SudoRoleCreate) -> SudoRoleRead:
        """Create a new sudo role."""
        
        # Check if role already exists
        existing = await self.get_role(data.cn)
        if existing:
            raise SudoValidationError(f"Sudo role '{data.cn}' already exists")
        
        # Ensure sudoers OU exists
        await self._ensure_sudoers_ou()
        
        # Build DN
        dn = f"cn={data.cn},{self._sudoers_dn}"
        
        # Build attributes
        attributes = self._build_attributes(data)
        
        try:
            await self._ldap.add(
                dn=dn,
                object_classes=self.OBJECT_CLASSES,
                attributes=attributes,
            )
            
            logger.info("sudo_role_created", cn=data.cn, dn=dn)
            
            # Read back and return
            return await self.get_role(data.cn)
            
        except LdapOperationError as e:
            logger.error("sudo_role_create_failed", cn=data.cn, error=str(e))
            raise SudoValidationError(f"Failed to create sudo role: {e}")
    
    async def update_role(self, cn: str, data: SudoRoleUpdate) -> SudoRoleRead:
        """Update an existing sudo role."""
        
        # Check if it's the defaults entry
        if cn.lower() == "defaults":
            # Only allow updating options for defaults
            if any([
                data.sudo_user is not None,
                data.sudo_host is not None,
                data.sudo_command is not None,
                data.sudo_run_as_user is not None,
                data.sudo_run_as_group is not None,
            ]):
                raise SudoValidationError(
                    "Cannot modify users/hosts/commands on the defaults entry"
                )
        
        dn = f"cn={cn},{self._sudoers_dn}"
        
        # Check exists
        existing = await self.get_role(cn)
        if not existing:
            raise LdapNotFoundError(f"Sudo role '{cn}' not found")
        
        # Build changes
        changes = {}
        
        if data.description is not None:
            if data.description:
                changes["description"] = ("replace", [data.description])
            else:
                changes["description"] = ("delete", [])
        
        if data.sudo_user is not None:
            if data.sudo_user:
                changes["sudoUser"] = ("replace", data.sudo_user)
            else:
                changes["sudoUser"] = ("delete", [])
        
        if data.sudo_host is not None:
            if data.sudo_host:
                changes["sudoHost"] = ("replace", data.sudo_host)
            else:
                changes["sudoHost"] = ("delete", [])
        
        if data.sudo_command is not None:
            if data.sudo_command:
                changes["sudoCommand"] = ("replace", data.sudo_command)
            else:
                changes["sudoCommand"] = ("delete", [])
        
        if data.sudo_run_as_user is not None:
            if data.sudo_run_as_user:
                changes["sudoRunAsUser"] = ("replace", data.sudo_run_as_user)
            else:
                changes["sudoRunAsUser"] = ("delete", [])
        
        if data.sudo_run_as_group is not None:
            if data.sudo_run_as_group:
                changes["sudoRunAsGroup"] = ("replace", data.sudo_run_as_group)
            else:
                changes["sudoRunAsGroup"] = ("delete", [])
        
        if data.sudo_option is not None:
            if data.sudo_option:
                changes["sudoOption"] = ("replace", data.sudo_option)
            else:
                changes["sudoOption"] = ("delete", [])
        
        if data.sudo_order is not None:
            changes["sudoOrder"] = ("replace", [str(data.sudo_order)])
        
        if data.sudo_not_before is not None:
            changes["sudoNotBefore"] = ("replace", [self._datetime_to_generalized(data.sudo_not_before)])
        elif data.sudo_not_before == "":
            changes["sudoNotBefore"] = ("delete", [])
        
        if data.sudo_not_after is not None:
            changes["sudoNotAfter"] = ("replace", [self._datetime_to_generalized(data.sudo_not_after)])
        elif data.sudo_not_after == "":
            changes["sudoNotAfter"] = ("delete", [])
        
        if changes:
            try:
                await self._ldap.modify(dn, changes)
                logger.info("sudo_role_updated", cn=cn)
            except LdapOperationError as e:
                logger.error("sudo_role_update_failed", cn=cn, error=str(e))
                raise SudoValidationError(f"Failed to update sudo role: {e}")
        
        return await self.get_role(cn)
    
    async def delete_role(self, cn: str) -> bool:
        """Delete a sudo role."""
        
        # Don't allow deleting defaults
        if cn.lower() == "defaults":
            raise SudoValidationError("Cannot delete the defaults entry")
        
        dn = f"cn={cn},{self._sudoers_dn}"
        
        # Check exists
        existing = await self.get_role(cn)
        if not existing:
            raise LdapNotFoundError(f"Sudo role '{cn}' not found")
        
        try:
            await self._ldap.delete(dn)
            logger.info("sudo_role_deleted", cn=cn)
            return True
        except LdapOperationError as e:
            logger.error("sudo_role_delete_failed", cn=cn, error=str(e))
            raise SudoValidationError(f"Failed to delete sudo role: {e}")
    
    # ========================================================================
    # Defaults Entry
    # ========================================================================
    
    async def get_defaults(self) -> Optional[SudoRoleRead]:
        """Get the sudo defaults entry."""
        return await self.get_role("defaults")
    
    async def create_defaults(self, options: List[str] = None) -> SudoRoleRead:
        """Create the sudo defaults entry if it doesn't exist."""
        existing = await self.get_defaults()
        if existing:
            return existing
        
        data = SudoRoleCreate(
            cn="defaults",
            description="Default sudo options",
            sudoOption=options or [],
        )
        return await self.create_role(data)
    
    # ========================================================================
    # User-centric queries
    # ========================================================================
    
    async def get_roles_for_user(self, uid: str, groups: List[str] = None) -> List[SudoRoleRead]:
        """Get all sudo roles that apply to a specific user."""
        
        # Build filter for user, their groups, and ALL
        filters = [f"(sudoUser={self._ldap._escape_filter(uid)})"]
        filters.append("(sudoUser=ALL)")
        
        if groups:
            for group in groups:
                filters.append(f"(sudoUser=%{self._ldap._escape_filter(group)})")
        
        search_filter = f"(&(objectClass=sudoRole)(|{''.join(filters)}))"
        
        try:
            entries = await self._ldap.search(
                search_base=self._sudoers_dn,
                search_filter=search_filter,
                attributes=self.MANAGED_ATTRIBUTES,
            )
            
            roles = [self._entry_to_read(entry) for entry in entries]
            
            # Filter out invalid (time-constrained) roles
            now = datetime.now(timezone.utc)
            valid_roles = [r for r in roles if self._is_role_valid(r, now)]
            
            # Sort by order
            valid_roles.sort(key=lambda r: (r.sudo_order or 0, r.cn))
            
            return valid_roles
            
        except LdapOperationError as e:
            logger.error("sudo_get_user_roles_failed", uid=uid, error=str(e))
            return []
    
    async def get_roles_for_host(self, hostname: str) -> List[SudoRoleRead]:
        """Get all sudo roles that apply to a specific host."""
        
        search_filter = f"(&(objectClass=sudoRole)(|(sudoHost={self._ldap._escape_filter(hostname)})(sudoHost=ALL)))"
        
        try:
            entries = await self._ldap.search(
                search_base=self._sudoers_dn,
                search_filter=search_filter,
                attributes=self.MANAGED_ATTRIBUTES,
            )
            
            roles = [self._entry_to_read(entry) for entry in entries]
            roles.sort(key=lambda r: (r.sudo_order or 0, r.cn))
            
            return roles
            
        except LdapOperationError as e:
            logger.error("sudo_get_host_roles_failed", hostname=hostname, error=str(e))
            return []
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    async def _ensure_sudoers_ou(self) -> None:
        """Ensure the sudoers OU exists."""
        try:
            entry = await self._ldap.get_by_dn(self._sudoers_dn)
            if entry is None:
                await self._ldap.add(
                    dn=self._sudoers_dn,
                    object_classes=["organizationalUnit"],
                    attributes={"ou": "sudoers"},
                )
                logger.info("sudoers_ou_created", dn=self._sudoers_dn)
        except LdapOperationError:
            # Try to create it
            try:
                await self._ldap.add(
                    dn=self._sudoers_dn,
                    object_classes=["organizationalUnit"],
                    attributes={"ou": "sudoers"},
                )
                logger.info("sudoers_ou_created", dn=self._sudoers_dn)
            except LdapOperationError as e:
                logger.debug("sudoers_ou_exists_or_error", error=str(e))
    
    def _build_attributes(self, data: SudoRoleCreate) -> Dict[str, Any]:
        """Build LDAP attributes from create schema."""
        attrs = {"cn": data.cn}
        
        if data.description:
            attrs["description"] = data.description
        
        if data.sudo_user:
            attrs["sudoUser"] = data.sudo_user
        
        if data.sudo_host:
            attrs["sudoHost"] = data.sudo_host
        
        if data.sudo_command:
            attrs["sudoCommand"] = data.sudo_command
        
        if data.sudo_run_as_user:
            attrs["sudoRunAsUser"] = data.sudo_run_as_user
        
        if data.sudo_run_as_group:
            attrs["sudoRunAsGroup"] = data.sudo_run_as_group
        
        if data.sudo_option:
            attrs["sudoOption"] = data.sudo_option
        
        if data.sudo_order is not None:
            attrs["sudoOrder"] = str(data.sudo_order)
        
        if data.sudo_not_before:
            attrs["sudoNotBefore"] = self._datetime_to_generalized(data.sudo_not_before)
        
        if data.sudo_not_after:
            attrs["sudoNotAfter"] = self._datetime_to_generalized(data.sudo_not_after)
        
        return attrs
    
    def _entry_to_read(self, entry: LdapEntry) -> SudoRoleRead:
        """Convert LDAP entry to read schema."""
        cn = self._get_first(entry, "cn", "")
        
        # Parse time constraints
        not_before = self._parse_generalized_time(self._get_first(entry, "sudoNotBefore"))
        not_after = self._parse_generalized_time(self._get_first(entry, "sudoNotAfter"))
        
        # Check if currently valid
        is_valid = self._is_time_valid(not_before, not_after)
        
        return SudoRoleRead(
            dn=entry.dn,
            cn=cn,
            description=self._get_first(entry, "description"),
            sudoUser=self._get_list(entry, "sudoUser"),
            sudoHost=self._get_list(entry, "sudoHost") or ["ALL"],
            sudoCommand=self._get_list(entry, "sudoCommand"),
            sudoRunAsUser=self._get_list(entry, "sudoRunAsUser") or ["ALL"],
            sudoRunAsGroup=self._get_list(entry, "sudoRunAsGroup"),
            sudoOption=self._get_list(entry, "sudoOption"),
            sudoOrder=self._get_int(entry, "sudoOrder", 0),
            sudoNotBefore=not_before,
            sudoNotAfter=not_after,
            isDefault=cn.lower() == "defaults",
            isValid=is_valid,
        )
    
    def _get_first(self, entry: LdapEntry, attr: str, default: Any = None) -> Any:
        """Get first value of an attribute."""
        val = entry.get(attr)
        if val is None:
            return default
        if isinstance(val, list):
            return val[0] if val else default
        return val
    
    def _get_list(self, entry: LdapEntry, attr: str) -> List[str]:
        """Get attribute as list."""
        val = entry.get(attr)
        if val is None:
            return []
        if isinstance(val, str):
            return [val]
        return list(val)
    
    def _get_int(self, entry: LdapEntry, attr: str, default: int = 0) -> int:
        """Get attribute as integer."""
        val = self._get_first(entry, attr)
        if val is None:
            return default
        try:
            return int(val)
        except (ValueError, TypeError):
            return default
    
    def _parse_generalized_time(self, value: Optional[str]) -> Optional[datetime]:
        """Parse LDAP generalized time to datetime."""
        if not value:
            return None
        try:
            # Format: YYYYMMDDHHMMSSZ or YYYYMMDDHHMMSS.ffffffZ
            value = value.rstrip("Z")
            if "." in value:
                value = value.split(".")[0]
            return datetime.strptime(value, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    
    def _datetime_to_generalized(self, dt: datetime) -> str:
        """Convert datetime to LDAP generalized time."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.strftime("%Y%m%d%H%M%SZ")
    
    def _is_time_valid(self, not_before: Optional[datetime], not_after: Optional[datetime]) -> bool:
        """Check if current time is within validity period."""
        now = datetime.now(timezone.utc)
        
        if not_before and now < not_before:
            return False
        if not_after and now > not_after:
            return False
        
        return True
    
    def _is_role_valid(self, role: SudoRoleRead, now: datetime = None) -> bool:
        """Check if a role is currently valid based on time constraints."""
        if now is None:
            now = datetime.now(timezone.utc)
        
        if role.sudo_not_before and now < role.sudo_not_before:
            return False
        if role.sudo_not_after and now > role.sudo_not_after:
            return False
        
        return True
    
    # ========================================================================
    # TabService Interface (for user tab, if needed)
    # ========================================================================
    
    async def is_active(self, dn: str) -> bool:
        """Not used for sudo - it's a standalone object type."""
        return False
    
    async def read(self, dn: str) -> Optional[SudoRoleRead]:
        """Read sudo role by DN."""
        try:
            entry = await self._ldap.get_by_dn(dn, attributes=self.MANAGED_ATTRIBUTES)
            if entry is None:
                return None
            return self._entry_to_read(entry)
        except LdapOperationError:
            return None
    
    async def activate(self, dn: str, data: SudoRoleCreate) -> SudoRoleRead:
        """Not applicable for sudo roles."""
        raise NotImplementedError("Use create_role() instead")
    
    async def deactivate(self, dn: str) -> bool:
        """Not applicable for sudo roles."""
        raise NotImplementedError("Use delete_role() instead")
    
    async def update(self, dn: str, data: SudoRoleUpdate) -> SudoRoleRead:
        """Update sudo role by DN."""
        # Extract CN from DN
        cn = dn.split(",")[0].split("=")[1]
        return await self.update_role(cn, data)
