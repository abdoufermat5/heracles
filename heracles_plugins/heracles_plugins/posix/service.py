"""
POSIX Service (Facade Module)
=============================

This module re-exports service classes for backward compatibility.
New code should import directly from heracles_plugins.posix.services.

Example:
    # Legacy import (still works)
    from heracles_plugins.posix.service import PosixService
    
    # Preferred import
    from heracles_plugins.posix.services import PosixService
"""

from .services import (
    PosixValidationError,
    PosixService,
    PosixGroupService,
    MixedGroupService,
)

__all__ = [
    "PosixValidationError",
    "PosixService",
    "PosixGroupService",
    "MixedGroupService",
]
