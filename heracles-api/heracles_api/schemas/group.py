"""
Group Schemas
=============

Pydantic models for group-related requests and responses.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class GroupBase(BaseModel):
    """Base group model."""
    cn: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")
    description: Optional[str] = Field(None, max_length=256)


class GroupCreate(GroupBase):
    """Group creation model."""
    ou: str = Field(default="groups", description="Organizational unit")
    members: List[str] = Field(default_factory=list, description="List of member UIDs")


class GroupUpdate(BaseModel):
    """Group update model."""
    description: Optional[str] = Field(None, max_length=256)


class GroupResponse(BaseModel):
    """Group response model."""
    dn: str
    cn: str
    description: Optional[str] = None
    members: List[str] = Field(default_factory=list, description="List of member UIDs")


class GroupListResponse(BaseModel):
    """Paginated group list response."""
    groups: List[GroupResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class MemberOperation(BaseModel):
    """Add/remove member operation."""
    uid: str = Field(..., description="User UID to add/remove")
