"""
Sudo Service Package
====================

Service for managing sudo roles in LDAP.
"""

from .sudo_service import SudoService
from .base import SudoValidationError

__all__ = [
    "SudoService",
    "SudoValidationError",
]
