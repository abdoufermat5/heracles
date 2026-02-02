"""
DHCP Operations Package
=======================

Provides operation mixins for different DHCP object types.
"""

from .service_ops import ServiceOperationsMixin
from .subnet_ops import SubnetOperationsMixin
from .pool_ops import PoolOperationsMixin
from .host_ops import HostOperationsMixin
from .shared_network_ops import SharedNetworkOperationsMixin
from .group_ops import GroupOperationsMixin
from .class_ops import ClassOperationsMixin
from .tsig_key_ops import TsigKeyOperationsMixin
from .dns_zone_ops import DnsZoneOperationsMixin
from .failover_peer_ops import FailoverPeerOperationsMixin
from .tree_ops import TreeOperationsMixin

__all__ = [
    "ServiceOperationsMixin",
    "SubnetOperationsMixin",
    "PoolOperationsMixin",
    "HostOperationsMixin",
    "SharedNetworkOperationsMixin",
    "GroupOperationsMixin",
    "ClassOperationsMixin",
    "TsigKeyOperationsMixin",
    "DnsZoneOperationsMixin",
    "FailoverPeerOperationsMixin",
    "TreeOperationsMixin",
]
