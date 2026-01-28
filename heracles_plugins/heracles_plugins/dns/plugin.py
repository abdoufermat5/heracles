"""
DNS Plugin Definition
=====================

Main plugin class that registers DNS zone and record management functionality.
"""

from typing import Any, List

from heracles_api.plugins.base import Plugin, PluginInfo, TabDefinition

from .schemas import (
    DnsZoneCreate,
    DnsZoneRead,
    DnsZoneUpdate,
)
from .service import DnsService
from .router import router


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
        dns_rdn = self._config.get("dns_rdn", "ou=dns")
        default_ttl = self._config.get("default_ttl", 3600)
        self.logger.info(
            f"DNS plugin activated (DNS RDN: {dns_rdn}, default TTL: {default_ttl})"
        )

    def on_deactivate(self) -> None:
        """Called when plugin is deactivated."""
        self.logger.info("DNS plugin deactivated")

    @staticmethod
    def routes() -> List[Any]:
        """Return API routers for DNS endpoints."""
        return [router]
