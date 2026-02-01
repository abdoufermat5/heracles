"""
DHCP Plugin Definition
======================

Main plugin class that registers DHCP configuration management functionality.
"""

from typing import Any, Dict, List, Optional

from heracles_api.plugins.base import (
    ConfigField,
    ConfigFieldOption,
    ConfigFieldType,
    ConfigFieldValidation,
    ConfigSection,
    Plugin,
    PluginInfo,
    TabDefinition,
)

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
    
    Configuration:
        - dhcp_rdn: Base RDN for DHCP entries (default: cn=dhcp)
        - default_lease_time: Default lease time in seconds
        - max_lease_time: Maximum lease time in seconds
        - validate_mac_addresses: Enable MAC address format validation
        - validate_system_references: Validate host references against systems
        - authoritative: Whether DHCP server is authoritative
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
    def config_schema() -> List[ConfigSection]:
        """
        Define configuration schema for DHCP plugin.
        
        Returns:
            List of configuration sections with fields.
        """
        return [
            ConfigSection(
                id="general",
                label="General Settings",
                description="Basic DHCP plugin configuration",
                fields=[
                    ConfigField(
                        key="dhcp_rdn",
                        label="DHCP RDN",
                        description="Base RDN for DHCP entries in LDAP",
                        field_type=ConfigFieldType.STRING,
                        default_value="cn=dhcp",
                        required=True,
                        requires_restart=True,
                        validation=ConfigFieldValidation(
                            pattern=r"^[a-z]+=.+$",
                        ),
                    ),
                    ConfigField(
                        key="authoritative",
                        label="Authoritative",
                        description="Whether the DHCP server is authoritative for the network",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=True,
                    ),
                ],
            ),
            ConfigSection(
                id="lease_times",
                label="Lease Times",
                description="Default and maximum lease time settings",
                fields=[
                    ConfigField(
                        key="default_lease_time",
                        label="Default Lease Time",
                        description="Default lease time in seconds",
                        field_type=ConfigFieldType.INTEGER,
                        default_value=86400,  # 24 hours
                        validation=ConfigFieldValidation(
                            min_value=300,  # 5 minutes minimum
                            max_value=31536000,  # 1 year maximum
                        ),
                    ),
                    ConfigField(
                        key="max_lease_time",
                        label="Maximum Lease Time",
                        description="Maximum lease time in seconds",
                        field_type=ConfigFieldType.INTEGER,
                        default_value=604800,  # 7 days
                        validation=ConfigFieldValidation(
                            min_value=300,
                            max_value=31536000,
                        ),
                    ),
                    ConfigField(
                        key="min_lease_time",
                        label="Minimum Lease Time",
                        description="Minimum lease time in seconds (0 to disable)",
                        field_type=ConfigFieldType.INTEGER,
                        default_value=0,
                        validation=ConfigFieldValidation(
                            min_value=0,
                            max_value=86400,
                        ),
                    ),
                ],
            ),
            ConfigSection(
                id="validation",
                label="Validation",
                description="Input validation settings",
                fields=[
                    ConfigField(
                        key="validate_mac_addresses",
                        label="Validate MAC Addresses",
                        description="Enable strict MAC address format validation",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=True,
                    ),
                    ConfigField(
                        key="validate_ip_ranges",
                        label="Validate IP Ranges",
                        description="Validate IP address ranges in pools and subnets",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=True,
                    ),
                    ConfigField(
                        key="validate_system_references",
                        label="Validate System References",
                        description="Validate DHCP host references against systems plugin",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=False,
                    ),
                ],
            ),
            ConfigSection(
                id="failover",
                label="Failover Settings",
                description="DHCP failover peer configuration defaults",
                fields=[
                    ConfigField(
                        key="failover_split",
                        label="Failover Split",
                        description="Default address split for failover (0-256, where 128 is 50/50)",
                        field_type=ConfigFieldType.INTEGER,
                        default_value=128,
                        validation=ConfigFieldValidation(
                            min_value=0,
                            max_value=256,
                        ),
                    ),
                    ConfigField(
                        key="mclt",
                        label="MCLT",
                        description="Maximum Client Lead Time in seconds",
                        field_type=ConfigFieldType.INTEGER,
                        default_value=3600,
                        validation=ConfigFieldValidation(
                            min_value=60,
                            max_value=86400,
                        ),
                    ),
                ],
            ),
            ConfigSection(
                id="dns_updates",
                label="Dynamic DNS",
                description="Dynamic DNS update settings",
                fields=[
                    ConfigField(
                        key="ddns_update_style",
                        label="DDNS Update Style",
                        description="Dynamic DNS update method",
                        field_type=ConfigFieldType.SELECT,
                        default_value="none",
                        options=[
                            ConfigFieldOption(value="none", label="Disabled"),
                            ConfigFieldOption(value="interim", label="Interim (ISC DHCP)"),
                            ConfigFieldOption(value="standard", label="Standard (RFC 2136)"),
                        ],
                    ),
                    ConfigField(
                        key="ddns_domainname",
                        label="DDNS Domain Name",
                        description="Default domain name for dynamic DNS updates",
                        field_type=ConfigFieldType.STRING,
                        default_value="",
                    ),
                    ConfigField(
                        key="ddns_rev_domainname",
                        label="DDNS Reverse Domain",
                        description="Reverse domain name for PTR updates",
                        field_type=ConfigFieldType.STRING,
                        default_value="in-addr.arpa.",
                    ),
                ],
            ),
        ]
    
    @staticmethod
    def default_config() -> Dict[str, Any]:
        """
        Return default configuration values.
        
        Returns:
            Dictionary of default configuration values.
        """
        return {
            # General
            "dhcp_rdn": "cn=dhcp",
            "authoritative": True,
            # Lease times
            "default_lease_time": 86400,
            "max_lease_time": 604800,
            "min_lease_time": 0,
            # Validation
            "validate_mac_addresses": True,
            "validate_ip_ranges": True,
            "validate_system_references": False,
            # Failover
            "failover_split": 128,
            "mclt": 3600,
            # DNS updates
            "ddns_update_style": "none",
            "ddns_domainname": "",
            "ddns_rev_domainname": "in-addr.arpa.",
        }
    
    @staticmethod
    def validate_config_business_rules(config: Dict[str, Any]) -> Optional[str]:
        """
        Validate configuration business rules.
        
        Args:
            config: Configuration dictionary to validate.
            
        Returns:
            Error message if validation fails, None otherwise.
        """
        # Validate lease time relationships
        default_lease = config.get("default_lease_time", 86400)
        max_lease = config.get("max_lease_time", 604800)
        min_lease = config.get("min_lease_time", 0)
        
        if default_lease > max_lease:
            return "Default lease time cannot exceed maximum lease time"
        
        if min_lease > 0 and min_lease > default_lease:
            return "Minimum lease time cannot exceed default lease time"
        
        # Validate failover split
        failover_split = config.get("failover_split", 128)
        if failover_split < 0 or failover_split > 256:
            return "Failover split must be between 0 and 256"
        
        return None
    
    @staticmethod
    def on_config_change(old_config: Dict[str, Any], new_config: Dict[str, Any]) -> None:
        """
        Handle configuration changes.
        
        Args:
            old_config: Previous configuration.
            new_config: New configuration.
        """
        # Log significant configuration changes
        if old_config.get("dhcp_rdn") != new_config.get("dhcp_rdn"):
            # RDN change requires service restart
            pass
        
        if old_config.get("authoritative") != new_config.get("authoritative"):
            # Authoritative flag change may affect DHCP behavior
            pass
    
    def on_activate(self) -> None:
        """Called when the plugin is activated."""
        # Load configuration using base class method
        self._dhcp_rdn = self.get_config_value("dhcp_rdn", "cn=dhcp")
    
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
