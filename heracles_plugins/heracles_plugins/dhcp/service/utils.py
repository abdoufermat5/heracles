"""
DHCP Service Utilities
======================

Helper functions for DHCP service operations.
"""

from typing import Any, List, Optional

from heracles_api.services.ldap_service import LdapEntry

from ..schemas import DhcpObjectType


def get_first_value(entry: LdapEntry, attr: str, default: Any = None) -> Any:
    """
    Safely get the first value of an attribute.

    Handles both single values and lists returned by LdapEntry.
    """
    value = entry.get(attr)
    if value is None:
        return default
    if isinstance(value, list):
        return value[0] if value else default
    return value


def get_list_value(entry: LdapEntry, attr: str) -> List[str]:
    """
    Safely get an attribute as a list.

    Handles both single values and lists returned by LdapEntry.
    """
    value = entry.get(attr)
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def extract_fixed_address(statements: List[str]) -> Optional[str]:
    """Extract fixed-address from dhcpStatements."""
    for stmt in statements:
        if stmt.startswith("fixed-address "):
            return stmt.split(" ", 1)[1].strip().rstrip(";")
    return None


def detect_object_type(entry: LdapEntry) -> Optional[DhcpObjectType]:
    """Detect object type from LDAP entry objectClasses."""
    object_classes = entry.get("objectClass", [])
    for oc in object_classes:
        obj_type = DhcpObjectType.from_object_class(oc)
        if obj_type:
            return obj_type
    return None


def get_parent_dn(dn: str, default_dn: str = "") -> str:
    """Extract parent DN from an object DN."""
    parts = dn.split(",", 1)
    if len(parts) > 1:
        return parts[1]
    return default_dn


def build_object_dn(cn: str, parent_dn: str) -> str:
    """Build the DN for a DHCP object under a parent."""
    return f"cn={cn},{parent_dn}"
