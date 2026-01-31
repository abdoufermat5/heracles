"""
Department Schemas
==================

Pydantic models for department-related requests and responses.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class DepartmentBase(BaseModel):
    """Base department model."""
    ou: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9._-]+$",
        description="Organizational unit name"
    )
    description: Optional[str] = Field(None, max_length=256)


class DepartmentCreate(DepartmentBase):
    """Department creation model."""
    parent_dn: Optional[str] = Field(
        None,
        alias="parentDn",
        description="Parent DN (department will be created under this DN)"
    )
    category: Optional[str] = Field(
        None,
        max_length=64,
        alias="hrcDepartmentCategory",
        description="Department category (e.g., division, team, project)"
    )
    manager_dn: Optional[str] = Field(
        None,
        alias="hrcDepartmentManager",
        description="DN of department manager"
    )


class DepartmentUpdate(BaseModel):
    """Department update model."""
    description: Optional[str] = Field(None, max_length=256)
    category: Optional[str] = Field(
        None,
        max_length=64,
        alias="hrcDepartmentCategory",
        description="Department category (e.g., division, team, project)"
    )
    manager_dn: Optional[str] = Field(
        None,
        alias="hrcDepartmentManager",
        description="DN of department manager"
    )


class DepartmentResponse(BaseModel):
    """Department response model."""
    dn: str
    ou: str
    description: Optional[str] = None
    path: str = Field(..., description="Human-readable path (e.g., /Engineering/DevOps)")
    parent_dn: Optional[str] = Field(None, alias="parentDn")
    children_count: int = Field(0, alias="childrenCount")
    category: Optional[str] = Field(None, alias="hrcDepartmentCategory")
    manager_dn: Optional[str] = Field(None, alias="hrcDepartmentManager")

    class Config:
        populate_by_name = True


class DepartmentTreeNode(BaseModel):
    """Department tree node for hierarchical display."""
    dn: str
    ou: str
    description: Optional[str] = None
    path: str
    depth: int
    children: List["DepartmentTreeNode"] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class DepartmentListResponse(BaseModel):
    """Department list response."""
    departments: List[DepartmentResponse]
    total: int


class DepartmentTreeResponse(BaseModel):
    """Department tree response."""
    tree: List[DepartmentTreeNode]
    total: int
