"""
DNS Plugin
==========

DNS zone and record management for Heracles.

This plugin provides:
    - DNS zone management (forward and reverse zones)
    - DNS record management (A, AAAA, MX, NS, CNAME, PTR, TXT, SRV)
    - Automatic SOA serial management
    - Standard dnszone.schema LDAP compatibility

Usage:
    Enable the plugin in configuration:
        PLUGINS_ENABLED=["posix", "systems", "dns"]

    API endpoints:
        GET    /api/v1/dns/zones              - List all zones
        POST   /api/v1/dns/zones              - Create a zone
        GET    /api/v1/dns/zones/{zone}       - Get zone details
        PUT    /api/v1/dns/zones/{zone}       - Update zone SOA
        DELETE /api/v1/dns/zones/{zone}       - Delete zone

        GET    /api/v1/dns/zones/{zone}/records           - List records
        POST   /api/v1/dns/zones/{zone}/records           - Create record
        PUT    /api/v1/dns/zones/{zone}/records/{n}/{t}   - Update record
        DELETE /api/v1/dns/zones/{zone}/records/{n}/{t}   - Delete record
"""

from .plugin import DnsPlugin
from .service import DnsService
from .schemas import (
    RecordType,
    ZoneType,
    SoaRecord,
    DnsZoneCreate,
    DnsZoneRead,
    DnsZoneUpdate,
    DnsZoneListItem,
    DnsZoneListResponse,
    DnsRecordCreate,
    DnsRecordRead,
    DnsRecordUpdate,
    DnsRecordListItem,
)
from .routes import router

__plugin__ = DnsPlugin

__all__ = [
    # Plugin
    "DnsPlugin",
    "__plugin__",
    # Service
    "DnsService",
    # Enums
    "RecordType",
    "ZoneType",
    # Schemas
    "SoaRecord",
    "DnsZoneCreate",
    "DnsZoneRead",
    "DnsZoneUpdate",
    "DnsZoneListItem",
    "DnsZoneListResponse",
    "DnsRecordCreate",
    "DnsRecordRead",
    "DnsRecordUpdate",
    "DnsRecordListItem",
    # Router
    "router",
]
