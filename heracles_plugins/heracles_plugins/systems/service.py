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

from .schemas import (
    SystemType,
    SystemCreate,
    SystemRead,
    SystemUpdate,
    SystemListItem,
    SystemListResponse,
    LockMode,
    HostValidationResponse,
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
    
    # Map system types to their primary objectClass
    TYPE_OBJECT_CLASSES = {
        SystemType.SERVER: ["hrcServer", "ipHost", "ieee802Device"],
        SystemType.WORKSTATION: ["hrcWorkstation", "ipHost", "ieee802Device"],
        SystemType.TERMINAL: ["hrcTerminal", "ipHost", "ieee802Device"],
        SystemType.PRINTER: ["hrcPrinter", "ipHost", "ieee802Device"],
        SystemType.COMPONENT: ["device", "ipHost", "ieee802Device"],
        SystemType.PHONE: ["hrcPhone", "ipHost", "ieee802Device"],
        SystemType.MOBILE: ["hrcMobilePhone"],
    }
    
    # Common attributes for all system types
    COMMON_ATTRIBUTES = [
        "cn",
        "description",
        "ipHostNumber",
        "macAddress",
        "l",  # location
        "hrcMode",
    ]
    
    # Type-specific attributes
    PRINTER_ATTRIBUTES = [
        "labeledURI",
        "hrcPrinterWindowsInfFile",
        "hrcPrinterWindowsDriverDir",
        "hrcPrinterWindowsDriverName",
    ]
    
    PHONE_ATTRIBUTES = [
        "telephoneNumber",
        "serialNumber",
    ]
    
    MOBILE_ATTRIBUTES = PHONE_ATTRIBUTES + [
        "hrcMobileIMEI",
        "hrcMobileOS",
        "hrcMobilePUK",
    ]
    
    COMPONENT_ATTRIBUTES = [
        "serialNumber",
        "owner",
    ]
    
    def __init__(self, ldap_service: LdapService, config: Dict[str, Any]):
        super().__init__(ldap_service, config)
        
        # Configuration
        self._systems_rdn = config.get("systems_rdn", "ou=systems")
        self._base_dn = config.get("base_dn", ldap_service.base_dn)
        self._systems_dn = f"{self._systems_rdn},{self._base_dn}"
    
    def _get_all_attributes(self) -> List[str]:
        """Get all managed attributes."""
        attrs = set(self.COMMON_ATTRIBUTES)
        attrs.update(self.PRINTER_ATTRIBUTES)
        attrs.update(self.MOBILE_ATTRIBUTES)  # Includes PHONE_ATTRIBUTES
        attrs.update(self.COMPONENT_ATTRIBUTES)
        attrs.add("objectClass")
        return list(attrs)
    
    def _get_type_ou(self, system_type: SystemType) -> str:
        """Get the OU DN for a system type."""
        rdn = SystemType.get_rdn(system_type)
        return f"{rdn},{self._systems_dn}"
    
    def _get_system_dn(self, cn: str, system_type: SystemType) -> str:
        """Get the DN for a system."""
        ou_dn = self._get_type_ou(system_type)
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
            # Determine search base
            if system_type:
                search_base = self._get_type_ou(system_type)
            else:
                search_base = self._systems_dn
            
            entries = await self._ldap.search(
                search_base=search_base,
                search_filter=combined_filter,
                attributes=self._get_all_attributes(),
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
    
    async def get_system(self, cn: str, system_type: SystemType) -> Optional[SystemRead]:
        """Get a single system by CN and type."""
        dn = self._get_system_dn(cn, system_type)
        
        try:
            entry = await self._ldap.get_by_dn(
                dn, 
                attributes=self._get_all_attributes()
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
                attributes=self._get_all_attributes()
            )
            if entry is None:
                return None
            
            # Detect type from objectClass
            system_type = self._detect_type(entry)
            if system_type is None:
                return None
            
            return self._entry_to_read(entry, system_type)
        except LdapOperationError:
            return None
    
    async def create_system(self, data: SystemCreate) -> SystemRead:
        """Create a new system."""
        
        # Ensure OU exists
        await self._ensure_type_ou(data.system_type)
        
        dn = self._get_system_dn(data.cn, data.system_type)
        
        # Check if system already exists
        existing = await self.get_system(data.cn, data.system_type)
        if existing:
            raise SystemValidationError(
                f"System '{data.cn}' of type '{data.system_type.value}' already exists"
            )
        
        # Get object classes for this type
        object_classes = self.TYPE_OBJECT_CLASSES[data.system_type].copy()
        
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
                dn=dn
            )
            
            # Read back and return
            return await self.get_system(data.cn, data.system_type)
            
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
        data: SystemUpdate
    ) -> SystemRead:
        """Update an existing system."""
        
        dn = self._get_system_dn(cn, system_type)
        
        # Check exists
        existing = await self.get_system(cn, system_type)
        if not existing:
            raise LdapNotFoundError(f"System '{cn}' of type '{system_type.value}' not found")
        
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
        
        return await self.get_system(cn, system_type)
    
    async def delete_system(self, cn: str, system_type: SystemType) -> None:
        """Delete a system."""
        
        dn = self._get_system_dn(cn, system_type)
        
        # Check exists
        existing = await self.get_system(cn, system_type)
        if not existing:
            raise LdapNotFoundError(f"System '{cn}' of type '{system_type.value}' not found")
        
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
    
    def _detect_type(self, entry: LdapEntry) -> Optional[SystemType]:
        """Detect system type from entry's objectClasses."""
        object_classes = entry.get("objectClass", [])
        if isinstance(object_classes, str):
            object_classes = [object_classes]
        
        for oc in object_classes:
            system_type = SystemType.from_object_class(oc)
            if system_type:
                return system_type
        
        return None
    
    def _entry_to_list_item(self, entry: LdapEntry) -> SystemListItem:
        """Convert LDAP entry to SystemListItem."""
        system_type = self._detect_type(entry)
        
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

