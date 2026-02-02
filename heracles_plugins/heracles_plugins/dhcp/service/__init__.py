"""
DHCP Service Package
====================

DHCP service implementation with constants and utilities.
"""

from .service import DhcpService, DhcpValidationError
from .constants import (
    TYPE_OBJECT_CLASSES,
    COMMON_ATTRIBUTES,
    SERVICE_ATTRIBUTES,
    SUBNET_ATTRIBUTES,
    POOL_ATTRIBUTES,
    HOST_ATTRIBUTES,
    SHARED_NETWORK_ATTRIBUTES,
    GROUP_ATTRIBUTES,
    CLASS_ATTRIBUTES,
    SUBCLASS_ATTRIBUTES,
    TSIG_KEY_ATTRIBUTES,
    DNS_ZONE_ATTRIBUTES,
    FAILOVER_PEER_ATTRIBUTES,
    get_all_attributes,
)
from .utils import (
    get_first_value,
    get_list_value,
    extract_fixed_address,
    detect_object_type,
    get_parent_dn,
    build_object_dn,
)

__all__ = [
    # Service
    "DhcpService",
    "DhcpValidationError",
    # Constants
    "TYPE_OBJECT_CLASSES",
    "COMMON_ATTRIBUTES",
    "SERVICE_ATTRIBUTES",
    "SUBNET_ATTRIBUTES",
    "POOL_ATTRIBUTES",
    "HOST_ATTRIBUTES",
    "SHARED_NETWORK_ATTRIBUTES",
    "GROUP_ATTRIBUTES",
    "CLASS_ATTRIBUTES",
    "SUBCLASS_ATTRIBUTES",
    "TSIG_KEY_ATTRIBUTES",
    "DNS_ZONE_ATTRIBUTES",
    "FAILOVER_PEER_ATTRIBUTES",
    "get_all_attributes",
    # Utilities
    "get_first_value",
    "get_list_value",
    "extract_fixed_address",
    "detect_object_type",
    "get_parent_dn",
    "build_object_dn",
]
