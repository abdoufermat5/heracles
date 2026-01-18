"""
POSIX Plugin API Routes
=======================

FastAPI endpoints for POSIX account management.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends, Query

import structlog

from .schemas import (
    PosixAccountCreate,
    PosixAccountRead,
    PosixAccountUpdate,
    PosixGroupCreate,
    PosixGroupRead,
    PosixGroupUpdate,
    PosixStatusResponse,
    PosixGroupStatusResponse,
    AvailableShellsResponse,
    IdAllocationResponse,
)
from .service import PosixService, PosixGroupService, PosixValidationError

logger = structlog.get_logger(__name__)

# Router for user POSIX operations
router = APIRouter(tags=["posix"])


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


# =============================================================================
# User POSIX Endpoints
# =============================================================================

@router.get(
    "/users/{uid}/posix",
    response_model=PosixStatusResponse,
    summary="Get POSIX status for a user",
)
async def get_user_posix(
    uid: str,
    service: PosixService = Depends(get_posix_service),
):
    """
    Get POSIX account status and data for a user.
    
    Returns whether POSIX is active and the account data if it is.
    """
    from heracles_api.core.dependencies import get_ldap_service
    from heracles_api.config import settings
    
    # Build DN from uid
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
        logger.info("posix_activated_via_api", uid=uid)
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
        logger.info("posix_updated_via_api", uid=uid)
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
        logger.info("posix_deactivated_via_api", uid=uid)
        
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
# Group POSIX Endpoints
# =============================================================================

@router.get(
    "/groups/{cn}/posix",
    response_model=PosixGroupStatusResponse,
    summary="Get POSIX status for a group",
)
async def get_group_posix(
    cn: str,
    service: PosixGroupService = Depends(get_posix_group_service),
):
    """
    Get POSIX status and data for a group.
    """
    from heracles_api.config import settings
    
    dn = f"cn={cn},ou=groups,{settings.LDAP_BASE_DN}"
    
    try:
        is_active = await service.is_active(dn)
        data = await service.read(dn) if is_active else None
        
        return PosixGroupStatusResponse(active=is_active, data=data)
        
    except Exception as e:
        logger.error("get_group_posix_failed", cn=cn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get POSIX status: {str(e)}",
        )


@router.post(
    "/groups/{cn}/posix",
    response_model=PosixGroupRead,
    status_code=status.HTTP_201_CREATED,
    summary="Activate POSIX for a group",
)
async def activate_group_posix(
    cn: str,
    data: PosixGroupCreate,
    service: PosixGroupService = Depends(get_posix_group_service),
):
    """
    Activate POSIX for a group.
    
    This adds the posixGroup objectClass and gidNumber attribute.
    If gidNumber is not provided, it will be auto-allocated.
    """
    from heracles_api.config import settings
    
    dn = f"cn={cn},ou=groups,{settings.LDAP_BASE_DN}"
    
    try:
        result = await service.activate(dn, data)
        logger.info("posix_group_activated_via_api", cn=cn)
        return result
        
    except PosixValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("activate_group_posix_failed", cn=cn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate POSIX: {str(e)}",
        )


@router.put(
    "/groups/{cn}/posix",
    response_model=PosixGroupRead,
    summary="Update POSIX attributes for a group",
)
async def update_group_posix(
    cn: str,
    data: PosixGroupUpdate,
    service: PosixGroupService = Depends(get_posix_group_service),
):
    """
    Update POSIX group attributes.
    """
    from heracles_api.config import settings
    
    dn = f"cn={cn},ou=groups,{settings.LDAP_BASE_DN}"
    
    try:
        result = await service.update(dn, data)
        logger.info("posix_group_updated_via_api", cn=cn)
        return result
        
    except PosixValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("update_group_posix_failed", cn=cn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update POSIX: {str(e)}",
        )


@router.delete(
    "/groups/{cn}/posix",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate POSIX for a group",
)
async def deactivate_group_posix(
    cn: str,
    service: PosixGroupService = Depends(get_posix_group_service),
):
    """
    Deactivate POSIX for a group.
    """
    from heracles_api.config import settings
    
    dn = f"cn={cn},ou=groups,{settings.LDAP_BASE_DN}"
    
    try:
        await service.deactivate(dn)
        logger.info("posix_group_deactivated_via_api", cn=cn)
        
    except PosixValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("deactivate_group_posix_failed", cn=cn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate POSIX: {str(e)}",
        )


@router.post(
    "/groups/{cn}/posix/members/{uid}",
    response_model=PosixGroupRead,
    summary="Add member to POSIX group",
)
async def add_posix_group_member(
    cn: str,
    uid: str,
    service: PosixGroupService = Depends(get_posix_group_service),
):
    """
    Add a member (by uid) to a POSIX group.
    """
    from heracles_api.config import settings
    
    dn = f"cn={cn},ou=groups,{settings.LDAP_BASE_DN}"
    
    try:
        result = await service.add_member(dn, uid)
        return result
        
    except PosixValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/groups/{cn}/posix/members/{uid}",
    response_model=PosixGroupRead,
    summary="Remove member from POSIX group",
)
async def remove_posix_group_member(
    cn: str,
    uid: str,
    service: PosixGroupService = Depends(get_posix_group_service),
):
    """
    Remove a member (by uid) from a POSIX group.
    """
    from heracles_api.config import settings
    
    dn = f"cn={cn},ou=groups,{settings.LDAP_BASE_DN}"
    
    try:
        result = await service.remove_member(dn, uid)
        return result
        
    except PosixValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
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


@router.get(
    "/posix/groups",
    summary="List all POSIX groups",
)
async def list_posix_groups(
    service: PosixGroupService = Depends(get_posix_group_service),
):
    """
    List all groups with POSIX enabled.
    
    Useful for populating primary group selection.
    """
    from heracles_api.plugins.registry import plugin_registry
    
    ldap = plugin_registry._ldap_service
    
    try:
        entries = await ldap.search(
            search_filter="(objectClass=posixGroup)",
            attributes=["cn", "gidNumber", "description"],
        )
        
        groups = []
        for entry in entries:
            groups.append({
                "cn": entry.get_first("cn", ""),
                "gidNumber": int(entry.get_first("gidNumber", 0)),
                "description": entry.get_first("description", ""),
            })
        
        # Sort by cn
        groups.sort(key=lambda g: g["cn"])
        
        return {"groups": groups, "total": len(groups)}
        
    except Exception as e:
        logger.error("list_posix_groups_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list POSIX groups: {str(e)}",
        )
