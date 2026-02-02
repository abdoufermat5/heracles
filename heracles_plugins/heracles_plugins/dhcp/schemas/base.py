"""
DHCP Base Schemas
=================

Base Pydantic models for DHCP objects.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class DhcpBase(BaseModel):
    """Base attributes for all DHCP objects."""

    dhcp_statements: List[str] = Field(
        default_factory=list,
        alias="dhcpStatements",
        description="DHCP configuration statements",
    )
    dhcp_options: List[str] = Field(
        default_factory=list,
        alias="dhcpOption",
        description="DHCP options to send to clients",
    )
    comments: Optional[str] = Field(
        default=None,
        alias="dhcpComments",
        max_length=1024,
        description="Comments/description",
    )

    @field_validator("dhcp_statements", "dhcp_options", mode="before")
    @classmethod
    def ensure_list(cls, v):
        """Ensure value is a list."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return list(v)

    model_config = {"populate_by_name": True}


class PaginatedResponse(BaseModel):
    """Base for paginated list responses."""

    total: int
    page: int = 1
    page_size: int = 50
