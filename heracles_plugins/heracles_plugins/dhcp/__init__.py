"""
DHCP Plugin
===========

Provides DHCP configuration management for LDAP-based infrastructure.

Manages the following LDAP objectClasses:
- dhcpService: Root DHCP service configuration
- dhcpSharedNetwork: Shared network configurations
- dhcpSubnet: Subnet definitions with IP ranges
- dhcpPool: IP address pools within subnets
- dhcpHost: Host reservations with fixed addresses
- dhcpGroup: Logical grouping of hosts
- dhcpClass: Client classification rules
- dhcpSubClass: Subclass for client matching
- dhcpTSigKey: TSIG keys for secure DNS updates
- dhcpDnsZone: DNS zones for dynamic updates
- dhcpFailOverPeer: Failover peer configuration

Hierarchy:
    dhcpService (root)
    ├── dhcpSharedNetwork
    │   └── dhcpSubnet
    │       ├── dhcpPool
    │       └── dhcpHost
    ├── dhcpSubnet
    │   ├── dhcpPool
    │   ├── dhcpHost
    │   └── dhcpGroup
    │       └── dhcpHost
    ├── dhcpGroup
    │   └── dhcpHost
    ├── dhcpHost
    ├── dhcpClass
    │   └── dhcpSubClass
    ├── dhcpTSigKey
    ├── dhcpDnsZone
    └── dhcpFailOverPeer

Common Attributes:
- cn: Object name (required)
- dhcpStatements: DHCP configuration statements
- dhcpOption: DHCP options to send to clients
- dhcpComments: Comments/description

Integration:
- Optional integration with 'systems' plugin for host validation
"""

from .plugin import DhcpPlugin

__plugin__ = DhcpPlugin

__all__ = ["DhcpPlugin", "__plugin__"]
