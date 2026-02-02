"""
DHCP DNS Zone Schemas
=====================

Pydantic models for DHCP DNS zone objects (for dynamic DNS updates).
"""

from typing import Optional, List
from pydantic import BaseModel, Field

from .base import DhcpBase, PaginatedResponse
from .enums import DhcpObjectType


class DnsZoneCreate(DhcpBase):
    """Schema for creating a DNS zone for dynamic updates."""

    cn: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Zone name (FQDN)",
    )
    dhcp_dns_zone_server: str = Field(
        ...,
        alias="dhcpDnsZoneServer",
        description="DNS server for this zone",
    )
    dhcp_key_dn: Optional[str] = Field(
        default=None,
        alias="dhcpKeyDN",
        description="DN of TSIG key for secure updates",
    )


class DnsZoneUpdate(DhcpBase):
    """Schema for updating a DNS zone."""

    dhcp_dns_zone_server: Optional[str] = Field(
        default=None,
        alias="dhcpDnsZoneServer",
    )
    dhcp_key_dn: Optional[str] = Field(
        default=None,
        alias="dhcpKeyDN",
    )


class DnsZoneRead(DhcpBase):
    """Schema for reading a DNS zone."""

    dn: str = Field(..., description="Distinguished Name")
    cn: str = Field(..., description="Zone name")
    dhcp_dns_zone_server: str = Field(..., alias="dhcpDnsZoneServer")
    dhcp_key_dn: Optional[str] = Field(
        default=None,
        alias="dhcpKeyDN",
    )
    parent_dn: Optional[str] = Field(
        default=None,
        alias="parentDn",
    )
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.DNS_ZONE,
        alias="objectType",
    )


class DnsZoneListItem(BaseModel):
    """Schema for DNS zone in list responses."""

    dn: str
    cn: str
    dhcp_dns_zone_server: str = Field(..., alias="dhcpDnsZoneServer")
    comments: Optional[str] = Field(default=None, alias="dhcpComments")
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.DNS_ZONE,
        alias="objectType",
    )

    model_config = {"populate_by_name": True}


class DnsZoneListResponse(PaginatedResponse):
    """Paginated list of DNS zones."""

    items: List[DnsZoneListItem]
