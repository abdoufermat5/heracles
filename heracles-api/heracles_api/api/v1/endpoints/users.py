"""
User Management Endpoints
=========================

CRUD operations for LDAP users.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, EmailStr

router = APIRouter()


# ===========================================
# Pydantic Models
# ===========================================

class UserBase(BaseModel):
    """Base user model."""
    uid: str
    cn: str
    sn: str
    given_name: Optional[str] = None
    mail: Optional[EmailStr] = None
    telephone_number: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None


class UserCreate(UserBase):
    """User creation model."""
    password: str
    uid_number: Optional[int] = None  # Auto-generated if not provided
    gid_number: int
    home_directory: Optional[str] = None  # Auto-generated if not provided
    login_shell: str = "/bin/bash"


class UserUpdate(BaseModel):
    """User update model (all fields optional)."""
    cn: Optional[str] = None
    sn: Optional[str] = None
    given_name: Optional[str] = None
    mail: Optional[EmailStr] = None
    telephone_number: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    login_shell: Optional[str] = None


class UserResponse(UserBase):
    """User response model."""
    dn: str
    uid_number: int
    gid_number: int
    home_directory: str
    login_shell: str
    object_classes: List[str]


class UserListResponse(BaseModel):
    """Paginated user list response."""
    items: List[UserResponse]
    total: int
    page: int
    page_size: int


class PasswordChange(BaseModel):
    """Password change request."""
    current_password: str
    new_password: str


# ===========================================
# Endpoints
# ===========================================

@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = None,
    filter_by: Optional[str] = None,
):
    """
    List all users with pagination.
    
    - **page**: Page number (1-indexed)
    - **page_size**: Items per page (max 100)
    - **search**: Search in cn, uid, mail
    - **filter_by**: LDAP filter to apply
    """
    # TODO: Implement LDAP search
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User listing not yet implemented"
    )


@router.get("/{uid}", response_model=UserResponse)
async def get_user(uid: str):
    """
    Get a single user by UID.
    """
    # TODO: Implement LDAP search for single user
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User retrieval not yet implemented"
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    """
    Create a new user.
    
    Creates an inetOrgPerson with posixAccount attributes.
    """
    # TODO: Implement LDAP add
    # 1. Validate user data
    # 2. Auto-generate uidNumber if not provided
    # 3. Auto-generate homeDirectory if not provided
    # 4. Hash password
    # 5. Add to LDAP
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User creation not yet implemented"
    )


@router.put("/{uid}", response_model=UserResponse)
async def update_user(uid: str, user: UserUpdate):
    """
    Update an existing user.
    """
    # TODO: Implement LDAP modify
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User update not yet implemented"
    )


@router.delete("/{uid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(uid: str):
    """
    Delete a user.
    """
    # TODO: Implement LDAP delete
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User deletion not yet implemented"
    )


@router.post("/{uid}/password")
async def change_password(uid: str, password_change: PasswordChange):
    """
    Change user password.
    
    Requires current password for verification.
    """
    # TODO: Implement password change
    # 1. Verify current password
    # 2. Hash new password
    # 3. Update LDAP
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Password change not yet implemented"
    )


@router.post("/{uid}/password/admin")
async def admin_reset_password(uid: str, new_password: str):
    """
    Admin password reset (no current password required).
    
    Requires admin privileges.
    """
    # TODO: Implement admin password reset
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Admin password reset not yet implemented"
    )


@router.get("/{uid}/groups", response_model=List[str])
async def get_user_groups(uid: str):
    """
    Get groups that a user belongs to.
    """
    # TODO: Implement group membership lookup
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User groups not yet implemented"
    )
