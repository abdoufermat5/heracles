"""
DNS Plugin Definition
=====================

Main plugin class that registers DNS zone and record management functionality.
"""

from typing import Any, Dict, List

from heracles_api.plugins.base import (
    Plugin,
    PluginInfo,
    TabDefinition,
    ConfigSection,
    ConfigField,
    ConfigFieldType,
    ConfigFieldValidation,
    ConfigFieldOption,
)

from .schemas import (
    DnsZoneCreate,
    DnsZoneRead,
    DnsZoneUpdate,
)
from .service import DnsService
from .routes import router


class DnsPlugin(Plugin):
    """
    DNS management plugin.

    Provides management of DNS zones and records in the LDAP directory
    using the standard dNSZone objectClass.

    Features:
        - Forward and reverse zone management
        - Support for common record types (A, AAAA, MX, NS, CNAME, PTR, TXT, SRV)
        - Automatic SOA serial management
        - Standard dnszone.schema compatibility

    Zone Types:
        - forward: Standard forward lookup zone (e.g., example.org)
        - reverse-ipv4: Reverse zone for IPv4 (e.g., 168.192.in-addr.arpa)
        - reverse-ipv6: Reverse zone for IPv6 (e.g., 8.b.d.0.1.0.0.2.ip6.arpa)

    Directory Structure:
        ou=dns,dc=example,dc=org                    # DNS container
        └── zoneName=example.org,ou=dns,...         # Zone entry (SOA, @ records)
            ├── relativeDomainName=www,...          # www.example.org
            ├── relativeDomainName=mail,...         # mail.example.org
            └── relativeDomainName=_sip._tcp,...    # SRV record
    """

    @staticmethod
    def info() -> PluginInfo:
        """Return plugin metadata."""
        return PluginInfo(
            name="dns",
            version="1.0.0",
            description="DNS zone and record management",
            author="Heracles Team",
            object_types=[
                "dns-zone",
            ],
            object_classes=[
                "dNSZone",
            ],
            dependencies=[],  # No dependencies
            optional_dependencies=["systems"],  # For future dnsHost integration
            required_config=[],
            priority=30,  # Load after systems plugin
        )
    
    @staticmethod
    def config_schema() -> List[ConfigSection]:
        """Define DNS plugin configuration schema."""
        return [
            ConfigSection(
                id="general",
                label="General Settings",
                description="General DNS configuration options",
                icon="globe",
                order=10,
                fields=[
                    ConfigField(
                        key="dns_rdn",
                        label="DNS RDN",
                        field_type=ConfigFieldType.STRING,
                        default_value="ou=dns",
                        description="Relative DN where DNS zones are stored",
                        validation=ConfigFieldValidation(
                            required=True,
                            pattern=r"^ou=[a-zA-Z0-9_-]+$",
                        ),
                    ),
                    ConfigField(
                        key="final_dot",
                        label="Store Final Dot",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=True,
                        description="Store trailing dot in zone names (e.g., example.org.)",
                    ),
                ],
            ),
            ConfigSection(
                id="defaults",
                label="Default Values",
                description="Default values for new DNS zones",
                icon="settings",
                order=20,
                fields=[
                    ConfigField(
                        key="default_ttl",
                        label="Default TTL",
                        field_type=ConfigFieldType.INTEGER,
                        default_value=3600,
                        description="Default Time-To-Live in seconds for new records",
                        validation=ConfigFieldValidation(
                            required=True,
                            min_value=60,
                            max_value=604800,  # 1 week
                        ),
                    ),
                    ConfigField(
                        key="default_refresh",
                        label="SOA Refresh",
                        field_type=ConfigFieldType.INTEGER,
                        default_value=10800,
                        description="SOA refresh interval in seconds (default: 3 hours)",
                        validation=ConfigFieldValidation(
                            required=True,
                            min_value=300,
                            max_value=86400,
                        ),
                    ),
                    ConfigField(
                        key="default_retry",
                        label="SOA Retry",
                        field_type=ConfigFieldType.INTEGER,
                        default_value=3600,
                        description="SOA retry interval in seconds (default: 1 hour)",
                        validation=ConfigFieldValidation(
                            required=True,
                            min_value=60,
                            max_value=86400,
                        ),
                    ),
                    ConfigField(
                        key="default_expire",
                        label="SOA Expire",
                        field_type=ConfigFieldType.INTEGER,
                        default_value=604800,
                        description="SOA expire time in seconds (default: 1 week)",
                        validation=ConfigFieldValidation(
                            required=True,
                            min_value=3600,
                            max_value=2419200,  # 4 weeks
                        ),
                    ),
                    ConfigField(
                        key="default_minimum",
                        label="SOA Minimum TTL",
                        field_type=ConfigFieldType.INTEGER,
                        default_value=3600,
                        description="SOA minimum/negative TTL in seconds",
                        validation=ConfigFieldValidation(
                            required=True,
                            min_value=60,
                            max_value=86400,
                        ),
                    ),
                ],
            ),
            ConfigSection(
                id="serial",
                label="Serial Number",
                description="SOA serial number format configuration",
                icon="hash",
                order=30,
                fields=[
                    ConfigField(
                        key="serial_format",
                        label="Serial Format",
                        field_type=ConfigFieldType.SELECT,
                        default_value="date",
                        description="Format for generating SOA serial numbers",
                        options=[
                            ConfigFieldOption("date", "Date-based (YYYYMMDDnn)"),
                            ConfigFieldOption("increment", "Simple increment"),
                            ConfigFieldOption("timestamp", "Unix timestamp"),
                        ],
                    ),
                    ConfigField(
                        key="auto_increment_serial",
                        label="Auto-increment Serial",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=True,
                        description="Automatically increment SOA serial on record changes",
                    ),
                ],
            ),
        ]
    
    @staticmethod
    def default_config() -> Dict[str, Any]:
        """Return default configuration values."""
        return {
            "dns_rdn": "ou=dns",
            "final_dot": True,
            "default_ttl": 3600,
            "default_refresh": 10800,
            "default_retry": 3600,
            "default_expire": 604800,
            "default_minimum": 3600,
            "serial_format": "date",
            "auto_increment_serial": True,
        }
    
    def validate_config_business_rules(self, config: Dict[str, Any]) -> List[str]:
        """Custom business rule validation for DNS config."""
        errors = []
        
        # SOA timing validation (RFC 1912 recommendations)
        refresh = config.get("default_refresh", 10800)
        retry = config.get("default_retry", 3600)
        expire = config.get("default_expire", 604800)
        
        if retry >= refresh:
            errors.append("SOA retry should be less than refresh")
        
        if expire <= refresh:
            errors.append("SOA expire should be greater than refresh")
        
        return errors

    @staticmethod
    def tabs() -> List[TabDefinition]:
        """
        Define tabs provided by this plugin.

        DNS is a management plugin - it manages standalone zone objects.
        """
        return [
            TabDefinition(
                id="dns",
                label="DNS",
                icon="globe",
                object_type="dns-zone",
                activation_filter="(objectClass=dNSZone)",
                schema_file=None,
                service_class=DnsService,
                create_schema=DnsZoneCreate,
                read_schema=DnsZoneRead,
                update_schema=DnsZoneUpdate,
                required=True,
            ),
        ]

    def on_activate(self) -> None:
        """Called when plugin is activated."""
        dns_rdn = self.get_config_value("dns_rdn", "ou=dns")
        default_ttl = self.get_config_value("default_ttl", 3600)
        self.logger.info(
            f"DNS plugin activated (DNS RDN: {dns_rdn}, default TTL: {default_ttl})"
        )

    def on_deactivate(self) -> None:
        """Called when plugin is deactivated."""
        self.logger.info("DNS plugin deactivated")
    
    def on_config_change(
        self,
        old_config: Dict[str, Any],
        new_config: Dict[str, Any],
        changed_keys: List[str],
    ) -> None:
        """Handle configuration changes at runtime."""
        self.logger.info(
            f"DNS plugin configuration updated",
            changed_keys=changed_keys,
        )
    
    @staticmethod
    def routes() -> List[Any]:
        """Return API routers for DNS endpoints."""
        return [router]

    @staticmethod
    def routes() -> List[Any]:
        """Return API routers for DNS endpoints."""
        return [router]
