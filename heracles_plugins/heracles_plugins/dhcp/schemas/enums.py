"""
DHCP Enums
==========

Enumeration types for DHCP objects.
"""

from enum import Enum
from typing import List, Optional


class DhcpObjectType(str, Enum):
    """DHCP object types supported by the plugin."""

    SERVICE = "service"
    SHARED_NETWORK = "shared-network"
    SUBNET = "subnet"
    POOL = "pool"
    HOST = "host"
    GROUP = "group"
    CLASS = "class"
    SUBCLASS = "subclass"
    TSIG_KEY = "tsig-key"
    DNS_ZONE = "dns-zone"
    FAILOVER_PEER = "failover-peer"

    @classmethod
    def get_object_class(cls, obj_type: "DhcpObjectType") -> str:
        """Get the LDAP objectClass for a DHCP object type."""
        mapping = {
            cls.SERVICE: "dhcpService",
            cls.SHARED_NETWORK: "dhcpSharedNetwork",
            cls.SUBNET: "dhcpSubnet",
            cls.POOL: "dhcpPool",
            cls.HOST: "dhcpHost",
            cls.GROUP: "dhcpGroup",
            cls.CLASS: "dhcpClass",
            cls.SUBCLASS: "dhcpSubClass",
            cls.TSIG_KEY: "dhcpTSigKey",
            cls.DNS_ZONE: "dhcpDnsZone",
            cls.FAILOVER_PEER: "dhcpFailOverPeer",
        }
        return mapping[obj_type]

    @classmethod
    def from_object_class(cls, object_class: str) -> Optional["DhcpObjectType"]:
        """Get the DhcpObjectType from an LDAP objectClass."""
        mapping = {
            "dhcpService": cls.SERVICE,
            "dhcpSharedNetwork": cls.SHARED_NETWORK,
            "dhcpSubnet": cls.SUBNET,
            "dhcpPool": cls.POOL,
            "dhcpHost": cls.HOST,
            "dhcpGroup": cls.GROUP,
            "dhcpClass": cls.CLASS,
            "dhcpSubClass": cls.SUBCLASS,
            "dhcpTSigKey": cls.TSIG_KEY,
            "dhcpDnsZone": cls.DNS_ZONE,
            "dhcpFailOverPeer": cls.FAILOVER_PEER,
        }
        return mapping.get(object_class)

    @classmethod
    def get_allowed_children(cls, obj_type: "DhcpObjectType") -> List["DhcpObjectType"]:
        """Get allowed child object types for a parent type."""
        mapping = {
            cls.SERVICE: [
                cls.SHARED_NETWORK, cls.SUBNET, cls.GROUP, cls.HOST,
                cls.CLASS, cls.TSIG_KEY, cls.DNS_ZONE, cls.FAILOVER_PEER
            ],
            cls.SHARED_NETWORK: [
                cls.SUBNET, cls.POOL, cls.TSIG_KEY, cls.DNS_ZONE, cls.FAILOVER_PEER
            ],
            cls.SUBNET: [
                cls.POOL, cls.GROUP, cls.HOST, cls.CLASS,
                cls.TSIG_KEY, cls.DNS_ZONE, cls.FAILOVER_PEER
            ],
            cls.GROUP: [cls.HOST],
            cls.CLASS: [cls.SUBCLASS],
            cls.POOL: [],
            cls.HOST: [],
            cls.SUBCLASS: [],
            cls.TSIG_KEY: [],
            cls.DNS_ZONE: [],
            cls.FAILOVER_PEER: [],
        }
        return mapping.get(obj_type, [])


class TsigKeyAlgorithm(str, Enum):
    """TSIG key algorithms."""

    HMAC_MD5 = "hmac-md5"
    HMAC_SHA1 = "hmac-sha1"
    HMAC_SHA256 = "hmac-sha256"
    HMAC_SHA512 = "hmac-sha512"
