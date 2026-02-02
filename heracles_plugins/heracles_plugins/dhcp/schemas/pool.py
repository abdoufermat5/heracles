"""
DHCP Pool Schemas
=================

Pydantic models for DHCP pool objects.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

from .base import DhcpBase, PaginatedResponse
from .enums import DhcpObjectType
from .validators import validate_ip_range


class PoolCreate(DhcpBase):
    """Schema for creating a DHCP pool."""

    cn: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Pool name",
    )
    dhcp_range: List[str] = Field(
        ...,
        min_length=1,
        alias="dhcpRange",
        description="IP ranges (required)",
    )
    dhcp_permit_list: List[str] = Field(
        default_factory=list,
        alias="dhcpPermitList",
        description="Permit list (allow/deny rules)",
    )

    @field_validator("dhcp_range", mode="before")
    @classmethod
    def validate_ranges(cls, v):
        """Validate IP ranges."""
        if v is None:
            raise ValueError("At least one IP range is required")
        if isinstance(v, str):
            v = [v]
        if len(v) == 0:
            raise ValueError("At least one IP range is required")
        return [validate_ip_range(r) for r in v]


class PoolUpdate(DhcpBase):
    """Schema for updating a DHCP pool."""

    dhcp_range: Optional[List[str]] = Field(
        default=None,
        alias="dhcpRange",
    )
    dhcp_permit_list: Optional[List[str]] = Field(
        default=None,
        alias="dhcpPermitList",
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


class PoolRead(DhcpBase):
    """Schema for reading a DHCP pool."""

    dn: str = Field(..., description="Distinguished Name")
    cn: str = Field(..., description="Pool name")
    dhcp_range: List[str] = Field(..., alias="dhcpRange")
    dhcp_permit_list: List[str] = Field(
        default_factory=list,
        alias="dhcpPermitList",
    )
    parent_dn: Optional[str] = Field(
        default=None,
        alias="parentDn",
    )
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.POOL,
        alias="objectType",
    )


class PoolListItem(BaseModel):
    """Schema for pool in list responses."""

    dn: str
    cn: str
    dhcp_range: List[str] = Field(..., alias="dhcpRange")
    comments: Optional[str] = Field(default=None, alias="dhcpComments")
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.POOL,
        alias="objectType",
    )

    model_config = {"populate_by_name": True}


class PoolListResponse(PaginatedResponse):
    """Paginated list of pools."""

    items: List[PoolListItem]
