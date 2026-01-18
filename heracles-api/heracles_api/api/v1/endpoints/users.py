"""
Users Endpoints
===============

User management endpoints (CRUD operations).
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query

from heracles_api.core.dependencies import CurrentUser, UserRepoDep, GroupRepoDep
from heracles_api.schemas import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    SetPasswordRequest,
)
from heracles_api.services import LdapOperationError

import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()


def _entry_to_response(entry, groups: list[str] = None) -> UserResponse:
    """Convert LDAP entry to UserResponse."""
    return UserResponse(
        dn=entry.dn,
        uid=entry.get_first("uid", ""),
        cn=entry.get_first("cn", ""),
        sn=entry.get_first("sn", ""),
        givenName=entry.get_first("givenName"),
        mail=entry.get_first("mail"),
        telephoneNumber=entry.get_first("telephoneNumber"),
        title=entry.get_first("title"),
        description=entry.get_first("description"),
        memberOf=groups or [],
    )


@router.get("", response_model=UserListResponse)
async def list_users(
    current_user: CurrentUser,
    user_repo: UserRepoDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None, description="Search in uid, cn, mail"),
    ou: Optional[str] = Query(None, description="Filter by organizational unit"),
):
    """
    List all users with pagination.
    """
    try:
        result = await user_repo.search(search_term=search, ou=ou)
        
        total = result.total
        
        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size
        page_entries = result.users[start:end]
        
        # Get group memberships for each user
        users = []
        for entry in page_entries:
            groups = await user_repo.get_groups(entry.dn)
            users.append(_entry_to_response(entry, groups))
        
        return UserListResponse(
            users=users,
            total=total,
            page=page,
            page_size=page_size,
            has_more=end < total,
        )
        
    except LdapOperationError as e:
        logger.error("list_users_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users",
        )


@router.get("/{uid}", response_model=UserResponse)
async def get_user(
    uid: str,
    current_user: CurrentUser,
    user_repo: UserRepoDep,
):
    """
    Get user by UID.
    """
    try:
        entry = await user_repo.find_by_uid(uid)
        
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{uid}' not found",
            )
        
        groups = await user_repo.get_groups(entry.dn)
        return _entry_to_response(entry, groups)
        
    except LdapOperationError as e:
        logger.error("get_user_failed", uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user",
        )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate,
    current_user: CurrentUser,
    user_repo: UserRepoDep,
):
    """
    Create a new user.
    """
    # Check if user already exists
    if await user_repo.exists(user.uid):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User '{user.uid}' already exists",
        )
    
    try:
        entry = await user_repo.create(user)
        
        logger.info("user_created", uid=user.uid, by=current_user.uid)
        
        return _entry_to_response(entry, [])
        
    except LdapOperationError as e:
        logger.error("create_user_failed", uid=user.uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {e}",
        )


@router.patch("/{uid}", response_model=UserResponse)
async def update_user(
    uid: str,
    updates: UserUpdate,
    current_user: CurrentUser,
    user_repo: UserRepoDep,
):
    """
    Update user attributes.
    """
    try:
        entry = await user_repo.update(uid, updates)
        
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{uid}' not found",
            )
        
        logger.info("user_updated", uid=uid, by=current_user.uid)
        
        groups = await user_repo.get_groups(entry.dn)
        return _entry_to_response(entry, groups)
        
    except LdapOperationError as e:
        logger.error("update_user_failed", uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {e}",
        )


@router.delete("/{uid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    uid: str,
    current_user: CurrentUser,
    user_repo: UserRepoDep,
    group_repo: GroupRepoDep,
):
    """
    Delete a user.
    """
    # Prevent self-deletion
    if uid == current_user.uid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    
    # Find user
    entry = await user_repo.find_by_uid(uid)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{uid}' not found",
        )
    
    try:
        # Remove user from all groups first
        await group_repo.remove_user_from_all_groups(entry.dn)
        
        # Delete user
        await user_repo.delete(uid)
        
        logger.info("user_deleted", uid=uid, by=current_user.uid)
        
    except LdapOperationError as e:
        logger.error("delete_user_failed", uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {e}",
        )


@router.post("/{uid}/password", status_code=status.HTTP_204_NO_CONTENT)
async def set_user_password(
    uid: str,
    request: SetPasswordRequest,
    current_user: CurrentUser,
    user_repo: UserRepoDep,
):
    """
    Set user password (admin operation).
    """
    if not await user_repo.exists(uid):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{uid}' not found",
        )
    
    try:
        await user_repo.set_password(uid, request.password)
        
        logger.info("user_password_set", uid=uid, by=current_user.uid)
        
    except LdapOperationError as e:
        logger.error("set_password_failed", uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set password: {e}",
        )
