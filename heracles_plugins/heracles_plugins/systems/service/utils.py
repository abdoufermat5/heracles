"""
Systems Service Utilities
=========================

Helper functions for system service operations.
"""

from typing import Any, List, Optional

from heracles_api.services.ldap_service import LdapEntry

from ..schemas import SystemType, LockMode


def get_first_value(entry: LdapEntry, attr: str, default: Any = None) -> Any:
    """
    Safely get the first value of an attribute.

    Handles both single values and lists returned by LdapEntry.
    """
    if hasattr(entry, 'get_first'):
        return entry.get_first(attr) or default
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
    value = entry.get(attr, [])
    if isinstance(value, str):
        return [value]
    return value if value else []


def detect_system_type(entry: LdapEntry) -> Optional[SystemType]:
    """Detect system type from entry's objectClasses."""
    object_classes = entry.get("objectClass", [])
    if isinstance(object_classes, str):
        object_classes = [object_classes]

    for oc in object_classes:
        system_type = SystemType.from_object_class(oc)
        if system_type:
            return system_type

    return None


def parse_lock_mode(entry: LdapEntry) -> Optional[LockMode]:
    """Parse the lock mode from an entry."""
    mode_str = get_first_value(entry, "hrcMode")
    if mode_str and mode_str in ["locked", "unlocked"]:
        return LockMode(mode_str)
    return None


def get_entry_dn(entry: LdapEntry) -> str:
    """Safely get the DN from an entry."""
    if hasattr(entry, 'dn'):
        return entry.dn or ""
    return entry.get("dn", "")
