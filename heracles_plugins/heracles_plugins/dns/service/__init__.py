"""
DNS Service Package
===================

DNS service implementation with constants and utilities.
"""

from .service import DnsService, DnsValidationError
from .base import DnsServiceBase
from .constants import (
    DNS_BASE_RDN,
    OBJECT_CLASSES,
    DNS_CLASS,
    MANAGED_ATTRIBUTES,
)
from .utils import (
    get_first_value,
    get_list_value,
    get_entry_dn,
)

__all__ = [
    # Service
    "DnsService",
    "DnsServiceBase",
    "DnsValidationError",
    # Constants
    "DNS_BASE_RDN",
    "OBJECT_CLASSES",
    "DNS_CLASS",
    "MANAGED_ATTRIBUTES",
    # Utilities
    "get_first_value",
    "get_list_value",
    "get_entry_dn",
]
