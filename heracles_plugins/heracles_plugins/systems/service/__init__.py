"""
Systems Service Package
=======================

Systems service implementation with constants and utilities.
"""

from .service import SystemService, SystemValidationError
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

__all__ = [
    # Service
    "SystemService",
    "SystemValidationError",
    # Constants
    "TYPE_OBJECT_CLASSES",
    "COMMON_ATTRIBUTES",
    "PRINTER_ATTRIBUTES",
    "PHONE_ATTRIBUTES",
    "MOBILE_ATTRIBUTES",
    "COMPONENT_ATTRIBUTES",
    "get_all_attributes",
    # Utilities
    "get_first_value",
    "get_list_value",
    "detect_system_type",
    "parse_lock_mode",
    "get_entry_dn",
]
