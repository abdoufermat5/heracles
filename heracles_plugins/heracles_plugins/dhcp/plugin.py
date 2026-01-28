"""
DHCP Plugin Definition
======================

Main plugin class that registers DHCP configuration management functionality.
"""

from typing import Any, List

from heracles_api.plugins.base import Plugin, PluginInfo, TabDefinition

from .schemas import (
    DhcpObjectType,
    DhcpServiceCreate,
    DhcpServiceRead,
    DhcpServiceUpdate,
)
from .service import DhcpService
from .routes import router


class DhcpPlugin(Plugin):
    """
    DHCP configuration management plugin.
    
    Provides management of DHCP services, subnets, pools, hosts, and related
    objects in the LDAP directory.
    
    Object Types:
        - service: Root DHCP service configuration (dhcpService)
        - shared-network: Shared network config (dhcpSharedNetwork)
        - subnet: Subnet definition (dhcpSubnet)
        - pool: IP address pool (dhcpPool)
        - host: Host reservation (dhcpHost)
        - group: Host grouping (dhcpGroup)
        - class: Client classification (dhcpClass)
        - subclass: Subclass matching (dhcpSubClass)
        - tsig-key: TSIG key for DNS updates (dhcpTSigKey)
        - dns-zone: DNS zone for dynamic updates (dhcpDnsZone)
        - failover-peer: Failover configuration (dhcpFailOverPeer)
    
    Hierarchy:
        dhcpService (root)
        ├── dhcpSharedNetwork
        │   └── dhcpSubnet
        │       └── dhcpPool, dhcpHost
        ├── dhcpSubnet
        │   └── dhcpPool, dhcpHost, dhcpGroup
        ├── dhcpGroup → dhcpHost
        ├── dhcpClass → dhcpSubClass
        ├── dhcpHost
        ├── dhcpTSigKey
        ├── dhcpDnsZone
        └── dhcpFailOverPeer
    
    Integration:
        Optional integration with 'systems' plugin for host validation.
        When systems plugin is available, DHCP hosts can reference system entries.
    """
    
    @staticmethod
    def info() -> PluginInfo:
        """Return plugin metadata."""
        return PluginInfo(
            name="dhcp",
            version="1.0.0",
            description="DHCP configuration management (services, subnets, pools, hosts)",
            author="Heracles Team",
            object_types=[
                "dhcp-service",
                "dhcp-shared-network",
                "dhcp-subnet",
                "dhcp-pool",
                "dhcp-host",
                "dhcp-group",
                "dhcp-class",
                "dhcp-subclass",
                "dhcp-tsig-key",
                "dhcp-dns-zone",
                "dhcp-failover-peer",
            ],
            object_classes=[
                "dhcpService",
                "dhcpSharedNetwork",
                "dhcpSubnet",
                "dhcpPool",
                "dhcpHost",
                "dhcpGroup",
                "dhcpClass",
                "dhcpSubClass",
                "dhcpTSigKey",
                "dhcpDnsZone",
                "dhcpFailOverPeer",
            ],
            dependencies=[],  # No hard dependencies
            optional_dependencies=["systems"],  # For host validation
            required_config=[],
            priority=20,  # After systems (priority 15)
        )
    
    @staticmethod
    def tabs() -> List[TabDefinition]:
        """
        Define tabs provided by this plugin.
        
        DHCP is a management plugin (standalone objects), not a tab plugin.
        Returns an empty list.
        
        Future: Could provide a DHCP tab on systems to show/manage
        DHCP reservations for that system.
        """
        return []
    
    @staticmethod
    def routes() -> List[Any]:
        """
        Return FastAPI routers provided by this plugin.
        
        Returns:
            List containing the DHCP router with all endpoints.
        """
        return [router]
    
    @staticmethod
    def service_class():
        """Return the service class for this plugin."""
        return DhcpService
    
    @staticmethod
    def on_load(registry: Any) -> None:
        """
        Called when the plugin is loaded.
        
        Sets up integration with the systems plugin if available.
        """
        # Try to integrate with systems plugin
        systems_service = registry.get_service("systems")
        dhcp_service = registry.get_service("dhcp")
        
        if systems_service and dhcp_service:
            dhcp_service.set_systems_service(systems_service)
