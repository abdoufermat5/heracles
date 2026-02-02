"""
DHCP Subnet Schemas
===================

Pydantic models for DHCP subnet objects.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

from .base import DhcpBase, PaginatedResponse
from .enums import DhcpObjectType
from .validators import validate_ip_address, validate_ip_range


class SubnetCreate(DhcpBase):
    """Schema for creating a DHCP subnet."""

    cn: str = Field(
        ...,
        description="Network address (e.g., '192.168.1.0')",
    )
    dhcp_netmask: int = Field(
        ...,
        ge=0,
        le=32,
        alias="dhcpNetMask",
        description="Subnet mask length (CIDR notation)",
    )
    dhcp_range: List[str] = Field(
        default_factory=list,
        alias="dhcpRange",
        description="IP ranges (e.g., ['192.168.1.100 192.168.1.200'])",
    )

    @field_validator("cn")
    @classmethod
    def validate_cn(cls, v):
        """Validate network address."""
        return validate_ip_address(v)

    @field_validator("dhcp_range", mode="before")
    @classmethod
    def validate_ranges(cls, v):
        """Validate IP ranges."""
        if v is None:
            return []
        if isinstance(v, str):
            v = [v]
        return [validate_ip_range(r) for r in v]


class SubnetUpdate(DhcpBase):
    """Schema for updating a DHCP subnet."""

    dhcp_netmask: Optional[int] = Field(
        default=None,
        ge=0,
        le=32,
        alias="dhcpNetMask",
    )
    dhcp_range: Optional[List[str]] = Field(
        default=None,
        alias="dhcpRange",
    )

    @field_validator("dhcp_range", mode="before")
    @classmethod
    def validate_ranges(cls, v):
        """Validate IP ranges."""
        if v is None:
            return None
        if isinstance(v, str):
            v = [v]
        return [validate_ip_range(r) for r in v]


class SubnetRead(DhcpBase):
    """Schema for reading a DHCP subnet."""

    dn: str = Field(..., description="Distinguished Name")
    cn: str = Field(..., description="Network address")
    dhcp_netmask: int = Field(..., alias="dhcpNetMask")
    dhcp_range: List[str] = Field(
        default_factory=list,
        alias="dhcpRange",
    )
    parent_dn: Optional[str] = Field(
        default=None,
        alias="parentDn",
        description="Parent object DN",
    )
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.SUBNET,
        alias="objectType",
    )


class SubnetListItem(BaseModel):
    """Schema for subnet in list responses."""

    dn: str
    cn: str
    dhcp_netmask: int = Field(..., alias="dhcpNetMask")
    dhcp_range: List[str] = Field(default_factory=list, alias="dhcpRange")
    comments: Optional[str] = Field(default=None, alias="dhcpComments")
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.SUBNET,
        alias="objectType",
    )

    model_config = {"populate_by_name": True}


class SubnetListResponse(PaginatedResponse):
    """Paginated list of subnets."""

    items: List[SubnetListItem]
