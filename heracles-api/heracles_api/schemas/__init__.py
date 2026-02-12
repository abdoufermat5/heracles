"""
Heracles API Schemas
====================

Pydantic models for request/response validation.
"""

from heracles_api.schemas.auth import (
    LoginRequest,
    PasswordChangeRequest,
    PasswordResetRequest,
    RefreshRequest,
    TokenResponse,
    UserInfoResponse,
)
from heracles_api.schemas.department import (
    DepartmentBase,
    DepartmentCreate,
    DepartmentListResponse,
    DepartmentResponse,
    DepartmentTreeNode,
    DepartmentTreeResponse,
    DepartmentUpdate,
)
from heracles_api.schemas.group import (
    GroupBase,
    GroupCreate,
    GroupListResponse,
    GroupResponse,
    GroupUpdate,
    MemberOperation,
)
from heracles_api.schemas.role import (
    RoleBase,
    RoleCreate,
    RoleListResponse,
    RoleMemberOperation,
    RoleResponse,
    RoleUpdate,
)
from heracles_api.schemas.user import (
    SetPasswordRequest,
    UserBase,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)

__all__ = [
    # User
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserListResponse",
    "SetPasswordRequest",
    # Group
    "GroupBase",
    "GroupCreate",
    "GroupUpdate",
    "GroupResponse",
    "GroupListResponse",
    "MemberOperation",
    # Role
    "RoleBase",
    "RoleCreate",
    "RoleUpdate",
    "RoleResponse",
    "RoleListResponse",
    "RoleMemberOperation",
    # Auth
    "LoginRequest",
    "TokenResponse",
    "RefreshRequest",
    "UserInfoResponse",
    "PasswordChangeRequest",
    "PasswordResetRequest",
    # Department
    "DepartmentBase",
    "DepartmentCreate",
    "DepartmentUpdate",
    "DepartmentResponse",
    "DepartmentTreeNode",
    "DepartmentListResponse",
    "DepartmentTreeResponse",
]
