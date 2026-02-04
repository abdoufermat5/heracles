"""
Roles Endpoints
================

Role management endpoints (CRUD operations).

Roles use the standard LDAP organizationalRole objectClass
with roleOccupant attribute for member tracking.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query

from heracles_api.core.dependencies import CurrentUser, UserRepoDep, RoleRepoDep
from heracles_api.schemas import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleListResponse,
    RoleMemberOperation,
)
from heracles_api.services import LdapOperationError

import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()


def _entry_to_response(entry, members: list[str] = None) -> RoleResponse:
    """Convert LDAP entry to RoleResponse."""
    member_list = members or []
    return RoleResponse(
        dn=entry.dn,
        cn=entry.get_first("cn", ""),
        description=entry.get_first("description"),
        members=member_list,
        memberCount=len(member_list),
    )


@router.get("", response_model=RoleListResponse)
async def list_roles(
    current_user: CurrentUser,
    role_repo: RoleRepoDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None, description="Search in cn, description"),
    base: Optional[str] = Query(None, description="Base DN (e.g., department DN) for scoped search"),
):
    """
    List all roles with pagination.
    """
    try:
        result = await role_repo.search(search_term=search, base_dn=base)
        
        total = result.total
        
        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size
        page_entries = result.roles[start:end]
        
        roles = []
        for entry in page_entries:
            members = await role_repo.get_members(entry.get_first("cn", ""))
            roles.append(_entry_to_response(entry, members))
        
        return RoleListResponse(
            roles=roles,
            total=total,
            page=page,
            pageSize=page_size,
            hasMore=end < total,
        )
        
    except LdapOperationError as e:
        logger.error("list_roles_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list roles",
        )


@router.get("/{cn}", response_model=RoleResponse)
async def get_role(
    cn: str,
    current_user: CurrentUser,
    role_repo: RoleRepoDep,
):
    """
    Get role by CN.
    """
    try:
        entry = await role_repo.find_by_cn(cn)
        
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role '{cn}' not found",
            )
        
        members = await role_repo.get_members(cn)
        return _entry_to_response(entry, members)
        
    except LdapOperationError as e:
        logger.error("get_role_failed", cn=cn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get role",
        )


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role: RoleCreate,
    current_user: CurrentUser,
    user_repo: UserRepoDep,
    role_repo: RoleRepoDep,
):
    """
    Create a new role.
    """
    # Check if role already exists
    if await role_repo.exists(role.cn):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Role '{role.cn}' already exists",
        )
    
    # Resolve member UIDs to DNs
    member_dns = []
    for uid in role.members:
        user = await user_repo.find_by_uid(uid)
        if user:
            member_dns.append(user.dn)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User '{uid}' not found",
            )
    
    try:
        entry = await role_repo.create(
            role=role,
            member_dns=member_dns,
            department_dn=role.department_dn,
        )

        logger.info("role_created", cn=role.cn, department_dn=role.department_dn, by=current_user.uid)
        
        members = role.members if role.members else []
        return _entry_to_response(entry, members)
        
    except LdapOperationError as e:
        logger.error("create_role_failed", cn=role.cn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create role: {e}",
        )


@router.patch("/{cn}", response_model=RoleResponse)
async def update_role(
    cn: str,
    updates: RoleUpdate,
    current_user: CurrentUser,
    role_repo: RoleRepoDep,
):
    """
    Update role attributes.
    """
    try:
        entry = await role_repo.update(cn, updates)
        
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role '{cn}' not found",
            )
        
        logger.info("role_updated", cn=cn, by=current_user.uid)
        
        members = await role_repo.get_members(cn)
        return _entry_to_response(entry, members)
        
    except LdapOperationError as e:
        logger.error("update_role_failed", cn=cn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update role: {e}",
        )


@router.delete("/{cn}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    cn: str,
    current_user: CurrentUser,
    role_repo: RoleRepoDep,
):
    """
    Delete a role.
    """
    if not await role_repo.exists(cn):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{cn}' not found",
        )
    
    try:
        await role_repo.delete(cn)
        
        logger.info("role_deleted", cn=cn, by=current_user.uid)
        
    except LdapOperationError as e:
        logger.error("delete_role_failed", cn=cn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete role: {e}",
        )


@router.post("/{cn}/members", status_code=status.HTTP_204_NO_CONTENT)
async def add_role_member(
    cn: str,
    member: RoleMemberOperation,
    current_user: CurrentUser,
    user_repo: UserRepoDep,
    role_repo: RoleRepoDep,
):
    """
    Add a member to a role.
    """
    if not await role_repo.exists(cn):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{cn}' not found",
        )
    
    # Get user DN
    user = await user_repo.find_by_uid(member.uid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{member.uid}' not found",
        )
    
    try:
        await role_repo.add_member(cn, user.dn)
        
        logger.info("role_member_added", cn=cn, uid=member.uid, by=current_user.uid)
        
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
async def remove_role_member(
    cn: str,
    uid: str,
    current_user: CurrentUser,
    user_repo: UserRepoDep,
    role_repo: RoleRepoDep,
):
    """
    Remove a member from a role.
    """
    if not await role_repo.exists(cn):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{cn}' not found",
        )
    
    # Get user DN
    user = await user_repo.find_by_uid(uid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{uid}' not found",
        )
    
    try:
        await role_repo.remove_member(cn, user.dn)
        
        logger.info("role_member_removed", cn=cn, uid=uid, by=current_user.uid)
        
    except LdapOperationError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{uid}' is not a member of '{cn}'",
            )
        logger.error("remove_member_failed", cn=cn, uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove member: {e}",
        )
