"""
DNS Record Operations Mixin
===========================

Record CRUD operations and validation for DNS service.
"""

import re
from typing import List, Optional, Tuple

import structlog

from heracles_api.services.ldap_service import (
    LdapEntry,
    LdapOperationError,
    LdapNotFoundError,
)

from ...schemas import (
    RecordType,
    SoaRecord,
    DnsRecordCreate,
    DnsRecordRead,
    DnsRecordUpdate,
    DnsRecordListItem,
    RECORD_TYPE_ATTRS,
    increment_serial,
)
from ..constants import OBJECT_CLASSES, DNS_CLASS, MANAGED_ATTRIBUTES
from ..utils import get_first_value
from ..base import DnsValidationError

logger = structlog.get_logger(__name__)


class RecordOperationsMixin:
    """Mixin providing DNS record CRUD operations."""

    # ========================================================================
    # Record List Operations
    # ========================================================================

    async def list_records(
        self, 
        zone_name: str,
        base_dn: Optional[str] = None
    ) -> List[DnsRecordListItem]:
        """
        List all records in a zone.

        Returns records from all relativeDomainName entries.
        """
        zone_name = zone_name.lower()

        # Verify zone exists
        zone = await self.get_zone(zone_name, base_dn=base_dn)
        if not zone:
            raise LdapNotFoundError(f"Zone '{zone_name}' not found")

        zone_dn = self._get_zone_dn(zone_name, base_dn=base_dn)

        try:
            entries = await self._ldap.search(
                search_base=zone_dn,
                search_filter="(objectClass=dNSZone)",
                attributes=MANAGED_ATTRIBUTES,
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
        name = get_first_value(entry, "relativeDomainName") or "@"
        ttl_str = get_first_value(entry, "dNSTTL")
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

    # ========================================================================
    # Record Create Operations
    # ========================================================================

    async def create_record(
        self,
        zone_name: str,
        data: DnsRecordCreate,
        base_dn: Optional[str] = None
    ) -> DnsRecordRead:
        """
        Create a new DNS record.

        If the relativeDomainName entry doesn't exist, creates it.
        Otherwise, adds the record value to the existing entry.
        """
        zone_name = zone_name.lower()

        # Verify zone exists
        zone = await self.get_zone(zone_name, base_dn=base_dn)
        if not zone:
            raise LdapNotFoundError(f"Zone '{zone_name}' not found")

        # Validate record
        self._validate_record(data)

        name = data.name
        dn = self._get_record_dn(zone_name, name, base_dn=base_dn)

        # Build record value (with priority for MX/SRV)
        record_value = self._build_record_value(data)

        # Get LDAP attribute name for this record type
        attr_name = RECORD_TYPE_ATTRS[data.record_type]

        try:
            # Check if entry exists
            existing = await self._ldap.get_by_dn(
                dn,
                attributes=MANAGED_ATTRIBUTES
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
                    "dNSClass": [DNS_CLASS],
                    attr_name: [record_value],
                }
                if data.ttl is not None:
                    attributes["dNSTTL"] = [str(data.ttl)]

                await self._ldap.add(
                    dn=dn,
                    object_classes=OBJECT_CLASSES,
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

    # ========================================================================
    # Record Update Operations
    # ========================================================================

    async def update_record(
        self,
        zone_name: str,
        name: str,
        record_type: str,
        old_value: str,
        data: DnsRecordUpdate,
        base_dn: Optional[str] = None
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
        zone = await self.get_zone(zone_name, base_dn=base_dn)
        if not zone:
            raise LdapNotFoundError(f"Zone '{zone_name}' not found")

        dn = self._get_record_dn(zone_name, name, base_dn=base_dn)
        attr_name = RECORD_TYPE_ATTRS[rtype]

        try:
            # Get existing entry
            entry = await self._ldap.get_by_dn(dn, attributes=MANAGED_ATTRIBUTES)
            if entry is None:
                raise LdapNotFoundError(f"Record entry '{name}' not found")

            # Build old and new values
            old_full_value = old_value

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

    # ========================================================================
    # Record Delete Operations
    # ========================================================================

    async def delete_record(
        self,
        zone_name: str,
        name: str,
        record_type: str,
        value: str,
        base_dn: Optional[str] = None
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
        zone = await self.get_zone(zone_name, base_dn=base_dn)
        if not zone:
            raise LdapNotFoundError(f"Zone '{zone_name}' not found")

        dn = self._get_record_dn(zone_name, name, base_dn=base_dn)
        attr_name = RECORD_TYPE_ATTRS[rtype]

        try:
            # Get existing entry
            entry = await self._ldap.get_by_dn(dn, attributes=MANAGED_ATTRIBUTES)
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

    # ========================================================================
    # Record Validation and Utilities
    # ========================================================================

    def _validate_record(self, data: DnsRecordCreate) -> None:
        """Validate record data based on type."""
        record_type = data.record_type
        value = data.value

        if record_type == RecordType.A:
            # Validate IPv4
            if not re.match(r"^(\d{1,3}\.){3}\d{1,3}$", value):
                raise DnsValidationError("Invalid IPv4 address format")
            octets = value.split(".")
            if not all(0 <= int(o) <= 255 for o in octets):
                raise DnsValidationError("Invalid IPv4 address")

        elif record_type == RecordType.AAAA:
            # Basic IPv6 validation
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
