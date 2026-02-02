"""
DHCP Failover Peer Schemas
==========================

Pydantic models for DHCP failover peer configuration objects.
"""

from typing import Optional, List
from pydantic import BaseModel, Field

from .base import DhcpBase, PaginatedResponse
from .enums import DhcpObjectType


class FailoverPeerCreate(DhcpBase):
    """Schema for creating a failover peer configuration."""

    cn: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Failover peer name",
    )
    dhcp_failover_primary_server: str = Field(
        ...,
        alias="dhcpFailOverPrimaryServer",
        description="Primary server IP or hostname",
    )
    dhcp_failover_secondary_server: str = Field(
        ...,
        alias="dhcpFailOverSecondaryServer",
        description="Secondary server IP or hostname",
    )
    dhcp_failover_primary_port: int = Field(
        ...,
        ge=1,
        le=65535,
        alias="dhcpFailOverPrimaryPort",
        description="Primary server failover port",
    )
    dhcp_failover_secondary_port: int = Field(
        ...,
        ge=1,
        le=65535,
        alias="dhcpFailOverSecondaryPort",
        description="Secondary server failover port",
    )
    dhcp_failover_response_delay: Optional[int] = Field(
        default=None,
        ge=1,
        alias="dhcpFailOverResponseDelay",
        description="Response delay in seconds",
    )
    dhcp_failover_unacked_updates: Optional[int] = Field(
        default=None,
        ge=1,
        alias="dhcpFailOverUnackedUpdates",
        description="Unacked updates count",
    )
    dhcp_max_client_lead_time: Optional[int] = Field(
        default=None,
        ge=1,
        alias="dhcpMaxClientLeadTime",
        description="Max client lead time (MCLT) in seconds",
    )
    dhcp_failover_split: Optional[int] = Field(
        default=None,
        ge=0,
        le=256,
        alias="dhcpFailOverSplit",
        description="Split value (0-256)",
    )
    dhcp_failover_load_balance_time: Optional[int] = Field(
        default=None,
        ge=0,
        alias="dhcpFailOverLoadBalanceTime",
        description="Load balance cutoff time in seconds",
    )


class FailoverPeerUpdate(DhcpBase):
    """Schema for updating a failover peer."""

    dhcp_failover_primary_server: Optional[str] = Field(
        default=None,
        alias="dhcpFailOverPrimaryServer",
    )
    dhcp_failover_secondary_server: Optional[str] = Field(
        default=None,
        alias="dhcpFailOverSecondaryServer",
    )
    dhcp_failover_primary_port: Optional[int] = Field(
        default=None,
        ge=1,
        le=65535,
        alias="dhcpFailOverPrimaryPort",
    )
    dhcp_failover_secondary_port: Optional[int] = Field(
        default=None,
        ge=1,
        le=65535,
        alias="dhcpFailOverSecondaryPort",
    )
    dhcp_failover_response_delay: Optional[int] = Field(
        default=None,
        alias="dhcpFailOverResponseDelay",
    )
    dhcp_failover_unacked_updates: Optional[int] = Field(
        default=None,
        alias="dhcpFailOverUnackedUpdates",
    )
    dhcp_max_client_lead_time: Optional[int] = Field(
        default=None,
        alias="dhcpMaxClientLeadTime",
    )
    dhcp_failover_split: Optional[int] = Field(
        default=None,
        alias="dhcpFailOverSplit",
    )
    dhcp_failover_load_balance_time: Optional[int] = Field(
        default=None,
        alias="dhcpFailOverLoadBalanceTime",
    )


class FailoverPeerRead(DhcpBase):
    """Schema for reading a failover peer."""

    dn: str = Field(..., description="Distinguished Name")
    cn: str = Field(..., description="Failover peer name")
    dhcp_failover_primary_server: str = Field(..., alias="dhcpFailOverPrimaryServer")
    dhcp_failover_secondary_server: str = Field(..., alias="dhcpFailOverSecondaryServer")
    dhcp_failover_primary_port: int = Field(..., alias="dhcpFailOverPrimaryPort")
    dhcp_failover_secondary_port: int = Field(..., alias="dhcpFailOverSecondaryPort")
    dhcp_failover_response_delay: Optional[int] = Field(
        default=None,
        alias="dhcpFailOverResponseDelay",
    )
    dhcp_failover_unacked_updates: Optional[int] = Field(
        default=None,
        alias="dhcpFailOverUnackedUpdates",
    )
    dhcp_max_client_lead_time: Optional[int] = Field(
        default=None,
        alias="dhcpMaxClientLeadTime",
    )
    dhcp_failover_split: Optional[int] = Field(
        default=None,
        alias="dhcpFailOverSplit",
    )
    dhcp_failover_load_balance_time: Optional[int] = Field(
        default=None,
        alias="dhcpFailOverLoadBalanceTime",
    )
    parent_dn: Optional[str] = Field(
        default=None,
        alias="parentDn",
    )
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.FAILOVER_PEER,
        alias="objectType",
    )


class FailoverPeerListItem(BaseModel):
    """Schema for failover peer in list responses."""

    dn: str
    cn: str
    dhcp_failover_primary_server: str = Field(..., alias="dhcpFailOverPrimaryServer")
    dhcp_failover_secondary_server: str = Field(..., alias="dhcpFailOverSecondaryServer")
    comments: Optional[str] = Field(default=None, alias="dhcpComments")
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.FAILOVER_PEER,
        alias="objectType",
    )

    model_config = {"populate_by_name": True}


class FailoverPeerListResponse(PaginatedResponse):
    """Paginated list of failover peers."""

    items: List[FailoverPeerListItem]
