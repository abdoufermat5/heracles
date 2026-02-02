"""
Systems Service
===============

Business logic for system management.
Handles LDAP operations for all system types (servers, workstations, etc.).
"""

from typing import Any, Dict, List, Optional, Tuple

import structlog

from heracles_api.plugins.base import TabService
from heracles_api.services.ldap_service import (
    LdapService,
    LdapEntry,
    LdapOperationError,
    LdapNotFoundError,
)

from ..schemas import (
    SystemType,
    SystemCreate,
    SystemRead,
    SystemUpdate,
    SystemListItem,
    SystemListResponse,
    LockMode,
    HostValidationResponse,
)

from .constants import (
    TYPE_OBJECT_CLASSES,
    COMMON_ATTRIBUTES,
    PRINTER_ATTRIBUTES,
    PHONE_ATTRIBUTES,
    MOBILE_ATTRIBUTES,
    COMPONENT_ATTRIBUTES,
    get_all_attributes,
)
from .utils import (
    get_first_value,
    get_list_value,
    detect_system_type,
    parse_lock_mode,
    get_entry_dn,
)

logger = structlog.get_logger(__name__)


class SystemValidationError(Exception):
    """Raised when system validation fails."""
    pass


class SystemService(TabService):
    """
    Service for managing systems in LDAP.

    Handles all system types:
    - Server (hrcServer)
    - Workstation (hrcWorkstation)
    - Terminal (hrcTerminal)
    - Printer (hrcPrinter)
    - Component (device)
    - Phone (hrcPhone)
    - Mobile Phone (hrcMobilePhone)

    All types support ipHost and ieee802Device for IP/MAC addressing.
    """

    def __init__(self, ldap_service: LdapService, config: Dict[str, Any]):
        super().__init__(ldap_service, config)
        
        # Configuration
        self._systems_rdn = config.get("systems_rdn", "ou=systems")
        self._base_dn = config.get("base_dn", ldap_service.base_dn)
        self._systems_dn = f"{self._systems_rdn},{self._base_dn}"
    
    # ========================================================================
    # Config-Based Validation
    # ========================================================================
    
    async def _get_validation_config(self) -> Dict[str, Any]:
        """
        Get systems validation config with hot-reload support.
        
        Reads from database config with fallback to init-time config.
        """
        try:
            from heracles_api.services.config import get_plugin_config_value
            
            validate_ip = await get_plugin_config_value(
                "systems",
                "validate_ip_addresses",
                self._config.get("validate_ip_addresses", True)
            )
            validate_mac = await get_plugin_config_value(
                "systems",
                "validate_mac_addresses",
                self._config.get("validate_mac_addresses", True)
            )
            require_unique_hostname = await get_plugin_config_value(
                "systems",
                "require_unique_hostname",
                self._config.get("require_unique_hostname", True)
            )
            require_unique_ip = await get_plugin_config_value(
                "systems",
                "require_unique_ip",
                self._config.get("require_unique_ip", False)
            )
            require_unique_mac = await get_plugin_config_value(
                "systems",
                "require_unique_mac",
                self._config.get("require_unique_mac", True)
            )
            
            return {
                "validate_ip_addresses": validate_ip,
                "validate_mac_addresses": validate_mac,
                "require_unique_hostname": require_unique_hostname,
                "require_unique_ip": require_unique_ip,
                "require_unique_mac": require_unique_mac,
            }
            
        except Exception as e:
            logger.warning("systems_config_load_error", error=str(e))
            return {
                "validate_ip_addresses": self._config.get("validate_ip_addresses", True),
                "validate_mac_addresses": self._config.get("validate_mac_addresses", True),
                "require_unique_hostname": self._config.get("require_unique_hostname", True),
                "require_unique_ip": self._config.get("require_unique_ip", False),
                "require_unique_mac": self._config.get("require_unique_mac", True),
            }
    
    async def _check_hostname_uniqueness(
        self, 
        hostname: str, 
        exclude_dn: Optional[str] = None,
        base_dn: Optional[str] = None
    ) -> Optional[str]:
        """
        Check if hostname is unique across all system types.
        
        Returns error message if duplicate found, None if unique.
        """
        config = await self._get_validation_config()
        
        if not config.get("require_unique_hostname", True):
            return None
        
        # Search across all system types
        search_base = self._get_systems_container(base_dn)
        search_filter = f"(cn={self._ldap._escape_filter(hostname)})"
        
        try:
            entries = await self._ldap.search(
                search_base=search_base,
                search_filter=search_filter,
                attributes=["cn"],
                size_limit=2,  # Only need to find one duplicate
            )
            
            for entry in entries:
                if exclude_dn and entry.dn == exclude_dn:
                    continue
                return f"Hostname '{hostname}' is already in use"
            
            return None
            
        except Exception as e:
            logger.warning("hostname_uniqueness_check_error", hostname=hostname, error=str(e))
            return None
    
    async def _check_ip_uniqueness(
        self, 
        ip_addresses: List[str],
        exclude_dn: Optional[str] = None,
        base_dn: Optional[str] = None
    ) -> List[str]:
        """
        Check if IP addresses are unique.
        
        Returns list of error messages for duplicates.
        """
        config = await self._get_validation_config()
        
        if not config.get("require_unique_ip", False):
            return []
        
        errors = []
        search_base = self._get_systems_container(base_dn)
        
        for ip in ip_addresses:
            search_filter = f"(ipHostNumber={self._ldap._escape_filter(ip)})"
            
            try:
                entries = await self._ldap.search(
                    search_base=search_base,
                    search_filter=search_filter,
                    attributes=["cn", "ipHostNumber"],
                    size_limit=2,
                )
                
                for entry in entries:
                    if exclude_dn and entry.dn == exclude_dn:
                        continue
                    errors.append(f"IP address '{ip}' is already assigned to '{entry.get_first('cn')}'")
                    break
                    
            except Exception as e:
                logger.warning("ip_uniqueness_check_error", ip=ip, error=str(e))
        
        return errors
    
    async def _check_mac_uniqueness(
        self, 
        mac_addresses: List[str],
        exclude_dn: Optional[str] = None,
        base_dn: Optional[str] = None
    ) -> List[str]:
        """
        Check if MAC addresses are unique.
        
        Returns list of error messages for duplicates.
        """
        config = await self._get_validation_config()
        
        if not config.get("require_unique_mac", True):
            return []
        
        errors = []
        search_base = self._get_systems_container(base_dn)
        
        for mac in mac_addresses:
            # Normalize MAC to uppercase for search
            mac_upper = mac.upper()
            search_filter = f"(macAddress={self._ldap._escape_filter(mac_upper)})"
            
            try:
                entries = await self._ldap.search(
                    search_base=search_base,
                    search_filter=search_filter,
                    attributes=["cn", "macAddress"],
                    size_limit=2,
                )
                
                for entry in entries:
                    if exclude_dn and entry.dn == exclude_dn:
                        continue
                    errors.append(f"MAC address '{mac}' is already assigned to '{entry.get_first('cn')}'")
                    break
                    
            except Exception as e:
                logger.warning("mac_uniqueness_check_error", mac=mac, error=str(e))
        
        return errors
    
    async def validate_system(
        self, 
        data: SystemCreate,
        exclude_dn: Optional[str] = None,
        base_dn: Optional[str] = None
    ) -> List[str]:
        """
        Validate a system against config-based rules.
        
        Checks:
        - Hostname uniqueness (if enabled)
        - IP address uniqueness (if enabled)
        - MAC address uniqueness (if enabled)
        
        Returns:
            List of validation errors (empty if all valid)
        """
        errors = []
        
        # Check hostname uniqueness
        hostname_error = await self._check_hostname_uniqueness(data.cn, exclude_dn, base_dn)
        if hostname_error:
            errors.append(hostname_error)
        
        # Check IP uniqueness
        if data.ip_addresses:
            ip_errors = await self._check_ip_uniqueness(data.ip_addresses, exclude_dn, base_dn)
            errors.extend(ip_errors)
        
        # Check MAC uniqueness
        if data.mac_addresses:
            mac_errors = await self._check_mac_uniqueness(data.mac_addresses, exclude_dn, base_dn)
            errors.extend(mac_errors)
        
        return errors

    def _get_systems_container(self, base_dn: Optional[str] = None) -> str:
        """Get the systems container DN for the given context.
        
        If base_dn is provided (department context), returns ou=systems,{base_dn}.
        Otherwise returns the default ou=systems,{root_base_dn}.
        """
        if base_dn:
            return f"{self._systems_rdn},{base_dn}"
        return self._systems_dn
    
    def _get_type_ou(self, system_type: SystemType, base_dn: Optional[str] = None) -> str:
        """Get the OU DN for a system type within the given context."""
        rdn = SystemType.get_rdn(system_type)
        container = self._get_systems_container(base_dn)
        return f"{rdn},{container}"
    
    def _get_system_dn(self, cn: str, system_type: SystemType, base_dn: Optional[str] = None) -> str:
        """Get the DN for a system within the given context."""
        ou_dn = self._get_type_ou(system_type, base_dn)
        return f"cn={cn},{ou_dn}"
    
    # ========================================================================
    # OU Management
    # ========================================================================
    
    async def _ensure_systems_ou(self) -> None:
        """Ensure the systems OU exists."""
        try:
            exists = await self._ldap.get_by_dn(
                self._systems_dn, 
                attributes=["ou"]
            )
            if exists is None:
                await self._ldap.add(
                    dn=self._systems_dn,
                    object_classes=["organizationalUnit"],
                    attributes={"ou": ["systems"]},
                )
                logger.info("systems_ou_created", dn=self._systems_dn)
        except LdapOperationError as e:
            logger.warning("systems_ou_check_failed", error=str(e))
    
    async def _ensure_type_ou(self, system_type: SystemType) -> None:
        """Ensure the OU for a specific system type exists."""
        await self._ensure_systems_ou()
        
        ou_dn = self._get_type_ou(system_type)
        ou_name = SystemType.get_rdn(system_type).replace("ou=", "")
        
        try:
            exists = await self._ldap.get_by_dn(ou_dn, attributes=["ou"])
            if exists is None:
                await self._ldap.add(
                    dn=ou_dn,
                    object_classes=["organizationalUnit"],
                    attributes={"ou": [ou_name]},
                )
                logger.info("system_type_ou_created", dn=ou_dn, type=system_type.value)
        except LdapOperationError as e:
            logger.warning("system_type_ou_check_failed", type=system_type.value, error=str(e))
    
    # ========================================================================
    # CRUD Operations
    # ========================================================================
    
    async def list_systems(
        self,
        system_type: Optional[SystemType] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        base_dn: Optional[str] = None,
    ) -> SystemListResponse:
        """
        List systems with optional filtering.
        
        Args:
            system_type: Filter by system type (None = all types)
            search: Search in cn, description, ipHostNumber
            page: Page number (1-indexed)
            page_size: Items per page
            
        Returns:
            SystemListResponse with paginated results
        """
        # Build search filter
        filters = []
        
        if system_type:
            obj_class = SystemType.get_object_class(system_type)
            filters.append(f"(objectClass={obj_class})")
        else:
            # Match any of our system types
            type_filters = [
                f"(objectClass={SystemType.get_object_class(t)})"
                for t in SystemType
            ]
            filters.append(f"(|{''.join(type_filters)})")
        
        if search:
            escaped_search = self._ldap._escape_filter(search)
            search_filter = f"(|(cn=*{escaped_search}*)(description=*{escaped_search}*)(ipHostNumber=*{escaped_search}*))"
            filters.append(search_filter)
        
        combined_filter = f"(&{''.join(filters)})" if len(filters) > 1 else filters[0]
        
        try:
            # Get the systems container for the given context
            # Search within specific type OU if type provided
            if system_type:
                search_base = self._get_type_ou(system_type, base_dn)
            else:
                search_base = self._get_systems_container(base_dn)
            
            entries = await self._ldap.search(
                search_base=search_base,
                search_filter=combined_filter,
                attributes=get_all_attributes(),
            )
            
            # Convert to list items
            systems = [self._entry_to_list_item(entry) for entry in entries]
            
            # Sort by cn
            systems.sort(key=lambda s: s.cn)
            
            # Pagination
            total = len(systems)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_systems = systems[start_idx:end_idx]
            
            return SystemListResponse(
                systems=paginated_systems,
                total=total,
                page=page,
                page_size=page_size,
                has_more=end_idx < total,
            )
            
        except LdapOperationError as e:
            logger.error("systems_list_failed", error=str(e))
            raise
    
    async def get_system(
        self, 
        cn: str, 
        system_type: SystemType,
        base_dn: Optional[str] = None
    ) -> Optional[SystemRead]:
        """
        Get a single system by CN and type.
        
        If base_dn is provided, looks within that context's systems container.
        Otherwise uses the default systems container.
        """
        dn = self._get_system_dn(cn, system_type, base_dn)
        
        try:
            entry = await self._ldap.get_by_dn(
                dn, 
                attributes=get_all_attributes()
            )
            if entry is None:
                return None
            return self._entry_to_read(entry, system_type)
        except LdapOperationError:
            return None
    
    async def get_system_by_dn(self, dn: str) -> Optional[SystemRead]:
        """Get a system by its DN (auto-detect type)."""
        try:
            entry = await self._ldap.get_by_dn(
                dn, 
                attributes=get_all_attributes()
            )
            if entry is None:
                return None
            
            # Detect type from objectClass
            system_type = detect_system_type(entry)
            if system_type is None:
                return None
            
            return self._entry_to_read(entry, system_type)
        except LdapOperationError:
            return None
    
    async def create_system(
        self, 
        data: SystemCreate,
        base_dn: Optional[str] = None
    ) -> SystemRead:
        """
        Create a new system.
        
        If base_dn is provided, creates in that department's systems container.
        Otherwise creates it in the default systems container.
        """
        
        # Check if system already exists
        existing = await self.get_system(data.cn, data.system_type, base_dn=base_dn)
        if existing:
            raise SystemValidationError(
                f"System '{data.cn}' of type '{data.system_type.value}' already exists"
            )
        
        # Validate against config-based rules (uniqueness checks)
        validation_errors = await self.validate_system(data, base_dn=base_dn)
        if validation_errors:
            raise SystemValidationError("; ".join(validation_errors))
        
        # Get the DN for the new system
        dn = self._get_system_dn(data.cn, data.system_type, base_dn)
        
        # Ensure OU exists (only for root context)
        if not base_dn:
            await self._ensure_type_ou(data.system_type)
        
        # Get object classes for this type
        object_classes = TYPE_OBJECT_CLASSES[data.system_type].copy()
        
        # Build attributes
        attributes = self._build_create_attributes(data)
        
        try:
            await self._ldap.add(
                dn=dn,
                object_classes=object_classes,
                attributes=attributes,
            )
            
            logger.info(
                "system_created", 
                cn=data.cn, 
                type=data.system_type.value,
                dn=dn,
                context="custom" if base_dn else "default"
            )
            
            # Read back and return
            # Pass base_dn to finding it again
            return await self.get_system(data.cn, data.system_type, base_dn=base_dn)
            
        except LdapOperationError as e:
            logger.error(
                "system_create_failed", 
                cn=data.cn, 
                type=data.system_type.value,
                error=str(e)
            )
            raise SystemValidationError(f"Failed to create system: {e}")
    
    async def update_system(
        self, 
        cn: str, 
        system_type: SystemType, 
        data: SystemUpdate,
        base_dn: Optional[str] = None
    ) -> SystemRead:
        """Update an existing system."""
        
        # Check exists and get current DN
        existing = await self.get_system(cn, system_type, base_dn=base_dn)
        if not existing:
            raise LdapNotFoundError(f"System '{cn}' of type '{system_type.value}' not found")
            
        # Determine actual DN from the existing entry or reconstruct
        # Since get_system returns SystemRead which doesn't have DN,
        # we might need to find the DN again if we didn't store it.
        # But wait, SystemRead usually doesn't expose DN.
        # We need the DN to update.
        # IF base_dn is used, we might not know the exact DN unless we searched.
        # get_system implementation above uses search but returns SystemRead.
        # We should use get_system logic to find DN?
        # Or better: search again here?
        
        if base_dn:
             # Search to get DN
             object_class = SystemType.get_object_class(system_type)
             search_filter = f"(&(cn={cn})(objectClass={object_class}))"
             entries = await self._ldap.search(base_dn, search_filter, attributes=["cn"])
             if not entries:
                 raise LdapNotFoundError(f"System '{cn}' not found in {base_dn}")
             dn = entries[0].dn
        else:
            dn = self._get_system_dn(cn, system_type)
        
        # Build changes
        changes = self._build_update_changes(data, system_type)
        
        if changes:
            try:
                await self._ldap.modify(dn, changes)
                logger.info(
                    "system_updated", 
                    cn=cn, 
                    type=system_type.value,
                    changes=len(changes)
                )
            except LdapOperationError as e:
                logger.error(
                    "system_update_failed", 
                    cn=cn, 
                    type=system_type.value,
                    error=str(e)
                )
                raise SystemValidationError(f"Failed to update system: {e}")
        
        return await self.get_system(cn, system_type, base_dn=base_dn)
    
    async def delete_system(
        self, 
        cn: str, 
        system_type: SystemType,
        base_dn: Optional[str] = None
    ) -> None:
        """Delete a system."""
        
        # Check exists and get DN
        existing = await self.get_system(cn, system_type, base_dn=base_dn)
        if not existing:
            raise LdapNotFoundError(f"System '{cn}' of type '{system_type.value}' not found")

        if base_dn:
             # Search to get DN
             object_class = SystemType.get_object_class(system_type)
             search_filter = f"(&(cn={cn})(objectClass={object_class}))"
             entries = await self._ldap.search(base_dn, search_filter, attributes=["cn"])
             if not entries:
                 raise LdapNotFoundError(f"System '{cn}' not found in {base_dn}")
             dn = entries[0].dn
        else:
            dn = self._get_system_dn(cn, system_type)
        
        try:
            await self._ldap.delete(dn)
            logger.info(
                "system_deleted", 
                cn=cn, 
                type=system_type.value,
                dn=dn
            )
        except LdapOperationError as e:
            logger.error(
                "system_delete_failed", 
                cn=cn, 
                type=system_type.value,
                error=str(e)
            )
            raise SystemValidationError(f"Failed to delete system: {e}")
    
    # ========================================================================
    # Host Validation (for other plugins)
    # ========================================================================
    
    async def validate_hosts(self, hostnames: List[str]) -> HostValidationResponse:
        """
        Validate that hostnames exist as registered systems.
        
        This method is used by other plugins (like POSIX) to validate
        host attributes against actual systems in the directory.
        
        Args:
            hostnames: List of hostnames to validate
            
        Returns:
            HostValidationResponse with valid and invalid hosts
        """
        if not hostnames:
            return HostValidationResponse(valid_hosts=[], invalid_hosts=[])
        
        valid_hosts = []
        invalid_hosts = []
        
        # Build filter to find any of the hostnames
        # Hostnames are stored as CN in systems
        escaped_names = [self._ldap._escape_filter(h) for h in hostnames]
        cn_filters = [f"(cn={name})" for name in escaped_names]
        
        # Match any of our system types
        type_filters = [
            f"(objectClass={SystemType.get_object_class(t)})"
            for t in SystemType
        ]
        
        search_filter = f"(&(|{''.join(type_filters)})(|{''.join(cn_filters)}))"
        
        try:
            entries = await self._ldap.search(
                search_base=self._systems_dn,
                search_filter=search_filter,
                attributes=["cn"],
            )
            
            # Extract found CNs
            found_cns = set()
            for entry in entries:
                cn = entry.get_first("cn") if hasattr(entry, 'get_first') else entry.get("cn", [""])[0]
                if cn:
                    found_cns.add(cn.lower())
            
            # Categorize hostnames
            for hostname in hostnames:
                if hostname.lower() in found_cns:
                    valid_hosts.append(hostname)
                else:
                    invalid_hosts.append(hostname)
            
        except LdapOperationError as e:
            logger.warning("host_validation_failed", error=str(e))
            # On error, mark all as invalid (strict mode)
            invalid_hosts = hostnames
        
        return HostValidationResponse(
            valid_hosts=valid_hosts,
            invalid_hosts=invalid_hosts,
        )
    
    async def host_exists(self, hostname: str) -> bool:
        """Check if a hostname exists as a registered system."""
        result = await self.validate_hosts([hostname])
        return len(result.valid_hosts) > 0
    
    async def get_all_hostnames(self) -> List[str]:
        """Get all registered system hostnames (for autocomplete)."""
        try:
            # Match any of our system types
            type_filters = [
                f"(objectClass={SystemType.get_object_class(t)})"
                for t in SystemType
            ]
            search_filter = f"(|{''.join(type_filters)})"
            
            entries = await self._ldap.search(
                search_base=self._systems_dn,
                search_filter=search_filter,
                attributes=["cn"],
            )
            
            hostnames = []
            for entry in entries:
                cn = entry.get_first("cn") if hasattr(entry, 'get_first') else entry.get("cn", [""])[0]
                if cn:
                    hostnames.append(cn)
            
            return sorted(hostnames)
            
        except LdapOperationError as e:
            logger.warning("get_all_hostnames_failed", error=str(e))
            return []
    
    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _entry_to_list_item(self, entry: LdapEntry) -> SystemListItem:
        """Convert LDAP entry to SystemListItem."""
        system_type = detect_system_type(entry)
        
        ip_addresses = entry.get("ipHostNumber", [])
        if isinstance(ip_addresses, str):
            ip_addresses = [ip_addresses]
        
        mac_addresses = entry.get("macAddress", [])
        if isinstance(mac_addresses, str):
            mac_addresses = [mac_addresses]
        
        mode_str = entry.get_first("hrcMode") if hasattr(entry, 'get_first') else entry.get("hrcMode", [None])[0]
        mode = LockMode(mode_str) if mode_str and mode_str in ["locked", "unlocked"] else None
        
        return SystemListItem(
            dn=entry.dn if hasattr(entry, 'dn') else entry.get("dn", ""),
            cn=entry.get_first("cn") if hasattr(entry, 'get_first') else entry.get("cn", [""])[0],
            system_type=system_type,
            description=entry.get_first("description") if hasattr(entry, 'get_first') else entry.get("description", [None])[0],
            ip_addresses=ip_addresses,
            mac_addresses=mac_addresses,
            location=entry.get_first("l") if hasattr(entry, 'get_first') else entry.get("l", [None])[0],
            mode=mode,
        )
    
    def _entry_to_read(self, entry: LdapEntry, system_type: SystemType) -> SystemRead:
        """Convert LDAP entry to SystemRead."""
        ip_addresses = entry.get("ipHostNumber", [])
        if isinstance(ip_addresses, str):
            ip_addresses = [ip_addresses]
        
        mac_addresses = entry.get("macAddress", [])
        if isinstance(mac_addresses, str):
            mac_addresses = [mac_addresses]
        
        mode_str = entry.get_first("hrcMode") if hasattr(entry, 'get_first') else entry.get("hrcMode", [None])[0]
        mode = LockMode(mode_str) if mode_str and mode_str in ["locked", "unlocked"] else None
        
        def get_first(attr: str) -> Optional[str]:
            if hasattr(entry, 'get_first'):
                return entry.get_first(attr)
            vals = entry.get(attr, [])
            return vals[0] if vals else None
        
        return SystemRead(
            dn=entry.dn if hasattr(entry, 'dn') else entry.get("dn", ""),
            cn=get_first("cn") or "",
            system_type=system_type,
            description=get_first("description"),
            ip_addresses=ip_addresses,
            mac_addresses=mac_addresses,
            location=get_first("l"),
            mode=mode,
            # Type-specific fields
            labeled_uri=get_first("labeledURI"),
            windows_inf_file=get_first("hrcPrinterWindowsInfFile"),
            windows_driver_dir=get_first("hrcPrinterWindowsDriverDir"),
            windows_driver_name=get_first("hrcPrinterWindowsDriverName"),
            telephone_number=get_first("telephoneNumber"),
            serial_number=get_first("serialNumber"),
            imei=get_first("hrcMobileIMEI"),
            operating_system=get_first("hrcMobileOS"),
            puk=get_first("hrcMobilePUK"),
            owner=get_first("owner"),
        )
    
    def _build_create_attributes(self, data: SystemCreate) -> Dict[str, List[str]]:
        """Build LDAP attributes for system creation."""
        attributes = {
            "cn": [data.cn],
        }
        
        if data.description:
            attributes["description"] = [data.description]
        
        if data.ip_addresses:
            attributes["ipHostNumber"] = data.ip_addresses
        
        if data.mac_addresses:
            attributes["macAddress"] = data.mac_addresses
        
        if data.location:
            attributes["l"] = [data.location]
        
        if data.mode:
            attributes["hrcMode"] = [data.mode.value]
        
        # Type-specific attributes
        if data.system_type == SystemType.PRINTER:
            if data.labeled_uri:
                attributes["labeledURI"] = [data.labeled_uri]
            if data.windows_inf_file:
                attributes["hrcPrinterWindowsInfFile"] = [data.windows_inf_file]
            if data.windows_driver_dir:
                attributes["hrcPrinterWindowsDriverDir"] = [data.windows_driver_dir]
            if data.windows_driver_name:
                attributes["hrcPrinterWindowsDriverName"] = [data.windows_driver_name]
        
        if data.system_type in [SystemType.PHONE, SystemType.MOBILE]:
            if data.telephone_number:
                attributes["telephoneNumber"] = [data.telephone_number]
            if data.serial_number:
                attributes["serialNumber"] = [data.serial_number]
        
        if data.system_type == SystemType.MOBILE:
            if data.imei:
                attributes["hrcMobileIMEI"] = [data.imei]
            if data.operating_system:
                attributes["hrcMobileOS"] = [data.operating_system]
            if data.puk:
                attributes["hrcMobilePUK"] = [data.puk]
        
        if data.system_type == SystemType.COMPONENT:
            if data.serial_number:
                attributes["serialNumber"] = [data.serial_number]
            if data.owner:
                attributes["owner"] = [data.owner]
        
        return attributes
    
    def _build_update_changes(
        self, 
        data: SystemUpdate, 
        system_type: SystemType
    ) -> Dict[str, Tuple[str, List[str]]]:
        """Build LDAP modification dict for system update."""
        changes = {}
        
        # Common attributes
        if data.description is not None:
            if data.description:
                changes["description"] = ("replace", [data.description])
            else:
                changes["description"] = ("delete", [])
        
        if data.ip_addresses is not None:
            if data.ip_addresses:
                changes["ipHostNumber"] = ("replace", data.ip_addresses)
            else:
                changes["ipHostNumber"] = ("delete", [])
        
        if data.mac_addresses is not None:
            if data.mac_addresses:
                changes["macAddress"] = ("replace", data.mac_addresses)
            else:
                changes["macAddress"] = ("delete", [])
        
        if data.location is not None:
            if data.location:
                changes["l"] = ("replace", [data.location])
            else:
                changes["l"] = ("delete", [])
        
        if data.mode is not None:
            changes["hrcMode"] = ("replace", [data.mode.value])
        
        # Type-specific attributes
        if system_type == SystemType.PRINTER:
            if data.labeled_uri is not None:
                if data.labeled_uri:
                    changes["labeledURI"] = ("replace", [data.labeled_uri])
                else:
                    changes["labeledURI"] = ("delete", [])
            if data.windows_inf_file is not None:
                if data.windows_inf_file:
                    changes["hrcPrinterWindowsInfFile"] = ("replace", [data.windows_inf_file])
                else:
                    changes["hrcPrinterWindowsInfFile"] = ("delete", [])
            if data.windows_driver_dir is not None:
                if data.windows_driver_dir:
                    changes["hrcPrinterWindowsDriverDir"] = ("replace", [data.windows_driver_dir])
                else:
                    changes["hrcPrinterWindowsDriverDir"] = ("delete", [])
            if data.windows_driver_name is not None:
                if data.windows_driver_name:
                    changes["hrcPrinterWindowsDriverName"] = ("replace", [data.windows_driver_name])
                else:
                    changes["hrcPrinterWindowsDriverName"] = ("delete", [])
        
        if system_type in [SystemType.PHONE, SystemType.MOBILE]:
            if data.telephone_number is not None:
                if data.telephone_number:
                    changes["telephoneNumber"] = ("replace", [data.telephone_number])
                else:
                    changes["telephoneNumber"] = ("delete", [])
            if data.serial_number is not None:
                if data.serial_number:
                    changes["serialNumber"] = ("replace", [data.serial_number])
                else:
                    changes["serialNumber"] = ("delete", [])
        
        if system_type == SystemType.MOBILE:
            if data.imei is not None:
                if data.imei:
                    changes["hrcMobileIMEI"] = ("replace", [data.imei])
                else:
                    changes["hrcMobileIMEI"] = ("delete", [])
            if data.operating_system is not None:
                if data.operating_system:
                    changes["hrcMobileOS"] = ("replace", [data.operating_system])
                else:
                    changes["hrcMobileOS"] = ("delete", [])
            if data.puk is not None:
                if data.puk:
                    changes["hrcMobilePUK"] = ("replace", [data.puk])
                else:
                    changes["hrcMobilePUK"] = ("delete", [])
        
        if system_type == SystemType.COMPONENT:
            if data.serial_number is not None:
                if data.serial_number:
                    changes["serialNumber"] = ("replace", [data.serial_number])
                else:
                    changes["serialNumber"] = ("delete", [])
            if data.owner is not None:
                if data.owner:
                    changes["owner"] = ("replace", [data.owner])
                else:
                    changes["owner"] = ("delete", [])
        
        return changes

    # ========================================================================
    # Abstract method implementations (required by TabService)
    # ========================================================================
    
    async def is_active(self, dn: str) -> bool:
        """
        Check if a system exists at the given DN.
        
        For standalone objects like systems, this checks if the entry exists.
        """
        try:
            entry = await self._ldap.get_by_dn(dn, attributes=["objectClass"])
            if entry is None:
                return False
            
            # Check if any system objectClass is present
            object_classes = {oc.lower() for oc in entry.get("objectClass", [])}
            system_classes = {"hrcserver", "hrcworkstation", "hrcterminal", 
                            "hrcprinter", "device", "hrcphone", "hrcmobilephone"}
            return bool(object_classes & system_classes)
        except Exception:
            return False
    
    async def read(self, dn: str) -> Optional[SystemRead]:
        """
        Read a system by DN.
        
        Extracts the CN and system type from the DN to use get_system.
        """
        try:
            entry = await self._ldap.get_by_dn(dn, attributes=["objectClass", "cn"])
            if entry is None:
                return None
            
            cn = entry.get("cn", [None])[0]
            if not cn:
                return None
            
            # Determine system type from objectClass
            object_classes = {oc.lower() for oc in entry.get("objectClass", [])}
            system_type = None
            for oc in object_classes:
                system_type = SystemType.from_object_class(oc)
                if system_type:
                    break
            
            if not system_type:
                return None
            
            return await self.get_system(system_type, cn)
        except Exception:
            return None
    
    async def activate(self, dn: str, data: SystemCreate) -> SystemRead:
        """
        Create/activate a system.
        
        For standalone objects, this is equivalent to create_system.
        """
        return await self.create_system(data)
    
    async def update(self, dn: str, data: SystemUpdate) -> SystemRead:
        """
        Update a system by DN.
        
        Extracts CN and type from DN to use update_system.
        """
        # Parse CN from DN
        cn_part = dn.split(",")[0]
        if "=" in cn_part:
            cn = cn_part.split("=")[1]
        else:
            raise SystemValidationError(f"Invalid DN format: {dn}")
        
        # Get existing entry to determine type
        entry = await self._ldap.get_by_dn(dn, attributes=["objectClass"])
        if entry is None:
            raise LdapNotFoundError(f"System not found: {dn}")
        
        object_classes = {oc.lower() for oc in entry.get("objectClass", [])}
        system_type = None
        for oc in object_classes:
            system_type = SystemType.from_object_class(oc)
            if system_type:
                break
        
        if not system_type:
            raise SystemValidationError(f"Could not determine system type for: {dn}")
        
        return await self.update_system(system_type, cn, data)
    
    async def deactivate(self, dn: str) -> None:
        """
        Delete/deactivate a system.
        
        For standalone objects, this deletes the entry.
        """
        # Parse CN from DN
        cn_part = dn.split(",")[0]
        if "=" in cn_part:
            cn = cn_part.split("=")[1]
        else:
            raise SystemValidationError(f"Invalid DN format: {dn}")
        
        # Get existing entry to determine type
        entry = await self._ldap.get_by_dn(dn, attributes=["objectClass"])
        if entry is None:
            raise LdapNotFoundError(f"System not found: {dn}")
        
        object_classes = {oc.lower() for oc in entry.get("objectClass", [])}
        system_type = None
        for oc in object_classes:
            system_type = SystemType.from_object_class(oc)
            if system_type:
                break
        
        if not system_type:
            raise SystemValidationError(f"Could not determine system type for: {dn}")
        
        await self.delete_system(system_type, cn)

