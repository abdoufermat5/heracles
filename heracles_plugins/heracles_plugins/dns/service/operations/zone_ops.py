"""
DNS Zone Operations Mixin
=========================

Zone CRUD operations for DNS service.
"""

from typing import List, Optional

import structlog

from heracles_api.services.ldap_service import (
    LdapEntry,
    LdapOperationError,
    LdapNotFoundError,
)

from ...schemas import (
    SoaRecord,
    DnsZoneCreate,
    DnsZoneRead,
    DnsZoneUpdate,
    DnsZoneListItem,
    DnsZoneListResponse,
    detect_zone_type,
    generate_serial,
    increment_serial,
)
from ..constants import OBJECT_CLASSES, DNS_CLASS, MANAGED_ATTRIBUTES
from ..utils import get_first_value
from ..base import DnsValidationError

logger = structlog.get_logger(__name__)


class ZoneOperationsMixin:
    """Mixin providing DNS zone CRUD operations."""

    # ========================================================================
    # Zone List Operations
    # ========================================================================

    async def list_zones(self, base_dn: Optional[str] = None) -> DnsZoneListResponse:
        """
        List all DNS zones.

        Returns:
            DnsZoneListResponse with all zones
        """
        try:
            # Get the DNS container for the given context
            search_base = self._get_dns_container(base_dn)
            
            # Ensure container exists (only for root context)
            if not base_dn:
                await self._ensure_dns_ou()

            # Search for zone entries (relativeDomainName=@ entries are zone roots)
            entries = await self._ldap.search(
                search_base=search_base,
                search_filter="(&(objectClass=dNSZone)(relativeDomainName=@))",
                attributes=["zoneName", "relativeDomainName", "sOARecord", "dNSTTL"],
            )

            zones = []
            for entry in entries:
                zone_name = get_first_value(entry, "zoneName")
                if not zone_name:
                    continue

                # Count records for this zone
                record_count = await self._count_zone_records(zone_name)

                zones.append(DnsZoneListItem(
                    dn=entry.dn if hasattr(entry, 'dn') else entry.get("dn", ""),
                    zone_name=zone_name,
                    zone_type=detect_zone_type(zone_name),
                    record_count=record_count,
                ))

            # Sort by zone name
            zones.sort(key=lambda z: z.zone_name)

            return DnsZoneListResponse(
                zones=zones,
                total=len(zones),
            )

        except LdapOperationError as e:
            logger.error("list_zones_failed", error=str(e))
            raise

    async def _count_zone_records(self, zone_name: str, base_dn: Optional[str] = None) -> int:
        """Count records in a zone (excluding the @ entry)."""
        try:
            zone_dn = self._get_zone_dn(zone_name, base_dn=base_dn)
            entries = await self._ldap.search(
                search_base=zone_dn,
                search_filter="(objectClass=dNSZone)",
                attributes=["relativeDomainName"],
            )
            # Count entries (including @ which has records)
            return len(entries)
        except LdapOperationError:
            return 0

    # ========================================================================
    # Zone Get Operations
    # ========================================================================

    async def get_zone(
        self, 
        zone_name: str,
        base_dn: Optional[str] = None
    ) -> Optional[DnsZoneRead]:
        """
        Get a single zone by name.
        
        with relativeDomainName=@ as an attribute.
        """
        zone_name = zone_name.lower()
        dn = self._get_zone_dn(zone_name, base_dn=base_dn)

        try:
            entry = await self._ldap.get_by_dn(
                dn,
                attributes=MANAGED_ATTRIBUTES + ["objectClass"]
            )
            if entry is None:
                return None
            
            # Verify it has relativeDomainName=@ (zone apex indicator)
            rel_domain = get_first_value(entry, "relativeDomainName")
            if rel_domain != "@":
                return None
            
            return await self._entry_to_zone_read(entry, base_dn=base_dn)

        except LdapOperationError:
            return None

    async def _entry_to_zone_read(
        self, 
        entry: LdapEntry,
        base_dn: Optional[str] = None
    ) -> DnsZoneRead:
        """Convert LDAP entry to DnsZoneRead."""
        zone_name = get_first_value(entry, "zoneName")
        soa_string = get_first_value(entry, "sOARecord")
        ttl_str = get_first_value(entry, "dNSTTL")

        if not zone_name or not soa_string:
            raise DnsValidationError("Invalid zone entry: missing zoneName or SOA")

        soa = SoaRecord.from_soa_string(soa_string)
        default_ttl = int(ttl_str) if ttl_str else self._default_ttl
        record_count = await self._count_zone_records(zone_name, base_dn=base_dn)

        return DnsZoneRead(
            dn=entry.dn if hasattr(entry, 'dn') else entry.get("dn", ""),
            zone_name=zone_name,
            zone_type=detect_zone_type(zone_name),
            soa=soa,
            default_ttl=default_ttl,
            record_count=record_count,
        )

    # ========================================================================
    # Zone Create Operations
    # ========================================================================

    async def create_zone(
        self, 
        data: DnsZoneCreate,
        base_dn: Optional[str] = None
    ) -> DnsZoneRead:
        """
        Create a new DNS zone.

        Creates the zone container and the @ (apex) record with SOA.
        """
        # Ensure base structure exists if we are in default mode
        if not base_dn:
            await self._ensure_dns_ou()

        zone_name = data.zone_name.lower()

        # Check if zone already exists
        existing = await self.get_zone(zone_name, base_dn=base_dn)
        if existing:
            raise DnsValidationError(f"Zone '{zone_name}' already exists")

        # Generate initial serial
        serial = generate_serial()

        # Build SOA record string
        soa = SoaRecord(
            primary_ns=data.soa_primary_ns,
            admin_email=data.soa_admin_email,
            serial=serial,
            refresh=data.soa_refresh,
            retry=data.soa_retry,
            expire=data.soa_expire,
            minimum=data.soa_minimum,
        )

        # Create the zone apex entry (@ record)
        dn = self._get_zone_dn(zone_name, base_dn=base_dn)

        attributes = {
            "zoneName": [zone_name],
            "relativeDomainName": ["@"],
            "dNSTTL": [str(data.default_ttl)],
            "dNSClass": [DNS_CLASS],
            "sOARecord": [soa.to_soa_string()],
        }

        try:
            await self._ldap.add(
                dn=dn,
                object_classes=OBJECT_CLASSES,
                attributes=attributes,
            )

            logger.info(
                "zone_created",
                zone_name=zone_name,
                dn=dn
            )

            return await self.get_zone(zone_name, base_dn=base_dn)

        except LdapOperationError as e:
            logger.error(
                "zone_create_failed",
                zone_name=zone_name,
                error=str(e)
            )
            raise DnsValidationError(f"Failed to create zone: {e}")

    # ========================================================================
    # Zone Update Operations
    # ========================================================================

    async def update_zone(
        self, 
        zone_name: str, 
        data: DnsZoneUpdate,
        base_dn: Optional[str] = None
    ) -> DnsZoneRead:
        """Update a DNS zone (SOA parameters)."""
        zone_name = zone_name.lower()

        # Get existing zone
        existing = await self.get_zone(zone_name, base_dn=base_dn)
        if not existing:
            raise LdapNotFoundError(f"Zone '{zone_name}' not found")

        dn = self._get_zone_dn(zone_name, base_dn=base_dn)

        # Build updated SOA
        soa = existing.soa
        new_soa = SoaRecord(
            primary_ns=data.soa_primary_ns or soa.primary_ns,
            admin_email=data.soa_admin_email or soa.admin_email,
            serial=increment_serial(soa.serial),  # Auto-increment on update
            refresh=data.soa_refresh if data.soa_refresh is not None else soa.refresh,
            retry=data.soa_retry if data.soa_retry is not None else soa.retry,
            expire=data.soa_expire if data.soa_expire is not None else soa.expire,
            minimum=data.soa_minimum if data.soa_minimum is not None else soa.minimum,
        )

        changes = {
            "sOARecord": ("replace", [new_soa.to_soa_string()]),
        }

        if data.default_ttl is not None:
            changes["dNSTTL"] = ("replace", [str(data.default_ttl)])

        try:
            await self._ldap.modify(dn, changes)
            logger.info(
                "zone_updated",
                zone_name=zone_name,
                new_serial=new_soa.serial
            )

            return await self.get_zone(zone_name, base_dn=base_dn)

        except LdapOperationError as e:
            logger.error(
                "zone_update_failed",
                zone_name=zone_name,
                error=str(e)
            )
            raise DnsValidationError(f"Failed to update zone: {e}")

    # ========================================================================
    # Zone Delete Operations
    # ========================================================================

    async def delete_zone(
        self, 
        zone_name: str,
        base_dn: Optional[str] = None
    ) -> None:
        """
        Delete a DNS zone and all its records.

        This deletes all record entries within the zone, then the zone itself.
        """
        zone_name = zone_name.lower()

        # Check exists
        existing = await self.get_zone(zone_name, base_dn=base_dn)
        if not existing:
            raise LdapNotFoundError(f"Zone '{zone_name}' not found")

        zone_dn = self._get_zone_dn(zone_name, base_dn=base_dn)

        try:
            # Find all entries in the zone
            entries = await self._ldap.search(
                search_base=zone_dn,
                search_filter="(objectClass=dNSZone)",
                attributes=["dn"],
            )

            # Delete all entries (children first, then parent)
            # Sort by DN length descending to delete children before parents
            dns = [e.dn if hasattr(e, 'dn') else e.get("dn", "") for e in entries]
            dns.sort(key=len, reverse=True)

            for entry_dn in dns:
                await self._ldap.delete(entry_dn)

            logger.info(
                "zone_deleted",
                zone_name=zone_name,
                entries_deleted=len(dns)
            )

        except LdapOperationError as e:
            logger.error(
                "zone_delete_failed",
                zone_name=zone_name,
                error=str(e)
            )
            raise DnsValidationError(f"Failed to delete zone: {e}")
