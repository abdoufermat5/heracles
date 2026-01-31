"""
POSIX Plugin Services - Base Module
====================================

Shared utilities, exceptions, and helpers for POSIX services.
"""

from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


class PosixValidationError(Exception):
    """Raised when POSIX validation fails."""
    pass


def get_int(entry: Any, attr: str) -> int:
    """
    Get integer attribute, raising if not present.
    
    Args:
        entry: LDAP entry object
        attr: Attribute name
        
    Returns:
        Integer value of the attribute
        
    Raises:
        PosixValidationError: If attribute is missing
    """
    if hasattr(entry, 'get_first'):
        val = entry.get_first(attr)
    else:
        vals = entry.get(attr, [])
        val = vals[0] if vals else None
    
    if val is None:
        raise PosixValidationError(f"Missing required attribute: {attr}")
    return int(val)


def get_int_optional(entry: Any, attr: str) -> Optional[int]:
    """
    Get optional integer attribute.
    
    Args:
        entry: LDAP entry object
        attr: Attribute name
        
    Returns:
        Integer value or None if not present
    """
    if hasattr(entry, 'get_first'):
        val = entry.get_first(attr)
    else:
        vals = entry.get(attr, [])
        val = vals[0] if vals else None
    return int(val) if val is not None else None
