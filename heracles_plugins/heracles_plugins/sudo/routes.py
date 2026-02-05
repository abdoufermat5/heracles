"""
Sudo Plugin API Routes
======================

FastAPI endpoints for sudo role management.
"""

from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, Depends, Query

import structlog

from .schemas import (
    SudoRoleCreate,
    SudoRoleRead,
    SudoRoleUpdate,
    SudoRoleListResponse,
)
from .service import SudoService, SudoValidationError

logger = structlog.get_logger(__name__)

# Router for sudo operations
router = APIRouter(prefix="/sudo", tags=["sudo"])


# =============================================================================
# Dependencies
# =============================================================================

def get_sudo_service() -> SudoService:
    """Get the sudo service from the plugin registry."""
    from heracles_api.plugins.registry import plugin_registry
    
    service = plugin_registry.get_service("sudo")
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sudo plugin is not loaded",
        )
    return service


# Import CurrentUser and AclGuardDep from core dependencies
from heracles_api.core.dependencies import CurrentUser, AclGuardDep


# =============================================================================
# Sudo Role CRUD Endpoints
# =============================================================================

@router.get(
    "/roles",
    response_model=SudoRoleListResponse,
    summary="List all sudo roles",
)
async def list_sudo_roles(
    current_user: CurrentUser,
    guard: AclGuardDep,
    search: Optional[str] = Query(None, description="Search in cn, description, sudoUser"),
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    service: SudoService = Depends(get_sudo_service),
):
    """
    List all sudo roles with optional filtering.
    
    Results are sorted by sudoOrder (priority), then by cn.
    """
    guard.require(service.get_sudoers_dn(), "sudo:read")
    try:
        return await service.list_roles(search=search, base_dn=base_dn, page=page, page_size=page_size)
    except Exception as e:
        logger.error("list_sudo_roles_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sudo roles: {str(e)}",
        )


@router.get(
    "/roles/{cn}",
    response_model=SudoRoleRead,
    summary="Get a sudo role",
)
async def get_sudo_role(
    cn: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: SudoService = Depends(get_sudo_service),
):
    """Get a specific sudo role by CN."""
    guard.require(service.get_sudoers_dn(), "sudo:read")
    try:
        role = await service.get_role(cn, base_dn=base_dn)
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sudo role '{cn}' not found",
            )
        return role
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_sudo_role_failed", cn=cn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sudo role: {str(e)}",
        )


@router.post(
    "/roles",
    response_model=SudoRoleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a sudo role",
)
async def create_sudo_role(
    data: SudoRoleCreate,
    current_user: CurrentUser,
    guard: AclGuardDep,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: SudoService = Depends(get_sudo_service),
):
    """
    Create a new sudo role.
    
    A sudo role defines who (sudoUser) can run what commands (sudoCommand)
    on which hosts (sudoHost) as which user/group (sudoRunAsUser/sudoRunAsGroup).
    """
    guard.require(service.get_sudoers_dn(), "sudo:create")
    try:
        return await service.create_role(data, base_dn=base_dn)
    except SudoValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("create_sudo_role_failed", cn=data.cn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create sudo role: {str(e)}",
        )


@router.put(
    "/roles/{cn}",
    response_model=SudoRoleRead,
    summary="Update a sudo role",
)
async def update_sudo_role(
    cn: str,
    data: SudoRoleUpdate,
    current_user: CurrentUser,
    guard: AclGuardDep,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: SudoService = Depends(get_sudo_service),
):
    """
    Update an existing sudo role.
    
    Only provided fields will be updated.
    """
    guard.require(service.get_sudoers_dn(), "sudo:write")
    try:
        return await service.update_role(cn, data, base_dn=base_dn)
    except SudoValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("update_sudo_role_failed", cn=cn, error=str(e))
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sudo role '{cn}' not found",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update sudo role: {str(e)}",
        )


@router.delete(
    "/roles/{cn}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a sudo role",
)
async def delete_sudo_role(
    cn: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: SudoService = Depends(get_sudo_service),
):
    """
    Delete a sudo role.
    
    Note: The 'defaults' role cannot be deleted.
    """
    guard.require(service.get_sudoers_dn(), "sudo:delete")
    try:
        await service.delete_role(cn, base_dn=base_dn)
    except SudoValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("delete_sudo_role_failed", cn=cn, error=str(e))
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sudo role '{cn}' not found",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete sudo role: {str(e)}",
        )


# =============================================================================
# Defaults Entry
# =============================================================================

@router.get(
    "/defaults",
    response_model=SudoRoleRead,
    summary="Get sudo defaults",
)
async def get_sudo_defaults(
    current_user: CurrentUser,
    guard: AclGuardDep,
    service: SudoService = Depends(get_sudo_service),
):
    """
    Get the sudo defaults entry.
    
    The defaults entry contains global sudo options that apply to all rules.
    """
    guard.require(service.get_sudoers_dn(), "sudo:read")
    try:
        defaults = await service.get_defaults()
        if defaults is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sudo defaults entry not found",
            )
        return defaults
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_sudo_defaults_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sudo defaults: {str(e)}",
        )


@router.post(
    "/defaults",
    response_model=SudoRoleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create sudo defaults",
)
async def create_sudo_defaults(
    current_user: CurrentUser,
    guard: AclGuardDep,
    options: List[str] = Query(default=[], description="Default sudo options"),
    service: SudoService = Depends(get_sudo_service),
):
    """
    Create the sudo defaults entry if it doesn't exist.
    
    Common options:
    - env_reset: Reset environment to default
    - mail_badpass: Send mail on bad password
    - secure_path: Secure PATH for sudo commands
    """
    guard.require(service.get_sudoers_dn(), "sudo:create")
    try:
        return await service.create_defaults(options)
    except SudoValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("create_sudo_defaults_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create sudo defaults: {str(e)}",
        )


# =============================================================================
# User-centric Queries
# =============================================================================

@router.get(
    "/users/{uid}/roles",
    response_model=List[SudoRoleRead],
    summary="Get sudo roles for a user",
)
async def get_user_sudo_roles(
    uid: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    service: SudoService = Depends(get_sudo_service),
):
    """
    Get all sudo roles that apply to a specific user.
    
    This includes:
    - Roles where the user is directly named
    - Roles where one of the user's groups is named
    - Roles that apply to ALL users
    
    Only currently valid rules (based on time constraints) are returned.
    """
    guard.require(service.get_sudoers_dn(), "sudo:read")
    try:
        # Get user's groups
        from heracles_api.services.ldap_service import get_ldap_service
        from heracles_api.config import settings
        
        ldap = get_ldap_service()
        user_dn = f"uid={uid},ou=people,{settings.LDAP_BASE_DN}"
        
        # Get user entry to find groups
        user_entry = await ldap.get_by_dn(user_dn, attributes=["uid"])
        if user_entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{uid}' not found",
            )
        
        # Find groups the user belongs to (memberUid or member)
        groups = []
        group_entries = await ldap.search(
            search_filter=f"(|(memberUid={uid})(member={user_dn}))",
            attributes=["cn"],
        )
        for entry in group_entries:
            cn = entry.get("cn")
            if cn:
                if isinstance(cn, list):
                    groups.extend(cn)
                else:
                    groups.append(cn)
        
        return await service.get_roles_for_user(uid, groups)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_user_sudo_roles_failed", uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user sudo roles: {str(e)}",
        )


@router.get(
    "/hosts/{hostname}/roles",
    response_model=List[SudoRoleRead],
    summary="Get sudo roles for a host",
)
async def get_host_sudo_roles(
    hostname: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    service: SudoService = Depends(get_sudo_service),
):
    """
    Get all sudo roles that apply to a specific host.
    
    This includes roles that explicitly name the host or use ALL.
    """
    guard.require(service.get_sudoers_dn(), "sudo:read")
    try:
        return await service.get_roles_for_host(hostname)
    except Exception as e:
        logger.error("get_host_sudo_roles_failed", hostname=hostname, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get host sudo roles: {str(e)}",
        )
