"""
DHCP Group Schemas
==================

Pydantic models for DHCP group objects.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

from .base import DhcpBase, PaginatedResponse
from .enums import DhcpObjectType
from .validators import validate_cn_alphanumeric


class GroupCreate(DhcpBase):
    """Schema for creating a DHCP group."""

    cn: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Group name",
    )

    @field_validator("cn")
    @classmethod
    def validate_cn(cls, v):
        """Validate group name."""
        return validate_cn_alphanumeric(v)


class GroupUpdate(DhcpBase):
    """Schema for updating a DHCP group."""
    pass


class GroupRead(DhcpBase):
    """Schema for reading a DHCP group."""

    dn: str = Field(..., description="Distinguished Name")
    cn: str = Field(..., description="Group name")
    parent_dn: Optional[str] = Field(
        default=None,
        alias="parentDn",
    )
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.GROUP,
        alias="objectType",
    )


class GroupListItem(BaseModel):
    """Schema for group in list responses."""

    dn: str
    cn: str
    comments: Optional[str] = Field(default=None, alias="dhcpComments")
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.GROUP,
        alias="objectType",
    )

    model_config = {"populate_by_name": True}


class GroupListResponse(PaginatedResponse):
    """Paginated list of groups."""

    items: List[GroupListItem]
