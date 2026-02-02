"""
DHCP Schemas Package
====================

Re-exports all DHCP Pydantic models for backward compatibility.
"""

# Enums
from .enums import DhcpObjectType, TsigKeyAlgorithm

# Validators
from .validators import (
    validate_ip_address,
    validate_ip_range,
    validate_mac_address,
    validate_netmask,
    validate_cn_alphanumeric,
)

# Base
from .base import DhcpBase, PaginatedResponse

# Service
from .service import (
    DhcpServiceCreate,
    DhcpServiceUpdate,
    DhcpServiceRead,
    DhcpServiceListItem,
    DhcpServiceListResponse,
)

# Subnet
from .subnet import (
    SubnetCreate,
    SubnetUpdate,
    SubnetRead,
    SubnetListItem,
    SubnetListResponse,
)

# Pool
from .pool import (
    PoolCreate,
    PoolUpdate,
    PoolRead,
    PoolListItem,
    PoolListResponse,
)

# Host
from .host import (
    HostCreate,
    HostUpdate,
    HostRead,
    HostListItem,
    HostListResponse,
)

# Shared Network
from .shared_network import (
    SharedNetworkCreate,
    SharedNetworkUpdate,
    SharedNetworkRead,
    SharedNetworkListItem,
    SharedNetworkListResponse,
)

# Group
from .group import (
    GroupCreate,
    GroupUpdate,
    GroupRead,
    GroupListItem,
    GroupListResponse,
)

# Class
from .dhcp_class import (
    DhcpClassCreate,
    DhcpClassUpdate,
    DhcpClassRead,
    DhcpClassListItem,
    DhcpClassListResponse,
    SubClassCreate,
    SubClassUpdate,
    SubClassRead,
)

# TSIG Key
from .tsig_key import (
    TsigKeyCreate,
    TsigKeyUpdate,
    TsigKeyRead,
    TsigKeyListItem,
    TsigKeyListResponse,
)

# DNS Zone
from .dns_zone import (
    DnsZoneCreate,
    DnsZoneUpdate,
    DnsZoneRead,
    DnsZoneListItem,
    DnsZoneListResponse,
)

# Failover Peer
from .failover_peer import (
    FailoverPeerCreate,
    FailoverPeerUpdate,
    FailoverPeerRead,
    FailoverPeerListItem,
    FailoverPeerListResponse,
)

# Tree
from .tree import (
    DhcpTreeNode,
    DhcpTreeResponse,
    DhcpObjectCreate,
    DhcpObjectRead,
)

__all__ = [
    # Enums
    "DhcpObjectType",
    "TsigKeyAlgorithm",
    # Validators
    "validate_ip_address",
    "validate_ip_range",
    "validate_mac_address",
    "validate_netmask",
    "validate_cn_alphanumeric",
    # Base
    "DhcpBase",
    "PaginatedResponse",
    # Service
    "DhcpServiceCreate",
    "DhcpServiceUpdate",
    "DhcpServiceRead",
    "DhcpServiceListItem",
    "DhcpServiceListResponse",
    # Subnet
    "SubnetCreate",
    "SubnetUpdate",
    "SubnetRead",
    "SubnetListItem",
    "SubnetListResponse",
    # Pool
    "PoolCreate",
    "PoolUpdate",
    "PoolRead",
    "PoolListItem",
    "PoolListResponse",
    # Host
    "HostCreate",
    "HostUpdate",
    "HostRead",
    "HostListItem",
    "HostListResponse",
    # Shared Network
    "SharedNetworkCreate",
    "SharedNetworkUpdate",
    "SharedNetworkRead",
    "SharedNetworkListItem",
    "SharedNetworkListResponse",
    # Group
    "GroupCreate",
    "GroupUpdate",
    "GroupRead",
    "GroupListItem",
    "GroupListResponse",
    # Class
    "DhcpClassCreate",
    "DhcpClassUpdate",
    "DhcpClassRead",
    "DhcpClassListItem",
    "DhcpClassListResponse",
    "SubClassCreate",
    "SubClassUpdate",
    "SubClassRead",
    # TSIG Key
    "TsigKeyCreate",
    "TsigKeyUpdate",
    "TsigKeyRead",
    "TsigKeyListItem",
    "TsigKeyListResponse",
    # DNS Zone
    "DnsZoneCreate",
    "DnsZoneUpdate",
    "DnsZoneRead",
    "DnsZoneListItem",
    "DnsZoneListResponse",
    # Failover Peer
    "FailoverPeerCreate",
    "FailoverPeerUpdate",
    "FailoverPeerRead",
    "FailoverPeerListItem",
    "FailoverPeerListResponse",
    # Tree
    "DhcpTreeNode",
    "DhcpTreeResponse",
    "DhcpObjectCreate",
    "DhcpObjectRead",
]
