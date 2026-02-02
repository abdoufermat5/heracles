"""
DHCP Service Constants
======================

Attribute definitions and mappings for DHCP objects.
"""

from typing import Dict, List
from ..schemas import DhcpObjectType


# Map object types to their LDAP objectClasses
TYPE_OBJECT_CLASSES: Dict[DhcpObjectType, List[str]] = {
    DhcpObjectType.SERVICE: ["dhcpService"],
    DhcpObjectType.SHARED_NETWORK: ["dhcpSharedNetwork"],
    DhcpObjectType.SUBNET: ["dhcpSubnet"],
    DhcpObjectType.POOL: ["dhcpPool"],
    DhcpObjectType.HOST: ["dhcpHost"],
    DhcpObjectType.GROUP: ["dhcpGroup"],
    DhcpObjectType.CLASS: ["dhcpClass"],
    DhcpObjectType.SUBCLASS: ["dhcpSubClass"],
    DhcpObjectType.TSIG_KEY: ["dhcpTSigKey"],
    DhcpObjectType.DNS_ZONE: ["dhcpDnsZone"],
    DhcpObjectType.FAILOVER_PEER: ["dhcpFailOverPeer"],
}

# Common attributes for all DHCP types
COMMON_ATTRIBUTES = [
    "cn",
    "objectClass",
    "dhcpStatements",
    "dhcpOption",
    "dhcpComments",
]

# Service-specific attributes
SERVICE_ATTRIBUTES = [
    "dhcpPrimaryDN",
    "dhcpSecondaryDN",
    "dhcpServerDN",
    "dhcpSharedNetworkDN",
    "dhcpSubnetDN",
    "dhcpGroupDN",
    "dhcpHostDN",
    "dhcpClassesDN",
    "dhcpZoneDN",
    "dhcpKeyDN",
    "dhcpFailOverPeerDN",
]

# Subnet-specific attributes
SUBNET_ATTRIBUTES = [
    "dhcpNetMask",
    "dhcpRange",
    "dhcpPoolDN",
    "dhcpGroupDN",
    "dhcpHostDN",
    "dhcpClassesDN",
    "dhcpLeasesDN",
    "dhcpZoneDN",
    "dhcpKeyDN",
    "dhcpFailOverPeerDN",
]

# Pool-specific attributes
POOL_ATTRIBUTES = [
    "dhcpRange",
    "dhcpPermitList",
    "dhcpClassesDN",
    "dhcpLeasesDN",
    "dhcpZoneDN",
    "dhcpKeyDN",
]

# Host-specific attributes
HOST_ATTRIBUTES = [
    "dhcpHWAddress",
    "dhcpLeaseDN",
]

# Shared network-specific attributes
SHARED_NETWORK_ATTRIBUTES = [
    "dhcpSubnetDN",
    "dhcpPoolDN",
    "dhcpZoneDN",
]

# Group-specific attributes
GROUP_ATTRIBUTES = [
    "dhcpHostDN",
]

# Class-specific attributes
CLASS_ATTRIBUTES = [
    "dhcpSubClassesDN",
]

# SubClass-specific attributes
SUBCLASS_ATTRIBUTES = [
    "dhcpClassData",
]

# TSIG Key-specific attributes
TSIG_KEY_ATTRIBUTES = [
    "dhcpKeyAlgorithm",
    "dhcpKeySecret",
]

# DNS Zone-specific attributes
DNS_ZONE_ATTRIBUTES = [
    "dhcpDnsZoneServer",
    "dhcpKeyDN",
]

# Failover Peer-specific attributes
FAILOVER_PEER_ATTRIBUTES = [
    "dhcpFailOverPrimaryServer",
    "dhcpFailOverSecondaryServer",
    "dhcpFailOverPrimaryPort",
    "dhcpFailOverSecondaryPort",
    "dhcpFailOverResponseDelay",
    "dhcpFailOverUnackedUpdates",
    "dhcpMaxClientLeadTime",
    "dhcpFailOverSplit",
    "dhcpHashBucketAssignment",
    "dhcpFailOverLoadBalanceTime",
]


def get_all_attributes() -> List[str]:
    """Get all managed attributes."""
    attrs = set(COMMON_ATTRIBUTES)
    attrs.update(SERVICE_ATTRIBUTES)
    attrs.update(SUBNET_ATTRIBUTES)
    attrs.update(POOL_ATTRIBUTES)
    attrs.update(HOST_ATTRIBUTES)
    attrs.update(SHARED_NETWORK_ATTRIBUTES)
    attrs.update(GROUP_ATTRIBUTES)
    attrs.update(CLASS_ATTRIBUTES)
    attrs.update(SUBCLASS_ATTRIBUTES)
    attrs.update(TSIG_KEY_ATTRIBUTES)
    attrs.update(DNS_ZONE_ATTRIBUTES)
    attrs.update(FAILOVER_PEER_ATTRIBUTES)
    return list(attrs)
