"""
DNS Service
===========

Business logic for DNS zone and record management.
Handles LDAP operations for the dNSZone objectClass.
"""

from typing import Any, Dict, List, Optional, Tuple

import structlog

from heracles_api.plugins.base import TabService
from heracles_api.services.ldap_service import (
    LdapService,
    LdapEntry,
    LdapOperationError,
    LdapNotFoundError,
)

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
    RECORD_TYPE_ATTRS,
    ATTR_RECORD_TYPES,
    detect_zone_type,
    generate_serial,
    increment_serial,
)

logger = structlog.get_logger(__name__)


class DnsValidationError(Exception):
    """Raised when DNS validation fails."""
    pass


class DnsService(TabService):
    """
    Service for managing DNS zones and records in LDAP.

    Uses the dNSZone objectClass with standard DNS attributes.
    Compatible with FusionDirectory DNS plugin structure.

    Directory structure:
        ou=dns,dc=example,dc=org                    # DNS container
        └── zoneName=example.org,ou=dns,...         # Zone entry (@ records, SOA, NS)
            │                                       # Has relativeDomainName=@ as attribute
            ├── relativeDomainName=www,...          # www.example.org
            ├── relativeDomainName=mail,...         # mail.example.org
            ├── relativeDomainName=_sip._tcp,...    # SRV record
            └── zoneName=168.192.in-addr.arpa,...   # Reverse zone (nested)
    """

    DNS_BASE_RDN = "ou=dns"
    OBJECT_CLASSES = ["dNSZone"]
    DNS_CLASS = "IN"

    # All DNS-related attributes we manage
    MANAGED_ATTRIBUTES = [
        "zoneName",
        "relativeDomainName",
        "dNSTTL",
        "dNSClass",
        "sOARecord",
        "aRecord",
        "aAAARecord",
        "mXRecord",
        "nSRecord",
        "cNAMERecord",
        "pTRRecord",
        "tXTRecord",
        "sRVRecord",
    ]

    def __init__(self, ldap_service: LdapService, config: Dict[str, Any]):
        super().__init__(ldap_service, config)

        # Configuration
        self._dns_rdn = config.get("dns_rdn", self.DNS_BASE_RDN)
        self._base_dn = config.get("base_dn", ldap_service.base_dn)
        self._dns_base_dn = f"{self._dns_rdn},{self._base_dn}"
        self._default_ttl = config.get("default_ttl", 3600)

    def _get_zone_dn(self, zone_name: str) -> str:
        """Get the DN for a zone entry (the @ apex record)."""
        return f"zoneName={zone_name},{self._dns_base_dn}"

    def _get_record_dn(self, zone_name: str, name: str) -> str:
        """
        Get the DN for a record entry.
        
        For FusionDirectory compatibility:
        - @ (apex) records are stored at the zone entry itself (zoneName=X,ou=dns,...)
        - Other records are children (relativeDomainName=www,zoneName=X,ou=dns,...)
        """
        zone_dn = self._get_zone_dn(zone_name)
        if name == "@":
            # Apex record is the zone entry itself
            return zone_dn
        return f"relativeDomainName={name},{zone_dn}"

    # ========================================================================
    # OU Management
    # ========================================================================

    async def _ensure_dns_ou(self) -> None:
        """Ensure the DNS OU exists."""
        try:
            exists = await self._ldap.get_by_dn(
                self._dns_base_dn,
                attributes=["ou"]
            )
            if exists is None:
                await self._ldap.add(
                    dn=self._dns_base_dn,
                    object_classes=["organizationalUnit"],
                    attributes={"ou": ["dns"]},
                )
                logger.info("dns_ou_created", dn=self._dns_base_dn)
        except LdapOperationError as e:
            logger.warning("dns_ou_check_failed", error=str(e))

    # ========================================================================
    # Zone Operations
    # ========================================================================

    async def list_zones(self) -> DnsZoneListResponse:
        """
        List all DNS zones.

        Returns:
            DnsZoneListResponse with all zones
        """
        try:
            await self._ensure_dns_ou()

            # Search for zone entries (relativeDomainName=@ entries are zone roots)
            entries = await self._ldap.search(
                search_base=self._dns_base_dn,
                search_filter="(&(objectClass=dNSZone)(relativeDomainName=@))",
                attributes=["zoneName", "relativeDomainName", "sOARecord", "dNSTTL"],
            )

            zones = []
            for entry in entries:
                zone_name = self._get_first_value(entry, "zoneName")
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

    async def _count_zone_records(self, zone_name: str) -> int:
        """Count records in a zone (excluding the @ entry)."""
        try:
            zone_dn = self._get_zone_dn(zone_name)
            entries = await self._ldap.search(
                search_base=zone_dn,
                search_filter="(objectClass=dNSZone)",
                attributes=["relativeDomainName"],
            )
            # Count entries (including @ which has records)
            return len(entries)
        except LdapOperationError:
            return 0

    async def get_zone(self, zone_name: str) -> Optional[DnsZoneRead]:
        """
        Get a single zone by name.
        
        FusionDirectory compatibility: Zone entry is at zoneName=X,ou=dns,...
        with relativeDomainName=@ as an attribute.
        """
        zone_name = zone_name.lower()
        dn = self._get_zone_dn(zone_name)

        try:
            entry = await self._ldap.get_by_dn(
                dn,
                attributes=self.MANAGED_ATTRIBUTES + ["objectClass"]
            )
            if entry is None:
                return None
            
            # Verify it has relativeDomainName=@ (zone apex indicator)
            rel_domain = self._get_first_value(entry, "relativeDomainName")
            if rel_domain != "@":
                return None

            return await self._entry_to_zone_read(entry)

        except LdapOperationError:
            return None

    async def _entry_to_zone_read(self, entry: LdapEntry) -> DnsZoneRead:
        """Convert LDAP entry to DnsZoneRead."""
        zone_name = self._get_first_value(entry, "zoneName")
        soa_string = self._get_first_value(entry, "sOARecord")
        ttl_str = self._get_first_value(entry, "dNSTTL")

        if not zone_name or not soa_string:
            raise DnsValidationError("Invalid zone entry: missing zoneName or SOA")

        soa = SoaRecord.from_soa_string(soa_string)
        default_ttl = int(ttl_str) if ttl_str else self._default_ttl
        record_count = await self._count_zone_records(zone_name)

        return DnsZoneRead(
            dn=entry.dn if hasattr(entry, 'dn') else entry.get("dn", ""),
            zone_name=zone_name,
            zone_type=detect_zone_type(zone_name),
            soa=soa,
            default_ttl=default_ttl,
            record_count=record_count,
        )

    async def create_zone(self, data: DnsZoneCreate) -> DnsZoneRead:
        """
        Create a new DNS zone.

        Creates the zone container and the @ (apex) record with SOA.
        """
        await self._ensure_dns_ou()

        zone_name = data.zone_name.lower()

        # Check if zone already exists
        existing = await self.get_zone(zone_name)
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
        # FusionDirectory compatibility: zone entry at zoneName=X,ou=dns,...
        # with relativeDomainName=@ as attribute (not in DN)
        dn = self._get_zone_dn(zone_name)

        attributes = {
            "zoneName": [zone_name],
            "relativeDomainName": ["@"],
            "dNSTTL": [str(data.default_ttl)],
            "dNSClass": [self.DNS_CLASS],
            "sOARecord": [soa.to_soa_string()],
        }

        try:
            await self._ldap.add(
                dn=dn,
                object_classes=self.OBJECT_CLASSES,
                attributes=attributes,
            )

            logger.info(
                "zone_created",
                zone_name=zone_name,
                dn=dn
            )

            return await self.get_zone(zone_name)

        except LdapOperationError as e:
            logger.error(
                "zone_create_failed",
                zone_name=zone_name,
                error=str(e)
            )
            raise DnsValidationError(f"Failed to create zone: {e}")

    async def update_zone(self, zone_name: str, data: DnsZoneUpdate) -> DnsZoneRead:
        """Update a DNS zone (SOA parameters)."""
        zone_name = zone_name.lower()

        # Get existing zone
        existing = await self.get_zone(zone_name)
        if not existing:
            raise LdapNotFoundError(f"Zone '{zone_name}' not found")

        dn = self._get_zone_dn(zone_name)

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

            return await self.get_zone(zone_name)

        except LdapOperationError as e:
            logger.error(
                "zone_update_failed",
                zone_name=zone_name,
                error=str(e)
            )
            raise DnsValidationError(f"Failed to update zone: {e}")

    async def delete_zone(self, zone_name: str) -> None:
        """
        Delete a DNS zone and all its records.

        This deletes all record entries within the zone, then the zone itself.
        """
        zone_name = zone_name.lower()

        # Check exists
        existing = await self.get_zone(zone_name)
        if not existing:
            raise LdapNotFoundError(f"Zone '{zone_name}' not found")

        zone_dn = self._get_zone_dn(zone_name)

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

    # ========================================================================
    # Record Operations
    # ========================================================================

    async def list_records(self, zone_name: str) -> List[DnsRecordListItem]:
        """
        List all records in a zone.

        Returns records from all relativeDomainName entries.
        """
        zone_name = zone_name.lower()

        # Verify zone exists
        zone = await self.get_zone(zone_name)
        if not zone:
            raise LdapNotFoundError(f"Zone '{zone_name}' not found")

        zone_dn = self._get_zone_dn(zone_name)

        try:
            entries = await self._ldap.search(
                search_base=zone_dn,
                search_filter="(objectClass=dNSZone)",
                attributes=self.MANAGED_ATTRIBUTES,
            )

            records = []
            for entry in entries:
                entry_records = self._extract_records_from_entry(entry)
                records.extend(entry_records)

            # Sort: @ first, then alphabetically by name, then by type
            def sort_key(r: DnsRecordListItem) -> Tuple[int, str, str]:
                name_priority = 0 if r.name == "@" else 1
                return (name_priority, r.name, r.record_type.value)

            records.sort(key=sort_key)

            return records

        except LdapOperationError as e:
            logger.error(
                "list_records_failed",
                zone_name=zone_name,
                error=str(e)
            )
            raise

    def _extract_records_from_entry(self, entry: LdapEntry) -> List[DnsRecordListItem]:
        """Extract all DNS records from an LDAP entry."""
        records = []
        dn = entry.dn if hasattr(entry, 'dn') else entry.get("dn", "")
        name = self._get_first_value(entry, "relativeDomainName") or "@"
        ttl_str = self._get_first_value(entry, "dNSTTL")
        ttl = int(ttl_str) if ttl_str else None

        # Check each record type attribute
        for record_type, attr_name in RECORD_TYPE_ATTRS.items():
            values = entry.get(attr_name, [])
            if isinstance(values, str):
                values = [values]

            for value in values:
                if not value:
                    continue

                # Parse priority for MX and SRV
                priority = None
                record_value = value

                if record_type == RecordType.MX:
                    # MX format: "priority target"
                    parts = value.split(None, 1)
                    if len(parts) == 2:
                        try:
                            priority = int(parts[0])
                            record_value = parts[1]
                        except ValueError:
                            pass

                elif record_type == RecordType.SRV:
                    # SRV format: "priority weight port target"
                    parts = value.split(None, 1)
                    if len(parts) >= 1:
                        try:
                            priority = int(parts[0])
                            record_value = parts[1] if len(parts) > 1 else ""
                        except ValueError:
                            pass

                records.append(DnsRecordListItem(
                    dn=dn,
                    name=name,
                    record_type=record_type,
                    value=record_value,
                    ttl=ttl,
                    priority=priority,
                ))

        return records

    async def create_record(
        self,
        zone_name: str,
        data: DnsRecordCreate
    ) -> DnsRecordRead:
        """
        Create a new DNS record.

        If the relativeDomainName entry doesn't exist, creates it.
        Otherwise, adds the record value to the existing entry.
        """
        zone_name = zone_name.lower()

        # Verify zone exists
        zone = await self.get_zone(zone_name)
        if not zone:
            raise LdapNotFoundError(f"Zone '{zone_name}' not found")

        # Validate record
        self._validate_record(data)

        name = data.name
        dn = self._get_record_dn(zone_name, name)

        # Build record value (with priority for MX/SRV)
        record_value = self._build_record_value(data)

        # Get LDAP attribute name for this record type
        attr_name = RECORD_TYPE_ATTRS[data.record_type]

        try:
            # Check if entry exists
            existing = await self._ldap.get_by_dn(
                dn,
                attributes=self.MANAGED_ATTRIBUTES
            )

            if existing:
                # Add record to existing entry
                changes = {
                    attr_name: ("add", [record_value]),
                }
                if data.ttl is not None:
                    changes["dNSTTL"] = ("replace", [str(data.ttl)])

                await self._ldap.modify(dn, changes)
            else:
                # Create new entry
                attributes = {
                    "zoneName": [zone_name],
                    "relativeDomainName": [name],
                    "dNSClass": [self.DNS_CLASS],
                    attr_name: [record_value],
                }
                if data.ttl is not None:
                    attributes["dNSTTL"] = [str(data.ttl)]

                await self._ldap.add(
                    dn=dn,
                    object_classes=self.OBJECT_CLASSES,
                    attributes=attributes,
                )

            # Increment zone serial
            await self._increment_zone_serial(zone_name)

            logger.info(
                "record_created",
                zone_name=zone_name,
                name=name,
                record_type=data.record_type.value,
            )

            return DnsRecordRead(
                dn=dn,
                name=name,
                record_type=data.record_type,
                value=data.value,
                ttl=data.ttl,
                priority=data.priority,
            )

        except LdapOperationError as e:
            logger.error(
                "record_create_failed",
                zone_name=zone_name,
                name=name,
                error=str(e)
            )
            raise DnsValidationError(f"Failed to create record: {e}")

    def _validate_record(self, data: DnsRecordCreate) -> None:
        """Validate record data based on type."""
        record_type = data.record_type
        value = data.value

        if record_type == RecordType.A:
            # Validate IPv4
            import re
            if not re.match(r"^(\d{1,3}\.){3}\d{1,3}$", value):
                raise DnsValidationError("Invalid IPv4 address format")
            octets = value.split(".")
            if not all(0 <= int(o) <= 255 for o in octets):
                raise DnsValidationError("Invalid IPv4 address")

        elif record_type == RecordType.AAAA:
            # Basic IPv6 validation
            import re
            if not (re.match(r"^[0-9a-fA-F:]+$", value) and "::" in value or ":" in value):
                raise DnsValidationError("Invalid IPv6 address format")

        elif record_type in [RecordType.MX, RecordType.SRV]:
            if data.priority is None:
                raise DnsValidationError(f"{record_type.value} records require priority")

        elif record_type == RecordType.CNAME:
            # CNAME must be an FQDN
            if not value:
                raise DnsValidationError("CNAME value cannot be empty")

    def _build_record_value(self, data: DnsRecordCreate) -> str:
        """Build the LDAP record value string."""
        if data.record_type == RecordType.MX:
            return f"{data.priority} {data.value}"
        elif data.record_type == RecordType.SRV:
            # SRV needs: priority weight port target
            # Assume value is "weight port target"
            return f"{data.priority} {data.value}"
        else:
            return data.value

    async def update_record(
        self,
        zone_name: str,
        name: str,
        record_type: str,
        old_value: str,
        data: DnsRecordUpdate
    ) -> DnsRecordRead:
        """
        Update a DNS record.

        Replaces an existing record value with a new one.
        """
        zone_name = zone_name.lower()

        # Parse record type
        try:
            rtype = RecordType(record_type)
        except ValueError:
            raise DnsValidationError(f"Invalid record type: {record_type}")

        # Verify zone exists
        zone = await self.get_zone(zone_name)
        if not zone:
            raise LdapNotFoundError(f"Zone '{zone_name}' not found")

        dn = self._get_record_dn(zone_name, name)
        attr_name = RECORD_TYPE_ATTRS[rtype]

        try:
            # Get existing entry
            entry = await self._ldap.get_by_dn(dn, attributes=self.MANAGED_ATTRIBUTES)
            if entry is None:
                raise LdapNotFoundError(f"Record entry '{name}' not found")

            # Build old and new values
            old_full_value = old_value
            if rtype == RecordType.MX and data.priority is not None:
                # Need to find the old MX record with matching target
                pass  # old_value should already be just the target

            new_value = data.value if data.value is not None else old_value
            new_priority = data.priority

            # For MX/SRV, rebuild the full value
            if rtype == RecordType.MX and new_priority is not None:
                new_full_value = f"{new_priority} {new_value}"
            elif rtype == RecordType.SRV and new_priority is not None:
                new_full_value = f"{new_priority} {new_value}"
            else:
                new_full_value = new_value

            # Find and replace the old value
            current_values = entry.get(attr_name, [])
            if isinstance(current_values, str):
                current_values = [current_values]

            # Find matching value
            found = False
            for i, cv in enumerate(current_values):
                # For MX/SRV, compare just the target part
                if rtype in [RecordType.MX, RecordType.SRV]:
                    parts = cv.split(None, 1)
                    cv_target = parts[1] if len(parts) > 1 else parts[0]
                    if cv_target == old_value or cv == old_value:
                        found = True
                        break
                elif cv == old_value:
                    found = True
                    break

            if not found:
                raise LdapNotFoundError(f"Record value '{old_value}' not found")

            # Build changes
            changes = {}
            if data.value is not None or data.priority is not None:
                # Delete old, add new
                changes[attr_name] = ("delete", [old_full_value])

            if data.ttl is not None:
                changes["dNSTTL"] = ("replace", [str(data.ttl)])

            if changes:
                await self._ldap.modify(dn, changes)

            # Add new value if changed
            if data.value is not None or data.priority is not None:
                add_changes = {
                    attr_name: ("add", [new_full_value]),
                }
                await self._ldap.modify(dn, add_changes)

            # Increment zone serial
            await self._increment_zone_serial(zone_name)

            logger.info(
                "record_updated",
                zone_name=zone_name,
                name=name,
                record_type=record_type,
            )

            return DnsRecordRead(
                dn=dn,
                name=name,
                record_type=rtype,
                value=new_value,
                ttl=data.ttl,
                priority=new_priority,
            )

        except LdapOperationError as e:
            logger.error(
                "record_update_failed",
                zone_name=zone_name,
                name=name,
                error=str(e)
            )
            raise DnsValidationError(f"Failed to update record: {e}")

    async def delete_record(
        self,
        zone_name: str,
        name: str,
        record_type: str,
        value: str
    ) -> None:
        """
        Delete a DNS record.

        If this is the last record in the entry, deletes the entry.
        Otherwise, just removes the record value.
        """
        zone_name = zone_name.lower()

        # Parse record type
        try:
            rtype = RecordType(record_type)
        except ValueError:
            raise DnsValidationError(f"Invalid record type: {record_type}")

        # Verify zone exists
        zone = await self.get_zone(zone_name)
        if not zone:
            raise LdapNotFoundError(f"Zone '{zone_name}' not found")

        dn = self._get_record_dn(zone_name, name)
        attr_name = RECORD_TYPE_ATTRS[rtype]

        try:
            # Get existing entry
            entry = await self._ldap.get_by_dn(dn, attributes=self.MANAGED_ATTRIBUTES)
            if entry is None:
                raise LdapNotFoundError(f"Record entry '{name}' not found")

            # Check if this is the @ entry (can't delete it, only remove records)
            is_apex = (name == "@")

            # Count remaining records across all types
            total_records = 0
            for attr in RECORD_TYPE_ATTRS.values():
                vals = entry.get(attr, [])
                if isinstance(vals, str):
                    vals = [vals]
                total_records += len(vals)

            # For MX/SRV, find the full value with priority
            current_values = entry.get(attr_name, [])
            if isinstance(current_values, str):
                current_values = [current_values]

            full_value = None
            for cv in current_values:
                if rtype in [RecordType.MX, RecordType.SRV]:
                    parts = cv.split(None, 1)
                    cv_target = parts[1] if len(parts) > 1 else parts[0]
                    if cv_target == value or cv == value:
                        full_value = cv
                        break
                elif cv == value:
                    full_value = cv
                    break

            if full_value is None:
                raise LdapNotFoundError(f"Record value '{value}' not found")

            # Determine if we should delete the entry or just remove the value
            if total_records == 1 and not is_apex:
                # Last record in non-apex entry - delete the entry
                await self._ldap.delete(dn)
            else:
                # Remove just this record value
                changes = {
                    attr_name: ("delete", [full_value]),
                }
                await self._ldap.modify(dn, changes)

            # Increment zone serial
            await self._increment_zone_serial(zone_name)

            logger.info(
                "record_deleted",
                zone_name=zone_name,
                name=name,
                record_type=record_type,
            )

        except LdapOperationError as e:
            logger.error(
                "record_delete_failed",
                zone_name=zone_name,
                name=name,
                error=str(e)
            )
            raise DnsValidationError(f"Failed to delete record: {e}")

    async def _increment_zone_serial(self, zone_name: str) -> None:
        """Increment the zone's SOA serial number."""
        try:
            zone = await self.get_zone(zone_name)
            if not zone:
                return

            new_serial = increment_serial(zone.soa.serial)
            new_soa = SoaRecord(
                primary_ns=zone.soa.primary_ns,
                admin_email=zone.soa.admin_email,
                serial=new_serial,
                refresh=zone.soa.refresh,
                retry=zone.soa.retry,
                expire=zone.soa.expire,
                minimum=zone.soa.minimum,
            )

            dn = self._get_zone_dn(zone_name)
            await self._ldap.modify(dn, {
                "sOARecord": ("replace", [new_soa.to_soa_string()]),
            })

        except LdapOperationError as e:
            logger.warning(
                "serial_increment_failed",
                zone_name=zone_name,
                error=str(e)
            )

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _get_first_value(self, entry: LdapEntry, attr: str) -> Optional[str]:
        """Get the first value of an attribute."""
        if hasattr(entry, 'get_first'):
            return entry.get_first(attr)
        vals = entry.get(attr, [])
        if isinstance(vals, str):
            return vals
        return vals[0] if vals else None

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
                attributes=self.MANAGED_ATTRIBUTES + ["objectClass"]
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
        # DN format: zoneName=example.org,ou=dns,dc=... (FusionDirectory compatible)
        parts = dn.split(",")
        zone_name = None
        for part in parts:
            if part.startswith("zoneName="):
                zone_name = part.split("=", 1)[1]
                break

        if not zone_name:
            raise DnsValidationError(f"Could not extract zone name from DN: {dn}")

        return await self.update_zone(zone_name, data)

    async def deactivate(self, dn: str) -> None:
        """Delete a zone by DN."""
        # Extract zone name from DN
        # DN format: zoneName=example.org,ou=dns,dc=... (FusionDirectory compatible)
        parts = dn.split(",")
        zone_name = None
        for part in parts:
            if part.startswith("zoneName="):
                zone_name = part.split("=", 1)[1]
                break

        if not zone_name:
            raise DnsValidationError(f"Could not extract zone name from DN: {dn}")

        await self.delete_zone(zone_name)
