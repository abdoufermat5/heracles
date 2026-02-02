"""
DHCP Service Schemas
====================

Pydantic models for DHCP service objects.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

from .base import DhcpBase, PaginatedResponse
from .enums import DhcpObjectType
from .validators import validate_cn_alphanumeric


class DhcpServiceCreate(DhcpBase):
    """Schema for creating a DHCP service (root configuration)."""

    cn: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Service name (e.g., 'main-dhcp')",
    )
    dhcp_primary_dn: Optional[str] = Field(
        default=None,
        alias="dhcpPrimaryDN",
        description="DN of the primary DHCP server",
    )
    dhcp_secondary_dn: Optional[str] = Field(
        default=None,
        alias="dhcpSecondaryDN",
        description="DN of the secondary DHCP server",
    )

    @field_validator("cn")
    @classmethod
    def validate_cn(cls, v):
        """Validate service name."""
        return validate_cn_alphanumeric(v)


class DhcpServiceUpdate(DhcpBase):
    """Schema for updating a DHCP service."""

    dhcp_primary_dn: Optional[str] = Field(
        default=None,
        alias="dhcpPrimaryDN",
    )
    dhcp_secondary_dn: Optional[str] = Field(
        default=None,
        alias="dhcpSecondaryDN",
    )


class DhcpServiceRead(DhcpBase):
    """Schema for reading a DHCP service."""

    dn: str = Field(..., description="Distinguished Name")
    cn: str = Field(..., description="Service name")
    dhcp_primary_dn: Optional[str] = Field(
        default=None,
        alias="dhcpPrimaryDN",
    )
    dhcp_secondary_dn: Optional[str] = Field(
        default=None,
        alias="dhcpSecondaryDN",
    )
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.SERVICE,
        alias="objectType",
    )


class DhcpServiceListItem(BaseModel):
    """Schema for service in list responses."""

    dn: str
    cn: str
    comments: Optional[str] = Field(default=None, alias="dhcpComments")
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.SERVICE,
        alias="objectType",
    )

    model_config = {"populate_by_name": True}


class DhcpServiceListResponse(PaginatedResponse):
    """Paginated list of DHCP services."""

    items: List[DhcpServiceListItem]
