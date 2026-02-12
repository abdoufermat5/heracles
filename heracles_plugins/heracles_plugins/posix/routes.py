"""
POSIX Plugin API Routes
=======================

FastAPI endpoints for POSIX account management.

In standard LDAP:
- posixAccount/shadowAccount are auxiliary classes added to users (inetOrgPerson)
- posixGroup is a standalone structural class for UNIX groups (separate from groupOfNames)
"""

from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, Depends, Query

import structlog

from heracles_api.services.ldap_service import LdapService

from .schemas import (
    PosixAccountCreate,
    PosixAccountRead,
    PosixAccountUpdate,
    PosixGroupRead,
    PosixGroupUpdate,
    PosixGroupFullCreate,
    PosixStatusResponse,
    AvailableShellsResponse,
    IdAllocationResponse,
    PosixGroupListResponse,
    # MixedGroup schemas
    MixedGroupCreate,
    MixedGroupRead,
    MixedGroupUpdate,
    MixedGroupListResponse,
)
from .service import PosixService, PosixGroupService, MixedGroupService, PosixValidationError

logger = structlog.get_logger(__name__)

# Router for POSIX operations
router = APIRouter(tags=["posix"])


# =============================================================================
# Helper Functions
# =============================================================================

async def find_user_dn(uid: str, ldap_service: LdapService) -> str:
    """
    Find user DN by UID.
    
    Searches the entire LDAP subtree to find users in any OU
    (including department OUs like ou=people,ou=engineering,...).
    
    Args:
        uid: User ID to find
        ldap_service: LDAP service instance
        
    Returns:
        User DN
        
    Raises:
        HTTPException: If user not found
    """
    from heracles_api.config import settings
    
    # Search from base DN with subtree scope to find users in any OU
    results = await ldap_service.search(
        search_base=settings.LDAP_BASE_DN,
        search_filter=f"(&(objectClass=inetOrgPerson)(uid={uid}))",
        attributes=["dn"],
        size_limit=1,
    )
    
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found: {uid}",
        )
    
    return results[0].dn


# =============================================================================
# Dependencies
# =============================================================================

async def get_ldap_service() -> LdapService:
    """Get the LDAP service."""
    from heracles_api.core.dependencies import get_ldap
    return await get_ldap()


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


def get_mixed_group_service() -> MixedGroupService:
    """Get the MixedGroup service from the plugin registry."""
    from heracles_api.plugins.registry import plugin_registry
    
    service = plugin_registry.get_service("mixed-group")
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="POSIX plugin (MixedGroup) is not loaded",
        )
    return service


# Import CurrentUser and AclGuardDep from core dependencies
from heracles_api.core.dependencies import CurrentUser, AclGuardDep  # noqa: E402


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
    guard: AclGuardDep,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: PosixService = Depends(get_posix_service),
    ldap_service: LdapService = Depends(get_ldap_service),
):
    """
    Get POSIX account status and data for a user.
    
    Returns whether POSIX is active and the account data if it is.
    """
    guard.require(service.get_base_dn(), "posix:read")
    try:
        dn = await find_user_dn(uid, ldap_service)
        is_active = await service.is_active(dn)
        data = await service.read(dn) if is_active else None
        
        return PosixStatusResponse(active=is_active, data=data)
        
    except HTTPException:
        raise
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
    guard: AclGuardDep,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: PosixService = Depends(get_posix_service),
    group_service: PosixGroupService = Depends(get_posix_group_service),
    ldap_service: LdapService = Depends(get_ldap_service),
):
    """
    Activate POSIX account for a user.
    
    This adds the posixAccount and shadowAccount objectClasses
    and sets the POSIX attributes.
    
    If uidNumber is not provided, it will be auto-allocated.
    If homeDirectory is not provided, it will be generated from the uid.
    
    When primaryGroupMode is "create_personal", a personal group with the same
    name as the user will be automatically created.
    """
    guard.require(service.get_base_dn(), "posix:create")
    try:
        dn = await find_user_dn(uid, ldap_service)
        
        # Extract base DN from user's DN for group creation context
        # User DN is like: uid=xxx,ou=people,ou=dept,dc=heracles,dc=local
        # We want the context after ou=people: ou=dept,dc=heracles,dc=local
        effective_base_dn = base_dn
        if effective_base_dn is None:
            # Try to extract from user DN
            dn_lower = dn.lower()
            ou_people_idx = dn_lower.find(",ou=people,")
            if ou_people_idx != -1:
                # Get everything after ,ou=people,
                effective_base_dn = dn[ou_people_idx + len(",ou=people,"):]
        
        result = await service.activate(dn, data, uid=uid, group_service=group_service, base_dn=effective_base_dn)
        logger.info("posix_activated_via_api", uid=uid, by=current_user.uid, base_dn=effective_base_dn)
        return result
        
    except HTTPException:
        raise
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
    guard: AclGuardDep,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: PosixService = Depends(get_posix_service),
    ldap_service: LdapService = Depends(get_ldap_service),
):
    """
    Update POSIX account attributes for a user.
    
    Only provided fields will be updated.
    """
    guard.require(service.get_base_dn(), "posix:write")
    try:
        dn = await find_user_dn(uid, ldap_service)
        result = await service.update(dn, data)
        logger.info("posix_updated_via_api", uid=uid, by=current_user.uid)
        return result
        
    except HTTPException:
        raise
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
    guard: AclGuardDep,
    delete_personal_group: bool = Query(
        default=True,
        description="Delete the personal group if it exists and is empty",
    ),
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: PosixService = Depends(get_posix_service),
    group_service: PosixGroupService = Depends(get_posix_group_service),
    ldap_service: LdapService = Depends(get_ldap_service),
):
    """
    Deactivate POSIX account for a user.
    
    This removes the posixAccount and shadowAccount objectClasses
    and all POSIX attributes.
    
    If delete_personal_group is True and the user has a personal group
    (same name as uid) that is empty, it will be automatically deleted.
    """
    guard.require(service.get_base_dn(), "posix:delete")
    try:
        dn = await find_user_dn(uid, ldap_service)
        await service.deactivate(
            dn,
            group_service=group_service,
            delete_personal_group=delete_personal_group,
        )
        logger.info("posix_deactivated_via_api", uid=uid, by=current_user.uid)
        
    except HTTPException:
        raise
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
    guard: AclGuardDep,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: PosixGroupService = Depends(get_posix_group_service),
):
    """
    List all POSIX groups.
    
    POSXI groups (posixGroup) are standalone entries separate from 
    organizational groups (groupOfNames).
    """
    guard.require(service.get_base_dn(), "posix:read")
    try:
        groups = await service.list_all(base_dn=base_dn)
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
    guard: AclGuardDep,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: PosixGroupService = Depends(get_posix_group_service),
):
    """
    Create a new standalone POSIX group.
    
    This creates a new entry with posixGroup as the structural objectClass.
    """
    guard.require(service.get_base_dn(), "posix:create")
    try:
        result = await service.create(data, base_dn=base_dn)
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
    guard: AclGuardDep,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: PosixGroupService = Depends(get_posix_group_service),
):
    """
    Get details of a specific POSIX group.
    """
    guard.require(service.get_base_dn(), "posix:read")
    try:
        result = await service.get(cn, base_dn=base_dn)
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
    guard: AclGuardDep,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: PosixGroupService = Depends(get_posix_group_service),
):
    """
    Update a POSIX group's attributes.
    """
    guard.require(service.get_base_dn(), "posix:write")
    try:
        result = await service.update_group(cn, data, base_dn=base_dn)
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
    guard: AclGuardDep,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: PosixGroupService = Depends(get_posix_group_service),
):
    """
    Delete a POSIX group.
    
    Warning: This will remove the group entry entirely.
    """
    guard.require(service.get_base_dn(), "posix:delete")
    try:
        await service.delete(cn, base_dn=base_dn)
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
    guard: AclGuardDep,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: PosixGroupService = Depends(get_posix_group_service),
):
    """
    Add a member (by uid) to a POSIX group.
    """
    guard.require(service.get_base_dn(), "posix:write")
    try:
        result = await service.add_member_by_cn(cn, uid, base_dn=base_dn)
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
    guard: AclGuardDep,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: PosixGroupService = Depends(get_posix_group_service),
):
    """
    Remove a member (by uid) from a POSIX group.
    """
    guard.require(service.get_base_dn(), "posix:write")
    try:
        result = await service.remove_member_by_cn(cn, uid, base_dn=base_dn)
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
    guard: AclGuardDep,
    service: PosixService = Depends(get_posix_service),
):
    """
    Get the list of available login shells.
    """
    guard.require(service.get_base_dn(), "posix:read")
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
    guard: AclGuardDep,
    service: PosixService = Depends(get_posix_service),
    group_service: PosixGroupService = Depends(get_posix_group_service),
):
    """
    Get the next available UID and GID numbers.
    
    Useful for displaying in the UI before creating an account.
    """
    guard.require(service.get_base_dn(), "posix:read")
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


# =============================================================================
# User Group Membership Management (from user perspective)
# =============================================================================

@router.get(
    "/users/{uid}/posix/groups",
    response_model=List[str],
    summary="Get user's POSIX group memberships",
)
async def get_user_group_memberships(
    uid: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    service: PosixService = Depends(get_posix_service),
):
    """
    Get all POSIX groups that a user belongs to (via memberUid).
    
    This returns the list of group CNs where the user is a member.
    """
    guard.require(service.get_base_dn(), "posix:read")
    groups = await service._get_user_group_memberships(uid)
    return groups


@router.post(
    "/users/{uid}/posix/groups/{cn}",
    response_model=PosixGroupRead,
    summary="Add user to a POSIX group",
)
async def add_user_to_group(
    uid: str,
    cn: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    group_service: PosixGroupService = Depends(get_posix_group_service),
):
    """
    Add a user to a POSIX group.
    
    This is the user-centric way to manage group memberships.
    """
    guard.require(group_service.get_base_dn(), "posix:write")
    try:
        result = await group_service.add_member_by_cn(cn, uid, base_dn=None)
        logger.info("user_added_to_group", uid=uid, cn=cn, by=current_user.uid)
        return result
        
    except PosixValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("add_user_to_group_failed", uid=uid, cn=cn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add user to group: {str(e)}",
        )


@router.delete(
    "/users/{uid}/posix/groups/{cn}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove user from a POSIX group",
)
async def remove_user_from_group(
    uid: str,
    cn: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    group_service: PosixGroupService = Depends(get_posix_group_service),
):
    """
    Remove a user from a POSIX group.
    
    This is the user-centric way to manage group memberships.
    """
    guard.require(group_service.get_base_dn(), "posix:write")
    try:
        await group_service.remove_member_by_cn(cn, uid, base_dn=None)
        logger.info("user_removed_from_group", uid=uid, cn=cn, by=current_user.uid)
        
    except PosixValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("remove_user_from_group_failed", uid=uid, cn=cn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove user from group: {str(e)}",
        )


# =============================================================================
# MixedGroup Endpoints (groupOfNames + posixGroup)
# =============================================================================

@router.get(
    "/posix/mixed-groups",
    response_model=MixedGroupListResponse,
    summary="List all MixedGroups",
)
async def list_mixed_groups(
    current_user: CurrentUser,
    guard: AclGuardDep,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: MixedGroupService = Depends(get_mixed_group_service),
):
    """
    List all MixedGroups.
    
    MixedGroups combine groupOfNames (LDAP) and posixGroup (UNIX)
    for hybrid access control.
    """
    guard.require(service.get_base_dn(), "posix:read")
    try:
        groups = await service.list_all(base_dn=base_dn)
        return MixedGroupListResponse(groups=groups, total=len(groups))
        
    except PosixValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/posix/mixed-groups/{cn}",
    response_model=MixedGroupRead,
    summary="Get a MixedGroup by name",
)
async def get_mixed_group(
    cn: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: MixedGroupService = Depends(get_mixed_group_service),
):
    """Get details of a specific MixedGroup."""
    guard.require(service.get_base_dn(), "posix:read")
    group = await service.get(cn, base_dn=base_dn)
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MixedGroup '{cn}' not found",
        )
    return group


@router.post(
    "/posix/mixed-groups",
    response_model=MixedGroupRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new MixedGroup",
)
async def create_mixed_group(
    data: MixedGroupCreate,
    current_user: CurrentUser,
    guard: AclGuardDep,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: MixedGroupService = Depends(get_mixed_group_service),
):
    """
    Create a new MixedGroup.
    
    A MixedGroup has both groupOfNames and posixGroup object classes,
    allowing it to be used for LDAP-based access control (member DNs)
    and UNIX group permissions (memberUid).
    """
    guard.require(service.get_base_dn(), "posix:create")
    try:
        result = await service.create(data, base_dn=base_dn)
        logger.info("mixed_group_created", cn=data.cn, by=current_user.uid)
        return result
        
    except PosixValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("create_mixed_group_failed", cn=data.cn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create MixedGroup: {str(e)}",
        )


@router.patch(
    "/posix/mixed-groups/{cn}",
    response_model=MixedGroupRead,
    summary="Update a MixedGroup",
)
async def update_mixed_group(
    cn: str,
    data: MixedGroupUpdate,
    current_user: CurrentUser,
    guard: AclGuardDep,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: MixedGroupService = Depends(get_mixed_group_service),
):
    """Update a MixedGroup's attributes."""
    guard.require(service.get_base_dn(), "posix:write")
    try:
        result = await service.update_group(cn, data, base_dn=base_dn)
        logger.info("mixed_group_updated", cn=cn, by=current_user.uid)
        return result
        
    except PosixValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("update_mixed_group_failed", cn=cn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update MixedGroup: {str(e)}",
        )


@router.delete(
    "/posix/mixed-groups/{cn}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a MixedGroup",
)
async def delete_mixed_group(
    cn: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: MixedGroupService = Depends(get_mixed_group_service),
):
    """Delete a MixedGroup."""
    guard.require(service.get_base_dn(), "posix:delete")
    try:
        await service.delete(cn, base_dn=base_dn)
        logger.info("mixed_group_deleted", cn=cn, by=current_user.uid)
        
    except PosixValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("delete_mixed_group_failed", cn=cn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete MixedGroup: {str(e)}",
        )


# =============================================================================
# MixedGroup Member Management
# =============================================================================

@router.post(
    "/posix/mixed-groups/{cn}/members",
    response_model=MixedGroupRead,
    summary="Add a member (DN) to a MixedGroup",
)
async def add_mixed_group_member(
    cn: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    member_dn: str = Query(..., description="The DN of the member to add"),
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: MixedGroupService = Depends(get_mixed_group_service),
):
    """
    Add a member to a MixedGroup by DN.
    
    This adds the member to the `member` attribute (groupOfNames).
    """
    guard.require(service.get_base_dn(), "posix:write")
    try:
        result = await service.add_member(cn, member_dn, base_dn=base_dn)
        logger.info("mixed_group_member_added", cn=cn, member_dn=member_dn, by=current_user.uid)
        return result
        
    except PosixValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/posix/mixed-groups/{cn}/members",
    response_model=MixedGroupRead,
    summary="Remove a member (DN) from a MixedGroup",
)
async def remove_mixed_group_member(
    cn: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    member_dn: str = Query(..., description="The DN of the member to remove"),
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: MixedGroupService = Depends(get_mixed_group_service),
):
    """
    Remove a member from a MixedGroup by DN.
    
    This removes the member from the `member` attribute (groupOfNames).
    """
    guard.require(service.get_base_dn(), "posix:write")
    try:
        result = await service.remove_member(cn, member_dn, base_dn=base_dn)
        logger.info("mixed_group_member_removed", cn=cn, member_dn=member_dn, by=current_user.uid)
        return result
        
    except PosixValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/posix/mixed-groups/{cn}/member-uids/{uid}",
    response_model=MixedGroupRead,
    summary="Add a memberUid to a MixedGroup",
)
async def add_mixed_group_member_uid(
    cn: str,
    uid: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: MixedGroupService = Depends(get_mixed_group_service),
):
    """
    Add a memberUid to a MixedGroup.
    
    This adds the UID to the `memberUid` attribute (posixGroup).
    """
    guard.require(service.get_base_dn(), "posix:write")
    try:
        result = await service.add_member_uid(cn, uid, base_dn=base_dn)
        logger.info("mixed_group_member_uid_added", cn=cn, uid=uid, by=current_user.uid)
        return result
        
    except PosixValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/posix/mixed-groups/{cn}/member-uids/{uid}",
    response_model=MixedGroupRead,
    summary="Remove a memberUid from a MixedGroup",
)
async def remove_mixed_group_member_uid(
    cn: str,
    uid: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: MixedGroupService = Depends(get_mixed_group_service),
):
    """
    Remove a memberUid from a MixedGroup.
    
    This removes the UID from the `memberUid` attribute (posixGroup).
    """
    guard.require(service.get_base_dn(), "posix:write")
    try:
        result = await service.remove_member_uid(cn, uid, base_dn=base_dn)
        logger.info("mixed_group_member_uid_removed", cn=cn, uid=uid, by=current_user.uid)
        return result
        
    except PosixValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/posix/mixed-groups/next-gid",
    response_model=IdAllocationResponse,
    summary="Get next available GID for MixedGroups",
)
async def get_mixed_group_next_gid(
    current_user: CurrentUser,
    guard: AclGuardDep,
    service: MixedGroupService = Depends(get_mixed_group_service),
):
    """Get the next available GID number for creating a MixedGroup."""
    guard.require(service.get_base_dn(), "posix:read")
    try:
        next_gid = await service.get_next_gid()
        return IdAllocationResponse(value=next_gid)
        
    except PosixValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
