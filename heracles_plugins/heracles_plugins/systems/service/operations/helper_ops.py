"""
Helper Operations
=================

Entry conversion and attribute building helpers.
"""

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from heracles_api.services.ldap_service import LdapEntry

if TYPE_CHECKING:
    from ..base import SystemServiceBase

from ...schemas import (
    SystemType,
    SystemCreate,
    SystemRead,
    SystemUpdate,
    SystemListItem,
    LockMode,
)
from ..utils import detect_system_type


class HelperOperationsMixin:
    """Mixin providing helper methods for entry conversion and attribute building."""
    
    def _entry_to_list_item(self: "SystemServiceBase", entry: LdapEntry) -> SystemListItem:
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
    
    def _entry_to_read(self: "SystemServiceBase", entry: LdapEntry, system_type: SystemType) -> SystemRead:
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
    
    def _build_create_attributes(self: "SystemServiceBase", data: SystemCreate) -> Dict[str, List[str]]:
        """Build LDAP attributes for system creation."""
        attributes: Dict[str, List[str]] = {
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
        self: "SystemServiceBase", 
        data: SystemUpdate, 
        system_type: SystemType
    ) -> Dict[str, Tuple[str, List[str]]]:
        """Build LDAP modification dict for system update."""
        changes: Dict[str, Tuple[str, List[str]]] = {}
        
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
