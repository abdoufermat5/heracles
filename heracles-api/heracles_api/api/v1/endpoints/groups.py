"""
Groups Endpoints
================

Group management endpoints (CRUD operations).
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query

from heracles_api.core.dependencies import CurrentUser, UserRepoDep, GroupRepoDep
from heracles_api.schemas import (
    GroupCreate,
    GroupUpdate,
    GroupResponse,
    GroupListResponse,
    MemberOperation,
)
from heracles_api.services import LdapOperationError

import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()


def _entry_to_response(entry, members: list[str] = None) -> GroupResponse:
    """Convert LDAP entry to GroupResponse."""
    return GroupResponse(
        dn=entry.dn,
        cn=entry.get_first("cn", ""),
        description=entry.get_first("description"),
        members=members or [],
    )


@router.get("", response_model=GroupListResponse)
async def list_groups(
    current_user: CurrentUser,
    group_repo: GroupRepoDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None, description="Search in cn, description"),
    ou: Optional[str] = Query(None, description="Filter by organizational unit"),
):
    """
    List all groups with pagination.
    """
    try:
        result = await group_repo.search(search_term=search, ou=ou)
        
        total = result.total
        
        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size
        page_entries = result.groups[start:end]
        
        groups = []
        for entry in page_entries:
            members = await group_repo.get_members(entry.get_first("cn", ""))
            groups.append(_entry_to_response(entry, members))
        
        return GroupListResponse(
            groups=groups,
            total=total,
            page=page,
            page_size=page_size,
            has_more=end < total,
        )
        
    except LdapOperationError as e:
        logger.error("list_groups_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list groups",
        )


@router.get("/{cn}", response_model=GroupResponse)
async def get_group(
    cn: str,
    current_user: CurrentUser,
    group_repo: GroupRepoDep,
):
    """
    Get group by CN.
    """
    try:
        entry = await group_repo.find_by_cn(cn)
        
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group '{cn}' not found",
            )
        
        members = await group_repo.get_members(cn)
        return _entry_to_response(entry, members)
        
    except LdapOperationError as e:
        logger.error("get_group_failed", cn=cn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get group",
        )


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    group: GroupCreate,
    current_user: CurrentUser,
    user_repo: UserRepoDep,
    group_repo: GroupRepoDep,
):
    """
    Create a new group.
    """
    # Check if group already exists
    if await group_repo.exists(group.cn):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Group '{group.cn}' already exists",
        )
    
    # Resolve member UIDs to DNs
    member_dns = []
    for uid in group.members:
        user = await user_repo.find_by_uid(uid)
        if user:
            member_dns.append(user.dn)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User '{uid}' not found",
            )
    
    try:
        entry = await group_repo.create(
            group=group,
            member_dns=member_dns,
            default_member_dn=current_user.user_dn,
        )
        
        logger.info("group_created", cn=group.cn, by=current_user.uid)
        
        members = group.members if group.members else [current_user.uid]
        return _entry_to_response(entry, members)
        
    except LdapOperationError as e:
        logger.error("create_group_failed", cn=group.cn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create group: {e}",
        )


@router.patch("/{cn}", response_model=GroupResponse)
async def update_group(
    cn: str,
    updates: GroupUpdate,
    current_user: CurrentUser,
    group_repo: GroupRepoDep,
):
    """
    Update group attributes.
    """
    try:
        entry = await group_repo.update(cn, updates)
        
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group '{cn}' not found",
            )
        
        logger.info("group_updated", cn=cn, by=current_user.uid)
        
        members = await group_repo.get_members(cn)
        return _entry_to_response(entry, members)
        
    except LdapOperationError as e:
        logger.error("update_group_failed", cn=cn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update group: {e}",
        )


@router.delete("/{cn}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    cn: str,
    current_user: CurrentUser,
    group_repo: GroupRepoDep,
):
    """
    Delete a group.
    """
    if not await group_repo.exists(cn):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group '{cn}' not found",
        )
    
    try:
        await group_repo.delete(cn)
        
        logger.info("group_deleted", cn=cn, by=current_user.uid)
        
    except LdapOperationError as e:
        logger.error("delete_group_failed", cn=cn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete group: {e}",
        )


@router.post("/{cn}/members", status_code=status.HTTP_204_NO_CONTENT)
async def add_group_member(
    cn: str,
    member: MemberOperation,
    current_user: CurrentUser,
    user_repo: UserRepoDep,
    group_repo: GroupRepoDep,
):
    """
    Add a member to a group.
    """
    if not await group_repo.exists(cn):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group '{cn}' not found",
        )
    
    # Get user DN
    user = await user_repo.find_by_uid(member.uid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{member.uid}' not found",
        )
    
    try:
        await group_repo.add_member(cn, user.dn)
        
        logger.info("group_member_added", cn=cn, uid=member.uid, by=current_user.uid)
        
    except LdapOperationError as e:
        if "already exists" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User '{member.uid}' is already a member of '{cn}'",
            )
        logger.error("add_member_failed", cn=cn, uid=member.uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add member: {e}",
        )


@router.delete("/{cn}/members/{uid}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_group_member(
    cn: str,
    uid: str,
    current_user: CurrentUser,
    user_repo: UserRepoDep,
    group_repo: GroupRepoDep,
):
    """
    Remove a member from a group.
    """
    if not await group_repo.exists(cn):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group '{cn}' not found",
        )
    
    # Get user DN
    user = await user_repo.find_by_uid(uid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{uid}' not found",
        )
    
    try:
        await group_repo.remove_member(cn, user.dn)
        
        logger.info("group_member_removed", cn=cn, uid=uid, by=current_user.uid)
        
    except LdapOperationError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{uid}' is not a member of '{cn}'",
            )
        if "last member" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last member of a group",
            )
        logger.error("remove_member_failed", cn=cn, uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove member: {e}",
        )
