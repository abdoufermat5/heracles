"""
DHCP TSIG Key Schemas
=====================

Pydantic models for DHCP TSIG key objects.
"""

from typing import Optional, List
from pydantic import BaseModel, Field

from .base import DhcpBase, PaginatedResponse
from .enums import DhcpObjectType, TsigKeyAlgorithm


class TsigKeyCreate(DhcpBase):
    """Schema for creating a TSIG key."""

    cn: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Key name",
    )
    dhcp_key_algorithm: TsigKeyAlgorithm = Field(
        ...,
        alias="dhcpKeyAlgorithm",
        description="TSIG key algorithm",
    )
    dhcp_key_secret: str = Field(
        ...,
        min_length=1,
        alias="dhcpKeySecret",
        description="TSIG key secret (base64 encoded)",
    )


class TsigKeyUpdate(DhcpBase):
    """Schema for updating a TSIG key."""

    dhcp_key_algorithm: Optional[TsigKeyAlgorithm] = Field(
        default=None,
        alias="dhcpKeyAlgorithm",
    )
    dhcp_key_secret: Optional[str] = Field(
        default=None,
        alias="dhcpKeySecret",
    )


class TsigKeyRead(DhcpBase):
    """Schema for reading a TSIG key."""

    dn: str = Field(..., description="Distinguished Name")
    cn: str = Field(..., description="Key name")
    dhcp_key_algorithm: TsigKeyAlgorithm = Field(..., alias="dhcpKeyAlgorithm")
    # Secret is not returned for security
    parent_dn: Optional[str] = Field(
        default=None,
        alias="parentDn",
    )
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.TSIG_KEY,
        alias="objectType",
    )


class TsigKeyListItem(BaseModel):
    """Schema for TSIG key in list responses."""

    dn: str
    cn: str
    dhcp_key_algorithm: TsigKeyAlgorithm = Field(..., alias="dhcpKeyAlgorithm")
    comments: Optional[str] = Field(default=None, alias="dhcpComments")
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.TSIG_KEY,
        alias="objectType",
    )

    model_config = {"populate_by_name": True}


class TsigKeyListResponse(PaginatedResponse):
    """Paginated list of TSIG keys."""

    items: List[TsigKeyListItem]
