"""
POSIX Plugin API Routes
=======================

FastAPI endpoints for POSIX account management.

Following FusionDirectory's model:
- posixAccount/shadowAccount are auxiliary classes added to users (inetOrgPerson)
- posixGroup is a standalone structural class for UNIX groups (separate from groupOfNames)
"""

from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, Depends, Query

import structlog

from .schemas import (
    PosixAccountCreate,
    PosixAccountRead,
    PosixAccountUpdate,
    PosixGroupCreate,
    PosixGroupRead,
    PosixGroupUpdate,
    PosixGroupFullCreate,
    PosixStatusResponse,
    PosixGroupStatusResponse,
    AvailableShellsResponse,
    IdAllocationResponse,
    PosixGroupListResponse,
)
from .service import PosixService, PosixGroupService, PosixValidationError

logger = structlog.get_logger(__name__)

# Router for POSIX operations
router = APIRouter(tags=["posix"])


# =============================================================================
# Dependencies
# =============================================================================

def get_posix_service() -> PosixService:
    """Get the POSIX service from the plugin registry."""
    from heracles_api.plugins.registry import plugin_registry
    
    service = plugin_registry.get_service("posix")
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="POSIX plugin is not loaded",
        )
    return service


def get_posix_group_service() -> PosixGroupService:
    """Get the POSIX group service from the plugin registry."""
    from heracles_api.plugins.registry import plugin_registry
    
    service = plugin_registry.get_service("posix-group")
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="POSIX plugin is not loaded",
        )
    return service


# Import CurrentUser from core dependencies
from heracles_api.core.dependencies import CurrentUser


# =============================================================================
# User POSIX Endpoints (posixAccount / shadowAccount)
# =============================================================================

@router.get(
    "/users/{uid}/posix",
    response_model=PosixStatusResponse,
    summary="Get POSIX status for a user",
)
async def get_user_posix(
    uid: str,
    current_user: CurrentUser,
    service: PosixService = Depends(get_posix_service),
):
    """
    Get POSIX account status and data for a user.
    
    Returns whether POSIX is active and the account data if it is.
    """
    from heracles_api.config import settings
    
    dn = f"uid={uid},ou=people,{settings.LDAP_BASE_DN}"
    
    try:
        is_active = await service.is_active(dn)
        data = await service.read(dn) if is_active else None
        
        return PosixStatusResponse(active=is_active, data=data)
        
    except Exception as e:
        logger.error("get_user_posix_failed", uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get POSIX status: {str(e)}",
        )


@router.post(
    "/users/{uid}/posix",
    response_model=PosixAccountRead,
    status_code=status.HTTP_201_CREATED,
    summary="Activate POSIX for a user",
)
async def activate_user_posix(
    uid: str,
    data: PosixAccountCreate,
    current_user: CurrentUser,
    service: PosixService = Depends(get_posix_service),
):
    """
    Activate POSIX account for a user.
    
    This adds the posixAccount and shadowAccount objectClasses
    and sets the POSIX attributes.
    
    If uidNumber is not provided, it will be auto-allocated.
    If homeDirectory is not provided, it will be generated from the uid.
    """
    from heracles_api.config import settings
    
    dn = f"uid={uid},ou=people,{settings.LDAP_BASE_DN}"
    
    try:
        result = await service.activate(dn, data, uid=uid)
        logger.info("posix_activated_via_api", uid=uid, by=current_user.uid)
        return result
        
    except PosixValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("activate_user_posix_failed", uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate POSIX: {str(e)}",
        )


@router.put(
    "/users/{uid}/posix",
    response_model=PosixAccountRead,
    summary="Update POSIX attributes for a user",
)
async def update_user_posix(
    uid: str,
    data: PosixAccountUpdate,
    current_user: CurrentUser,
    service: PosixService = Depends(get_posix_service),
):
    """
    Update POSIX account attributes for a user.
    
    Only provided fields will be updated.
    """
    from heracles_api.config import settings
    
    dn = f"uid={uid},ou=people,{settings.LDAP_BASE_DN}"
    
    try:
        result = await service.update(dn, data)
        logger.info("posix_updated_via_api", uid=uid, by=current_user.uid)
        return result
        
    except PosixValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("update_user_posix_failed", uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update POSIX: {str(e)}",
        )


@router.delete(
    "/users/{uid}/posix",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate POSIX for a user",
)
async def deactivate_user_posix(
    uid: str,
    current_user: CurrentUser,
    service: PosixService = Depends(get_posix_service),
):
    """
    Deactivate POSIX account for a user.
    
    This removes the posixAccount and shadowAccount objectClasses
    and all POSIX attributes.
    """
    from heracles_api.config import settings
    
    dn = f"uid={uid},ou=people,{settings.LDAP_BASE_DN}"
    
    try:
        await service.deactivate(dn)
        logger.info("posix_deactivated_via_api", uid=uid, by=current_user.uid)
        
    except PosixValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("deactivate_user_posix_failed", uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate POSIX: {str(e)}",
        )


# =============================================================================
# POSIX Group Management Endpoints (standalone posixGroup entries)
# =============================================================================

@router.get(
    "/posix/groups",
    response_model=PosixGroupListResponse,
    summary="List all POSIX groups",
)
async def list_posix_groups(
    current_user: CurrentUser,
    service: PosixGroupService = Depends(get_posix_group_service),
):
    """
    List all POSIX groups.
    
    POSIX groups (posixGroup) are standalone entries separate from 
    organizational groups (groupOfNames).
    """
    try:
        groups = await service.list_all()
        return PosixGroupListResponse(groups=groups, total=len(groups))
        
    except Exception as e:
        logger.error("list_posix_groups_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list POSIX groups: {str(e)}",
        )


@router.post(
    "/posix/groups",
    response_model=PosixGroupRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new POSIX group",
)
async def create_posix_group(
    data: PosixGroupFullCreate,
    current_user: CurrentUser,
    service: PosixGroupService = Depends(get_posix_group_service),
):
    """
    Create a new standalone POSIX group.
    
    This creates a new entry with posixGroup as the structural objectClass.
    """
    try:
        result = await service.create(data)
        logger.info("posix_group_created_via_api", cn=data.cn, by=current_user.uid)
        return result
        
    except PosixValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("create_posix_group_failed", cn=data.cn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create POSIX group: {str(e)}",
        )


@router.get(
    "/posix/groups/{cn}",
    response_model=PosixGroupRead,
    summary="Get a POSIX group by name",
)
async def get_posix_group(
    cn: str,
    current_user: CurrentUser,
    service: PosixGroupService = Depends(get_posix_group_service),
):
    """
    Get details of a specific POSIX group.
    """
    try:
        result = await service.get(cn)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"POSIX group '{cn}' not found",
            )
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_posix_group_failed", cn=cn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get POSIX group: {str(e)}",
        )


@router.put(
    "/posix/groups/{cn}",
    response_model=PosixGroupRead,
    summary="Update a POSIX group",
)
async def update_posix_group(
    cn: str,
    data: PosixGroupUpdate,
    current_user: CurrentUser,
    service: PosixGroupService = Depends(get_posix_group_service),
):
    """
    Update a POSIX group's attributes.
    """
    try:
        result = await service.update_group(cn, data)
        logger.info("posix_group_updated_via_api", cn=cn, by=current_user.uid)
        return result
        
    except PosixValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("update_posix_group_failed", cn=cn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update POSIX group: {str(e)}",
        )


@router.delete(
    "/posix/groups/{cn}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a POSIX group",
)
async def delete_posix_group(
    cn: str,
    current_user: CurrentUser,
    service: PosixGroupService = Depends(get_posix_group_service),
):
    """
    Delete a POSIX group.
    
    Warning: This will remove the group entry entirely.
    """
    try:
        await service.delete(cn)
        logger.info("posix_group_deleted_via_api", cn=cn, by=current_user.uid)
        
    except PosixValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("delete_posix_group_failed", cn=cn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete POSIX group: {str(e)}",
        )


# =============================================================================
# POSIX Group Member Management
# =============================================================================

@router.post(
    "/posix/groups/{cn}/members/{uid}",
    response_model=PosixGroupRead,
    summary="Add member to POSIX group",
)
async def add_posix_group_member(
    cn: str,
    uid: str,
    current_user: CurrentUser,
    service: PosixGroupService = Depends(get_posix_group_service),
):
    """
    Add a member (by uid) to a POSIX group.
    """
    try:
        result = await service.add_member_by_cn(cn, uid)
        logger.info("posix_group_member_added", cn=cn, uid=uid, by=current_user.uid)
        return result
        
    except PosixValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("add_posix_group_member_failed", cn=cn, uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add member: {str(e)}",
        )


@router.delete(
    "/posix/groups/{cn}/members/{uid}",
    response_model=PosixGroupRead,
    summary="Remove member from POSIX group",
)
async def remove_posix_group_member(
    cn: str,
    uid: str,
    current_user: CurrentUser,
    service: PosixGroupService = Depends(get_posix_group_service),
):
    """
    Remove a member (by uid) from a POSIX group.
    """
    try:
        result = await service.remove_member_by_cn(cn, uid)
        logger.info("posix_group_member_removed", cn=cn, uid=uid, by=current_user.uid)
        return result
        
    except PosixValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("remove_posix_group_member_failed", cn=cn, uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove member: {str(e)}",
        )


# =============================================================================
# Utility Endpoints
# =============================================================================

@router.get(
    "/posix/shells",
    response_model=AvailableShellsResponse,
    summary="Get available login shells",
)
async def get_available_shells(
    current_user: CurrentUser,
    service: PosixService = Depends(get_posix_service),
):
    """
    Get the list of available login shells.
    """
    return AvailableShellsResponse(
        shells=service.get_shells(),
        default=service.get_default_shell(),
    )


@router.get(
    "/posix/next-ids",
    response_model=IdAllocationResponse,
    summary="Get next available UID and GID",
)
async def get_next_ids(
    current_user: CurrentUser,
    service: PosixService = Depends(get_posix_service),
    group_service: PosixGroupService = Depends(get_posix_group_service),
):
    """
    Get the next available UID and GID numbers.
    
    Useful for displaying in the UI before creating an account.
    """
    try:
        next_uid = await service.get_next_uid()
        next_gid = await group_service.get_next_gid()
        ranges = service.get_id_ranges()
        
        return IdAllocationResponse(
            next_uid=next_uid,
            next_gid=next_gid,
            uid_range=ranges["uid"],
            gid_range=ranges["gid"],
        )
        
    except PosixValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
