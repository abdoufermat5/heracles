"""
Group Management Endpoints
==========================

CRUD operations for LDAP groups.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

router = APIRouter()


# ===========================================
# Pydantic Models
# ===========================================

class GroupBase(BaseModel):
    """Base group model."""
    cn: str
    description: Optional[str] = None


class GroupCreate(GroupBase):
    """Group creation model."""
    gid_number: Optional[int] = None  # Auto-generated if not provided
    member_uids: List[str] = []


class GroupUpdate(BaseModel):
    """Group update model (all fields optional)."""
    description: Optional[str] = None


class GroupResponse(GroupBase):
    """Group response model."""
    dn: str
    gid_number: int
    member_uids: List[str]


class GroupListResponse(BaseModel):
    """Paginated group list response."""
    items: List[GroupResponse]
    total: int
    page: int
    page_size: int


class MemberOperation(BaseModel):
    """Add/remove member operation."""
    uid: str


# ===========================================
# Endpoints
# ===========================================

@router.get("", response_model=GroupListResponse)
async def list_groups(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = None,
):
    """
    List all groups with pagination.
    
    - **page**: Page number (1-indexed)
    - **page_size**: Items per page (max 100)
    - **search**: Search in cn, description
    """
    # TODO: Implement LDAP search
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Group listing not yet implemented"
    )


@router.get("/{cn}", response_model=GroupResponse)
async def get_group(cn: str):
    """
    Get a single group by CN.
    """
    # TODO: Implement LDAP search for single group
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Group retrieval not yet implemented"
    )


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(group: GroupCreate):
    """
    Create a new POSIX group.
    """
    # TODO: Implement LDAP add
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Group creation not yet implemented"
    )


@router.put("/{cn}", response_model=GroupResponse)
async def update_group(cn: str, group: GroupUpdate):
    """
    Update an existing group.
    """
    # TODO: Implement LDAP modify
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Group update not yet implemented"
    )


@router.delete("/{cn}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(cn: str):
    """
    Delete a group.
    """
    # TODO: Implement LDAP delete
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Group deletion not yet implemented"
    )


@router.post("/{cn}/members", status_code=status.HTTP_204_NO_CONTENT)
async def add_member(cn: str, member: MemberOperation):
    """
    Add a member to a group.
    """
    # TODO: Implement LDAP modify (add memberUid)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Add member not yet implemented"
    )


@router.delete("/{cn}/members/{uid}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(cn: str, uid: str):
    """
    Remove a member from a group.
    """
    # TODO: Implement LDAP modify (delete memberUid)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Remove member not yet implemented"
    )


@router.get("/{cn}/members", response_model=List[str])
async def list_members(cn: str):
    """
    List all members of a group.
    """
    # TODO: Implement member listing
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="List members not yet implemented"
    )
