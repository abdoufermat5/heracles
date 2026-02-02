"""
DHCP Host Schemas
=================

Pydantic models for DHCP host reservation objects.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, model_validator

from .base import DhcpBase, PaginatedResponse
from .enums import DhcpObjectType
from .validators import validate_ip_address, validate_mac_address


class HostCreate(DhcpBase):
    """Schema for creating a DHCP host reservation."""

    cn: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Hostname",
    )
    dhcp_hw_address: str = Field(
        ...,
        alias="dhcpHWAddress",
        description="Hardware address (MAC)",
    )
    fixed_address: Optional[str] = Field(
        default=None,
        alias="fixedAddress",
        description="Fixed IP address (stored in dhcpStatements)",
    )
    system_dn: Optional[str] = Field(
        default=None,
        alias="systemDn",
        description="DN of linked system (from systems plugin)",
    )

    @field_validator("dhcp_hw_address")
    @classmethod
    def validate_hw_address(cls, v):
        """Validate and normalize hardware address."""
        return validate_mac_address(v)

    @field_validator("fixed_address")
    @classmethod
    def validate_fixed_address(cls, v):
        """Validate fixed IP address."""
        if v is not None:
            return validate_ip_address(v)
        return v

    @model_validator(mode="after")
    def add_fixed_address_statement(self):
        """Add fixed-address to dhcpStatements if provided."""
        if self.fixed_address:
            statement = f"fixed-address {self.fixed_address}"
            if statement not in self.dhcp_statements:
                self.dhcp_statements.append(statement)
        return self


class HostUpdate(DhcpBase):
    """Schema for updating a DHCP host."""

    dhcp_hw_address: Optional[str] = Field(
        default=None,
        alias="dhcpHWAddress",
    )
    fixed_address: Optional[str] = Field(
        default=None,
        alias="fixedAddress",
    )
    system_dn: Optional[str] = Field(
        default=None,
        alias="systemDn",
    )

    @field_validator("dhcp_hw_address")
    @classmethod
    def validate_hw_address(cls, v):
        """Validate and normalize hardware address."""
        if v is not None:
            return validate_mac_address(v)
        return v

    @field_validator("fixed_address")
    @classmethod
    def validate_fixed_address(cls, v):
        """Validate fixed IP address."""
        if v is not None:
            return validate_ip_address(v)
        return v


class HostRead(DhcpBase):
    """Schema for reading a DHCP host."""

    dn: str = Field(..., description="Distinguished Name")
    cn: str = Field(..., description="Hostname")
    dhcp_hw_address: Optional[str] = Field(
        default=None,
        alias="dhcpHWAddress",
    )
    fixed_address: Optional[str] = Field(
        default=None,
        alias="fixedAddress",
    )
    parent_dn: Optional[str] = Field(
        default=None,
        alias="parentDn",
    )
    system_dn: Optional[str] = Field(
        default=None,
        alias="systemDn",
    )
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.HOST,
        alias="objectType",
    )


class HostListItem(BaseModel):
    """Schema for host in list responses."""

    dn: str
    cn: str
    dhcp_hw_address: Optional[str] = Field(default=None, alias="dhcpHWAddress")
    fixed_address: Optional[str] = Field(default=None, alias="fixedAddress")
    comments: Optional[str] = Field(default=None, alias="dhcpComments")
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.HOST,
        alias="objectType",
    )

    model_config = {"populate_by_name": True}


class HostListResponse(PaginatedResponse):
    """Paginated list of hosts."""

    items: List[HostListItem]
