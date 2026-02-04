"""
Heracles API Schemas
====================

Pydantic models for request/response validation.
"""

from heracles_api.schemas.user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    SetPasswordRequest,
)

from heracles_api.schemas.group import (
    GroupBase,
    GroupCreate,
    GroupUpdate,
    GroupResponse,
    GroupListResponse,
    MemberOperation,
)

from heracles_api.schemas.role import (
    RoleBase,
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleListResponse,
    RoleMemberOperation,
)

from heracles_api.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    UserInfoResponse,
    PasswordChangeRequest,
    PasswordResetRequest,
)

from heracles_api.schemas.department import (
    DepartmentBase,
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse,
    DepartmentTreeNode,
    DepartmentListResponse,
    DepartmentTreeResponse,
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

