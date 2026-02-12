"""
DNS Service Utilities
=====================

Helper functions for DNS service operations.
"""

from typing import Any, List

from heracles_api.services.ldap_service import LdapEntry


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


def get_entry_dn(entry: LdapEntry) -> str:
    """Safely get the DN from an entry."""
    if hasattr(entry, 'dn'):
        return entry.dn or ""
    return entry.get("dn", "")
