"""
DNS Service
===========

Business logic for DNS zone and record management.
Handles LDAP operations for the dNSZone objectClass.

This service is composed of:
- DnsServiceBase: Common functionality (DN building, OU management)
- ZoneOperationsMixin: Zone CRUD operations
- RecordOperationsMixin: Record CRUD operations and validation
"""

from typing import Any, Dict, Optional

import structlog

from heracles_api.plugins.base import TabService
from heracles_api.services.ldap_service import LdapService

from ..schemas import (
    DnsZoneCreate,
    DnsZoneRead,
    DnsZoneUpdate,
)
from .base import DnsServiceBase, DnsValidationError
from .constants import MANAGED_ATTRIBUTES
from .operations import ZoneOperationsMixin, RecordOperationsMixin

logger = structlog.get_logger(__name__)

# Re-export DnsValidationError for backward compatibility
__all__ = ["DnsService", "DnsValidationError"]


class DnsService(
    ZoneOperationsMixin,
    RecordOperationsMixin,
    DnsServiceBase,
    TabService,
):
    """
    Service for managing DNS zones and records in LDAP.

    Uses the dNSZone objectClass with standard DNS attributes.

    Directory structure:
        ou=dns,dc=example,dc=org                    # DNS container
        └── zoneName=example.org,ou=dns,...         # Zone entry (@ records, SOA, NS)
            │                                       # Has relativeDomainName=@ as attribute
            ├── relativeDomainName=www,...          # www.example.org
            ├── relativeDomainName=mail,...         # mail.example.org
            ├── relativeDomainName=_sip._tcp,...    # SRV record
            └── zoneName=168.192.in-addr.arpa,...   # Reverse zone (nested)
    
    Composed of:
        - DnsServiceBase: DN building, OU management
        - ZoneOperationsMixin: Zone CRUD operations
        - RecordOperationsMixin: Record CRUD operations + validation
        - TabService: Plugin tab interface
    """

    def __init__(self, ldap_service: LdapService, config: Dict[str, Any]):
        # Initialize base classes
        DnsServiceBase.__init__(self, ldap_service, config)
        TabService.__init__(self, ldap_service, config)

    # ========================================================================
    # TabService Abstract Method Implementations
    # ========================================================================

    async def is_active(self, dn: str) -> bool:
        """Check if a DNS zone entry exists at the given DN."""
        try:
            entry = await self._ldap.get_by_dn(dn, attributes=["objectClass"])
            if entry is None:
                return False

            object_classes = {oc.lower() for oc in entry.get("objectClass", [])}
            return "dnszone" in object_classes
        except Exception:
            return False

    async def read(self, dn: str) -> Optional[DnsZoneRead]:
        """Read a zone by DN."""
        try:
            entry = await self._ldap.get_by_dn(
                dn,
                attributes=MANAGED_ATTRIBUTES + ["objectClass"]
            )
            if entry is None:
                return None

            return await self._entry_to_zone_read(entry)
        except Exception:
            return None

    async def activate(self, dn: str, data: DnsZoneCreate) -> DnsZoneRead:
        """Create a zone."""
        return await self.create_zone(data)

    async def update(self, dn: str, data: DnsZoneUpdate) -> DnsZoneRead:
        """Update a zone by DN."""
        # Extract zone name from DN
        # DN format: zoneName=example.org,ou=dns,dc=... 
        zone_name = self._extract_zone_name_from_dn(dn)
        if not zone_name:
            raise DnsValidationError(f"Could not extract zone name from DN: {dn}")

        return await self.update_zone(zone_name, data)

    async def deactivate(self, dn: str) -> None:
        """Delete a zone by DN."""
        # Extract zone name from DN
        zone_name = self._extract_zone_name_from_dn(dn)
        if not zone_name:
            raise DnsValidationError(f"Could not extract zone name from DN: {dn}")

        await self.delete_zone(zone_name)

    def _extract_zone_name_from_dn(self, dn: str) -> Optional[str]:
        """Extract zone name from DN."""
        # DN format: zoneName=example.org,ou=dns,dc=... 
        parts = dn.split(",")
        for part in parts:
            if part.startswith("zoneName="):
                return part.split("=", 1)[1]
        return None
