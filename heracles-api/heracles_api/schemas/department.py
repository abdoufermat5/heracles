"""
Department Schemas
==================

Pydantic models for department-related requests and responses.
"""

from pydantic import BaseModel, Field


class DepartmentBase(BaseModel):
    """Base department model."""

    ou: str = Field(
        ..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$", description="Organizational unit name"
    )
    description: str | None = Field(None, max_length=256)


class DepartmentCreate(DepartmentBase):
    """Department creation model."""

    parent_dn: str | None = Field(
        None, alias="parentDn", description="Parent DN (department will be created under this DN)"
    )
    category: str | None = Field(
        None,
        max_length=64,
        alias="hrcDepartmentCategory",
        description="Department category (e.g., division, team, project)",
    )
    manager_dn: str | None = Field(None, alias="hrcDepartmentManager", description="DN of department manager")


class DepartmentUpdate(BaseModel):
    """Department update model."""

    description: str | None = Field(None, max_length=256)
    category: str | None = Field(
        None,
        max_length=64,
        alias="hrcDepartmentCategory",
        description="Department category (e.g., division, team, project)",
    )
    manager_dn: str | None = Field(None, alias="hrcDepartmentManager", description="DN of department manager")


class DepartmentResponse(BaseModel):
    """Department response model."""

    dn: str
    ou: str
    description: str | None = None
    path: str = Field(..., description="Human-readable path (e.g., /Engineering/DevOps)")
    parent_dn: str | None = Field(None, alias="parentDn")
    children_count: int = Field(0, alias="childrenCount")
    category: str | None = Field(None, alias="hrcDepartmentCategory")
    manager_dn: str | None = Field(None, alias="hrcDepartmentManager")

    class Config:
        populate_by_name = True


class DepartmentTreeNode(BaseModel):
    """Department tree node for hierarchical display."""

    dn: str
    ou: str
    description: str | None = None
    path: str
    depth: int
    children: list["DepartmentTreeNode"] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class DepartmentListResponse(BaseModel):
    """Department list response."""

    departments: list[DepartmentResponse]
    total: int


class DepartmentTreeResponse(BaseModel):
    """Department tree response."""

    tree: list[DepartmentTreeNode]
    total: int
