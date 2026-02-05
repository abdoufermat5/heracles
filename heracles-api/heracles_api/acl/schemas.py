"""
ACL Schemas
===========

Pydantic models for ACL API endpoints.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Permission (read-only)
# ============================================================================


class PermissionResponse(BaseModel):
    """A registered permission."""
    
    bit_position: int = Field(..., description="Bit position in the permission bitmap")
    name: str = Field(..., description="Permission name (scope:action)")
    scope: str = Field(..., description="Object scope (user, group, etc.)")
    action: str = Field(..., description="Action (read, write, create, delete, manage)")
    description: str = Field(..., description="Human-readable description")
    plugin: Optional[str] = Field(None, description="Plugin that defines this permission (null=core)")
    
    model_config = {"from_attributes": True}


# ============================================================================
# Attribute Groups (read-only)
# ============================================================================


class AttributeGroupResponse(BaseModel):
    """A registered attribute group."""
    
    id: int = Field(..., description="Group ID")
    object_type: str = Field(..., description="Object type (user, group, system)")
    group_name: str = Field(..., alias="groupName", description="Group name (identity, contact, security)")
    label: str = Field(..., description="Human-readable label")
    attributes: list[str] = Field(..., description="LDAP attribute names in this group")
    plugin: Optional[str] = Field(None, description="Plugin that defines this group (null=core)")
    
    model_config = {"from_attributes": True, "populate_by_name": True}


# ============================================================================
# Policies
# ============================================================================


class PolicyResponse(BaseModel):
    """An ACL policy."""
    
    id: UUID = Field(..., description="Policy UUID")
    name: str = Field(..., description="Policy name")
    description: Optional[str] = Field(None, description="Policy description")
    permissions: list[str] = Field(..., description="List of permission names (scope:action)")
    builtin: bool = Field(..., description="Whether this is a built-in policy")
    created_at: datetime = Field(..., alias="createdAt", description="Creation timestamp")
    updated_at: datetime = Field(..., alias="updatedAt", description="Last update timestamp")
    
    model_config = {"from_attributes": True, "populate_by_name": True}


class PolicyListResponse(BaseModel):
    """Paginated list of policies."""
    
    policies: list[PolicyResponse]
    total: int
    page: int
    page_size: int = Field(..., alias="pageSize")
    has_more: bool = Field(..., alias="hasMore")
    
    model_config = {"populate_by_name": True}


class PolicyCreate(BaseModel):
    """Create a new policy."""
    
    name: str = Field(..., min_length=1, max_length=128, description="Policy name")
    description: Optional[str] = Field(None, max_length=1024, description="Policy description")
    permissions: list[str] = Field(..., min_length=1, description="List of permission names")


class PolicyUpdate(BaseModel):
    """Update an existing policy."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=128, description="Policy name")
    description: Optional[str] = Field(None, max_length=1024, description="Policy description")
    permissions: Optional[list[str]] = Field(None, description="List of permission names")


# ============================================================================
# Assignments
# ============================================================================


class AssignmentResponse(BaseModel):
    """An ACL assignment."""
    
    id: UUID = Field(..., description="Assignment UUID")
    policy_id: UUID = Field(..., alias="policyId", description="Policy UUID")
    policy_name: str = Field(..., alias="policyName", description="Policy name")
    subject_type: str = Field(..., alias="subjectType", description="Subject type (user, group, role)")
    subject_dn: str = Field(..., alias="subjectDn", description="Subject DN")
    scope_dn: str = Field(..., alias="scopeDn", description="Scope DN (empty=global)")
    scope_type: str = Field(..., alias="scopeType", description="Scope type (base, subtree)")
    self_only: bool = Field(..., alias="selfOnly", description="Only applies to own entry")
    deny: bool = Field(..., description="Deny (negate) permissions")
    priority: int = Field(..., description="Priority (higher=later evaluation)")
    created_at: datetime = Field(..., alias="createdAt", description="Creation timestamp")
    
    model_config = {"from_attributes": True, "populate_by_name": True}


class AssignmentListResponse(BaseModel):
    """Paginated list of assignments."""
    
    assignments: list[AssignmentResponse]
    total: int
    page: int
    page_size: int = Field(..., alias="pageSize")
    has_more: bool = Field(..., alias="hasMore")
    
    model_config = {"populate_by_name": True}


class AssignmentCreate(BaseModel):
    """Create a new assignment."""
    
    policy_id: UUID = Field(..., alias="policyId", description="Policy UUID")
    subject_type: str = Field(..., alias="subjectType", pattern="^(user|group|role)$", description="Subject type")
    subject_dn: str = Field(..., alias="subjectDn", min_length=1, description="Subject DN")
    scope_dn: Optional[str] = Field("", alias="scopeDn", description="Scope DN (empty=global)")
    scope_type: Optional[str] = Field("subtree", alias="scopeType", pattern="^(base|subtree)$", description="Scope type")
    self_only: Optional[bool] = Field(False, alias="selfOnly", description="Only applies to own entry")
    deny: Optional[bool] = Field(False, description="Deny (negate) permissions")
    priority: Optional[int] = Field(0, ge=0, le=1000, description="Priority")
    
    model_config = {"populate_by_name": True}


# ============================================================================
# My Permissions
# ============================================================================


class MyPermissionsResponse(BaseModel):
    """Current user's effective permissions."""
    
    user_dn: str = Field(..., alias="userDn", description="User DN")
    permissions: list[str] = Field(..., description="List of effective permission names")
    
    model_config = {"populate_by_name": True}
