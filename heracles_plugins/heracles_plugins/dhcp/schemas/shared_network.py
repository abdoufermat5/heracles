"""
DHCP Shared Network Schemas
===========================

Pydantic models for DHCP shared network objects.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

from .base import DhcpBase, PaginatedResponse
from .enums import DhcpObjectType
from .validators import validate_cn_alphanumeric


class SharedNetworkCreate(DhcpBase):
    """Schema for creating a DHCP shared network."""

    cn: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Shared network name",
    )

    @field_validator("cn")
    @classmethod
    def validate_cn(cls, v):
        """Validate shared network name."""
        return validate_cn_alphanumeric(v)


class SharedNetworkUpdate(DhcpBase):
    """Schema for updating a DHCP shared network."""
    pass


class SharedNetworkRead(DhcpBase):
    """Schema for reading a DHCP shared network."""

    dn: str = Field(..., description="Distinguished Name")
    cn: str = Field(..., description="Shared network name")
    parent_dn: Optional[str] = Field(
        default=None,
        alias="parentDn",
    )
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.SHARED_NETWORK,
        alias="objectType",
    )


class SharedNetworkListItem(BaseModel):
    """Schema for shared network in list responses."""

    dn: str
    cn: str
    comments: Optional[str] = Field(default=None, alias="dhcpComments")
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.SHARED_NETWORK,
        alias="objectType",
    )

    model_config = {"populate_by_name": True}


class SharedNetworkListResponse(PaginatedResponse):
    """Paginated list of shared networks."""

    items: List[SharedNetworkListItem]
