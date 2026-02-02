"""
DHCP Tree Schemas
=================

Pydantic models for DHCP configuration tree/hierarchy.
"""

from typing import Optional, List
from pydantic import BaseModel, Field

from .enums import DhcpObjectType


class DhcpTreeNode(BaseModel):
    """Node in the DHCP configuration tree."""

    dn: str
    cn: str
    object_type: DhcpObjectType = Field(..., alias="objectType")
    comments: Optional[str] = Field(default=None, alias="dhcpComments")
    children: List["DhcpTreeNode"] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class DhcpTreeResponse(BaseModel):
    """Full DHCP configuration tree response."""

    service: DhcpTreeNode


# Generic DHCP object schemas for dynamic operations
class DhcpObjectCreate(BaseModel):
    """Generic schema for creating any DHCP object."""

    cn: str
    object_type: DhcpObjectType = Field(..., alias="objectType")
    parent_dn: str = Field(..., alias="parentDn")
    attributes: dict = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class DhcpObjectRead(BaseModel):
    """Generic schema for reading any DHCP object."""

    dn: str
    cn: str
    object_type: DhcpObjectType = Field(..., alias="objectType")
    parent_dn: Optional[str] = Field(default=None, alias="parentDn")
    attributes: dict = Field(default_factory=dict)

    model_config = {"populate_by_name": True}
