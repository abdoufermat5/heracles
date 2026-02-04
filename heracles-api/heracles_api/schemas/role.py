"""
Role Schemas
============

Pydantic models for role-related requests and responses.

Roles use the standard LDAP organizationalRole objectClass with
roleOccupant attribute for member tracking.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class RoleBase(BaseModel):
    """Base role model."""
    cn: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")
    description: Optional[str] = Field(None, max_length=256)


class RoleCreate(RoleBase):
    """Role creation model."""
    department_dn: Optional[str] = Field(
        None,
        alias="departmentDn",
        description="Department DN (role will be created under ou=roles within this department)"
    )
    members: List[str] = Field(default_factory=list, description="List of member UIDs")


class RoleUpdate(BaseModel):
    """Role update model."""
    description: Optional[str] = Field(None, max_length=256)


class RoleResponse(BaseModel):
    """Role response model."""
    dn: str
    cn: str
    description: Optional[str] = None
    members: List[str] = Field(default_factory=list, description="List of member UIDs")
    member_count: int = Field(default=0, alias="memberCount")
    
    class Config:
        populate_by_name = True


class RoleListResponse(BaseModel):
    """Paginated role list response."""
    roles: List[RoleResponse]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")
    has_more: bool = Field(alias="hasMore")
    
    class Config:
        populate_by_name = True


class RoleMemberOperation(BaseModel):
    """Add/remove member operation."""
    uid: str = Field(..., description="User UID to add/remove")
