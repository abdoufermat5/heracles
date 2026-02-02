"""
DHCP Class Schemas
==================

Pydantic models for DHCP class and subclass objects.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

from .base import DhcpBase, PaginatedResponse
from .enums import DhcpObjectType
from .validators import validate_cn_alphanumeric


class DhcpClassCreate(DhcpBase):
    """Schema for creating a DHCP class."""

    cn: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Class name",
    )

    @field_validator("cn")
    @classmethod
    def validate_cn(cls, v):
        """Validate class name."""
        return validate_cn_alphanumeric(v)


class DhcpClassUpdate(DhcpBase):
    """Schema for updating a DHCP class."""
    pass


class DhcpClassRead(DhcpBase):
    """Schema for reading a DHCP class."""

    dn: str = Field(..., description="Distinguished Name")
    cn: str = Field(..., description="Class name")
    parent_dn: Optional[str] = Field(
        default=None,
        alias="parentDn",
    )
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.CLASS,
        alias="objectType",
    )


class DhcpClassListItem(BaseModel):
    """Schema for class in list responses."""

    dn: str
    cn: str
    comments: Optional[str] = Field(default=None, alias="dhcpComments")
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.CLASS,
        alias="objectType",
    )

    model_config = {"populate_by_name": True}


class DhcpClassListResponse(PaginatedResponse):
    """Paginated list of classes."""

    items: List[DhcpClassListItem]


# SubClass schemas
class SubClassCreate(DhcpBase):
    """Schema for creating a DHCP subclass."""

    cn: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Subclass name",
    )
    dhcp_class_data: Optional[str] = Field(
        default=None,
        alias="dhcpClassData",
        description="Class data for client matching",
    )


class SubClassUpdate(DhcpBase):
    """Schema for updating a DHCP subclass."""

    dhcp_class_data: Optional[str] = Field(
        default=None,
        alias="dhcpClassData",
    )


class SubClassRead(DhcpBase):
    """Schema for reading a DHCP subclass."""

    dn: str = Field(..., description="Distinguished Name")
    cn: str = Field(..., description="Subclass name")
    dhcp_class_data: Optional[str] = Field(
        default=None,
        alias="dhcpClassData",
    )
    parent_dn: Optional[str] = Field(
        default=None,
        alias="parentDn",
    )
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.SUBCLASS,
        alias="objectType",
    )
