"""
Systems Service Constants
=========================

Attribute definitions and mappings for system objects.
"""

from typing import Dict, List
from ..schemas import SystemType


# Map system types to their LDAP objectClasses
TYPE_OBJECT_CLASSES: Dict[SystemType, List[str]] = {
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


def get_all_attributes() -> List[str]:
    """Get all managed attributes."""
    attrs = set(COMMON_ATTRIBUTES)
    attrs.update(PRINTER_ATTRIBUTES)
    attrs.update(MOBILE_ATTRIBUTES)  # Includes PHONE_ATTRIBUTES
    attrs.update(COMPONENT_ATTRIBUTES)
    attrs.add("objectClass")
    return list(attrs)
