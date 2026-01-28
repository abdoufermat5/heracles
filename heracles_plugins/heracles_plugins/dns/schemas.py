"""
DNS Plugin Schemas
==================

Pydantic models for DNS zone and record management.

Record Types:
    - A: IPv4 address
    - AAAA: IPv6 address
    - MX: Mail exchanger
    - NS: Name server
    - CNAME: Canonical name (alias)
    - PTR: Pointer (reverse DNS)
    - TXT: Text record
    - SRV: Service location

Zone Types:
    - forward: Standard forward lookup zone (e.g., example.org)
    - reverse-ipv4: Reverse lookup zone for IPv4 (e.g., 168.192.in-addr.arpa)
    - reverse-ipv6: Reverse lookup zone for IPv6 (e.g., 8.b.d.0.1.0.0.2.ip6.arpa)
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import re


# ============================================================================
# Enums
# ============================================================================

class RecordType(str, Enum):
    """DNS record types supported by this plugin."""

    A = "A"
    AAAA = "AAAA"
    MX = "MX"
    NS = "NS"
    CNAME = "CNAME"
    PTR = "PTR"
    TXT = "TXT"
    SRV = "SRV"


class ZoneType(str, Enum):
    """DNS zone types."""

    FORWARD = "forward"
    REVERSE_IPV4 = "reverse-ipv4"
    REVERSE_IPV6 = "reverse-ipv6"


# ============================================================================
# LDAP Attribute Mapping
# ============================================================================

# Map record types to LDAP attributes
RECORD_TYPE_ATTRS = {
    RecordType.A: "aRecord",
    RecordType.AAAA: "aAAARecord",
    RecordType.MX: "mXRecord",
    RecordType.NS: "nSRecord",
    RecordType.CNAME: "cNAMERecord",
    RecordType.PTR: "pTRRecord",
    RecordType.TXT: "tXTRecord",
    RecordType.SRV: "sRVRecord",
}

# Reverse mapping: LDAP attribute to record type
ATTR_RECORD_TYPES = {v: k for k, v in RECORD_TYPE_ATTRS.items()}


# ============================================================================
# SOA Record Schema
# ============================================================================

class SoaRecord(BaseModel):
    """SOA (Start of Authority) record data."""

    primary_ns: str = Field(
        ...,
        alias="primaryNs",
        description="Primary nameserver (MNAME)",
    )
    admin_email: str = Field(
        ...,
        alias="adminEmail",
        description="Admin email (RNAME), dot notation",
    )
    serial: int = Field(
        ...,
        description="Zone serial number (YYYYMMDDNN format)",
    )
    refresh: int = Field(
        default=3600,
        ge=60,
        description="Refresh interval in seconds",
    )
    retry: int = Field(
        default=600,
        ge=60,
        description="Retry interval in seconds",
    )
    expire: int = Field(
        default=604800,
        ge=3600,
        description="Expire time in seconds",
    )
    minimum: int = Field(
        default=86400,
        ge=60,
        description="Minimum TTL (negative cache)",
    )

    model_config = {"populate_by_name": True}

    @classmethod
    def from_soa_string(cls, soa_string: str) -> "SoaRecord":
        """Parse SOA record from LDAP string format.

        Format: 'primary_ns admin_email serial refresh retry expire minimum'
        Example: 'ns1.example.org. admin.example.org. 2024010101 3600 600 604800 86400'
        """
        parts = soa_string.split()
        if len(parts) != 7:
            raise ValueError(f"Invalid SOA format: {soa_string}")

        return cls(
            primary_ns=parts[0],
            admin_email=parts[1],
            serial=int(parts[2]),
            refresh=int(parts[3]),
            retry=int(parts[4]),
            expire=int(parts[5]),
            minimum=int(parts[6]),
        )

    def to_soa_string(self) -> str:
        """Convert to LDAP SOA string format."""
        return f"{self.primary_ns} {self.admin_email} {self.serial} {self.refresh} {self.retry} {self.expire} {self.minimum}"


# ============================================================================
# Zone Schemas
# ============================================================================

class DnsZoneCreate(BaseModel):
    """Schema for creating a new DNS zone."""

    zone_name: str = Field(
        ...,
        alias="zoneName",
        min_length=1,
        max_length=253,
        description="Zone name (e.g., example.org)",
    )
    soa_primary_ns: str = Field(
        ...,
        alias="soaPrimaryNs",
        description="Primary nameserver FQDN (must end with dot)",
    )
    soa_admin_email: str = Field(
        ...,
        alias="soaAdminEmail",
        description="Admin email in dot notation (e.g., admin.example.org.)",
    )
    default_ttl: int = Field(
        default=3600,
        alias="defaultTtl",
        ge=60,
        le=604800,
        description="Default TTL for records in seconds",
    )
    soa_refresh: int = Field(
        default=3600,
        alias="soaRefresh",
        ge=60,
        description="SOA refresh interval",
    )
    soa_retry: int = Field(
        default=600,
        alias="soaRetry",
        ge=60,
        description="SOA retry interval",
    )
    soa_expire: int = Field(
        default=604800,
        alias="soaExpire",
        ge=3600,
        description="SOA expire time",
    )
    soa_minimum: int = Field(
        default=86400,
        alias="soaMinimum",
        ge=60,
        description="SOA minimum TTL",
    )

    @field_validator("zone_name")
    @classmethod
    def validate_zone_name(cls, v: str) -> str:
        """Validate zone name format."""
        v = v.strip().lower()
        # Remove trailing dot if present
        if v.endswith("."):
            v = v[:-1]

        # Basic DNS name validation
        if not re.match(r"^[a-z0-9]([a-z0-9\-\.]*[a-z0-9])?$", v):
            raise ValueError("Invalid zone name format")

        # Check each label
        labels = v.split(".")
        for label in labels:
            if len(label) > 63:
                raise ValueError("Label too long (max 63 characters)")
            if label.startswith("-") or label.endswith("-"):
                raise ValueError("Labels cannot start or end with hyphen")

        return v

    @field_validator("soa_primary_ns")
    @classmethod
    def validate_primary_ns(cls, v: str) -> str:
        """Validate primary nameserver - must be FQDN with trailing dot."""
        v = v.strip().lower()
        if not v.endswith("."):
            v = v + "."
        return v

    @field_validator("soa_admin_email")
    @classmethod
    def validate_admin_email(cls, v: str) -> str:
        """Validate admin email in DNS notation."""
        v = v.strip().lower()
        if not v.endswith("."):
            v = v + "."
        return v

    model_config = {"populate_by_name": True}


class DnsZoneUpdate(BaseModel):
    """Schema for updating a DNS zone."""

    soa_primary_ns: Optional[str] = Field(
        default=None,
        alias="soaPrimaryNs",
        description="Primary nameserver FQDN",
    )
    soa_admin_email: Optional[str] = Field(
        default=None,
        alias="soaAdminEmail",
        description="Admin email in dot notation",
    )
    soa_refresh: Optional[int] = Field(
        default=None,
        alias="soaRefresh",
        ge=60,
        description="SOA refresh interval",
    )
    soa_retry: Optional[int] = Field(
        default=None,
        alias="soaRetry",
        ge=60,
        description="SOA retry interval",
    )
    soa_expire: Optional[int] = Field(
        default=None,
        alias="soaExpire",
        ge=3600,
        description="SOA expire time",
    )
    soa_minimum: Optional[int] = Field(
        default=None,
        alias="soaMinimum",
        ge=60,
        description="SOA minimum TTL",
    )
    default_ttl: Optional[int] = Field(
        default=None,
        alias="defaultTtl",
        ge=60,
        le=604800,
        description="Default TTL for records",
    )

    @field_validator("soa_primary_ns")
    @classmethod
    def validate_primary_ns(cls, v: Optional[str]) -> Optional[str]:
        """Validate primary nameserver if provided."""
        if v is None:
            return None
        v = v.strip().lower()
        if not v.endswith("."):
            v = v + "."
        return v

    @field_validator("soa_admin_email")
    @classmethod
    def validate_admin_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate admin email if provided."""
        if v is None:
            return None
        v = v.strip().lower()
        if not v.endswith("."):
            v = v + "."
        return v

    model_config = {"populate_by_name": True}


class DnsZoneRead(BaseModel):
    """Schema for reading a DNS zone."""

    dn: str = Field(..., description="Distinguished Name")
    zone_name: str = Field(..., alias="zoneName", description="Zone name")
    zone_type: ZoneType = Field(..., alias="zoneType", description="Zone type")
    soa: SoaRecord = Field(..., description="SOA record")
    default_ttl: int = Field(..., alias="defaultTtl", description="Default TTL")
    record_count: int = Field(..., alias="recordCount", description="Number of records")

    model_config = {"populate_by_name": True}


class DnsZoneListItem(BaseModel):
    """Summary of a zone for list views."""

    dn: str = Field(..., description="Distinguished Name")
    zone_name: str = Field(..., alias="zoneName", description="Zone name")
    zone_type: ZoneType = Field(..., alias="zoneType", description="Zone type")
    record_count: int = Field(..., alias="recordCount", description="Number of records")

    model_config = {"populate_by_name": True}


class DnsZoneListResponse(BaseModel):
    """Response for listing zones."""

    zones: List[DnsZoneListItem]
    total: int


# ============================================================================
# Record Schemas
# ============================================================================

class DnsRecordCreate(BaseModel):
    """Schema for creating a new DNS record."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=253,
        description="Record name (@ for zone apex)",
    )
    record_type: RecordType = Field(
        ...,
        alias="recordType",
        description="DNS record type",
    )
    value: str = Field(
        ...,
        min_length=1,
        description="Record value",
    )
    ttl: Optional[int] = Field(
        default=None,
        ge=60,
        le=604800,
        description="TTL in seconds (uses zone default if not set)",
    )
    priority: Optional[int] = Field(
        default=None,
        ge=0,
        le=65535,
        description="Priority (for MX and SRV records)",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate record name."""
        v = v.strip().lower()
        if v == "@":
            return "@"

        # Validate DNS label format
        if not re.match(r"^[a-z0-9_]([a-z0-9\-_\.]*[a-z0-9])?$", v):
            raise ValueError("Invalid record name format")

        return v

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: str) -> str:
        """Basic value validation - specific validation done per type in service."""
        return v.strip()

    model_config = {"populate_by_name": True}


class DnsRecordUpdate(BaseModel):
    """Schema for updating a DNS record."""

    value: Optional[str] = Field(
        default=None,
        min_length=1,
        description="New record value",
    )
    ttl: Optional[int] = Field(
        default=None,
        ge=60,
        le=604800,
        description="TTL in seconds",
    )
    priority: Optional[int] = Field(
        default=None,
        ge=0,
        le=65535,
        description="Priority (for MX and SRV)",
    )

    model_config = {"populate_by_name": True}


class DnsRecordRead(BaseModel):
    """Schema for reading a DNS record."""

    dn: str = Field(..., description="Distinguished Name of the record entry")
    name: str = Field(..., description="Record name (relativeDomainName)")
    record_type: RecordType = Field(..., alias="recordType", description="Record type")
    value: str = Field(..., description="Record value")
    ttl: Optional[int] = Field(default=None, description="TTL in seconds")
    priority: Optional[int] = Field(default=None, description="Priority (MX/SRV)")

    model_config = {"populate_by_name": True}


class DnsRecordListItem(BaseModel):
    """Summary of a record for list views."""

    dn: str = Field(..., description="Distinguished Name")
    name: str = Field(..., description="Record name")
    record_type: RecordType = Field(..., alias="recordType", description="Record type")
    value: str = Field(..., description="Record value")
    ttl: Optional[int] = Field(default=None, description="TTL")
    priority: Optional[int] = Field(default=None, description="Priority")

    model_config = {"populate_by_name": True}


# ============================================================================
# Utility Functions
# ============================================================================

def detect_zone_type(zone_name: str) -> ZoneType:
    """Detect zone type from zone name.

    Args:
        zone_name: The zone name (e.g., 'example.org' or '168.192.in-addr.arpa')

    Returns:
        ZoneType indicating forward or reverse zone
    """
    zone_name = zone_name.lower()

    if zone_name.endswith(".in-addr.arpa"):
        return ZoneType.REVERSE_IPV4
    elif zone_name.endswith(".ip6.arpa"):
        return ZoneType.REVERSE_IPV6
    else:
        return ZoneType.FORWARD


def generate_serial() -> int:
    """Generate a new SOA serial number in YYYYMMDDNN format.

    Returns:
        Serial number based on current date with sequence 01
    """
    today = datetime.now()
    return int(f"{today.year:04d}{today.month:02d}{today.day:02d}01")


def increment_serial(current_serial: int) -> int:
    """Increment SOA serial number.

    If the current serial is from today, increment the sequence.
    Otherwise, generate a new serial with today's date.

    Args:
        current_serial: Current serial number

    Returns:
        Incremented serial number
    """
    today = datetime.now()
    today_base = int(f"{today.year:04d}{today.month:02d}{today.day:02d}00")

    # If current serial is from today, increment
    if current_serial >= today_base and current_serial < today_base + 99:
        return current_serial + 1

    # Otherwise, start fresh with today's date
    return today_base + 1
