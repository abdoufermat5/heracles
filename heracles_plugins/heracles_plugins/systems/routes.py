"""
Systems Plugin API Routes
=========================

FastAPI endpoints for system management.
"""

from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, Depends, Query

import structlog

from .schemas import (
    SystemType,
    SystemCreate,
    SystemRead,
    SystemUpdate,
    SystemListResponse,
    HostValidationRequest,
    HostValidationResponse,
)
from .service import SystemService, SystemValidationError

logger = structlog.get_logger(__name__)

# Router for systems operations
router = APIRouter(prefix="/systems", tags=["systems"])


# =============================================================================
# Dependencies
# =============================================================================

def get_systems_service() -> SystemService:
    """Get the systems service from the plugin registry."""
    from heracles_api.plugins.registry import plugin_registry
    
    service = plugin_registry.get_service("systems")
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Systems plugin is not loaded",
        )
    return service


# Import CurrentUser from core dependencies
from heracles_api.core.dependencies import CurrentUser


# =============================================================================
# System CRUD Endpoints
# =============================================================================

@router.get(
    "",
    response_model=SystemListResponse,
    summary="List all systems",
)
async def list_systems(
    current_user: CurrentUser,
    system_type: Optional[SystemType] = Query(
        None, 
        alias="type",
        description="Filter by system type"
    ),
    search: Optional[str] = Query(
        None, 
        description="Search in cn, description, ipHostNumber"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    service: SystemService = Depends(get_systems_service),
):
    """
    List all systems with optional filtering.
    
    Results can be filtered by system type and searched by hostname,
    description, or IP address.
    """
    try:
        return await service.list_systems(
            system_type=system_type,
            search=search,
            page=page,
            page_size=page_size,
        )
    except Exception as e:
        logger.error("list_systems_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list systems: {str(e)}",
        )


@router.get(
    "/types",
    response_model=List[dict],
    summary="Get available system types",
)
async def get_system_types(current_user: CurrentUser):
    """Get the list of available system types."""
    return [
        {
            "value": t.value,
            "label": t.value.title(),
            "objectClass": SystemType.get_object_class(t),
        }
        for t in SystemType
    ]


@router.get(
    "/hostnames",
    response_model=List[str],
    summary="Get all system hostnames",
)
async def get_all_hostnames(
    current_user: CurrentUser,
    service: SystemService = Depends(get_systems_service),
):
    """
    Get all registered system hostnames.
    
    Useful for autocomplete in forms that reference hosts.
    """
    try:
        return await service.get_all_hostnames()
    except Exception as e:
        logger.error("get_hostnames_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get hostnames: {str(e)}",
        )


@router.post(
    "/validate-hosts",
    response_model=HostValidationResponse,
    summary="Validate hostnames against registered systems",
)
async def validate_hosts(
    data: HostValidationRequest,
    current_user: CurrentUser,
    service: SystemService = Depends(get_systems_service),
):
    """
    Validate that hostnames exist as registered systems.
    
    Used by other features (POSIX groups, sudo rules, etc.) to validate
    host references.
    """
    try:
        return await service.validate_hosts(data.hostnames)
    except Exception as e:
        logger.error("validate_hosts_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate hosts: {str(e)}",
        )


@router.get(
    "/{system_type}/{cn}",
    response_model=SystemRead,
    summary="Get a system",
)
async def get_system(
    system_type: SystemType,
    cn: str,
    current_user: CurrentUser,
    service: SystemService = Depends(get_systems_service),
):
    """Get a specific system by type and CN."""
    try:
        system = await service.get_system(cn, system_type)
        if system is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"System '{cn}' of type '{system_type.value}' not found",
            )
        return system
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_system_failed", cn=cn, type=system_type.value, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system: {str(e)}",
        )


@router.post(
    "",
    response_model=SystemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a system",
)
async def create_system(
    data: SystemCreate,
    current_user: CurrentUser,
    service: SystemService = Depends(get_systems_service),
):
    """
    Create a new system.
    
    The system type must be specified and determines which OU the system
    will be created in and which objectClasses are used.
    """
    try:
        return await service.create_system(data)
    except SystemValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "create_system_failed", 
            cn=data.cn, 
            type=data.system_type.value,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create system: {str(e)}",
        )


@router.put(
    "/{system_type}/{cn}",
    response_model=SystemRead,
    summary="Update a system",
)
async def update_system(
    system_type: SystemType,
    cn: str,
    data: SystemUpdate,
    current_user: CurrentUser,
    service: SystemService = Depends(get_systems_service),
):
    """Update an existing system."""
    try:
        return await service.update_system(cn, system_type, data)
    except SystemValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"System '{cn}' of type '{system_type.value}' not found",
            )
        logger.error(
            "update_system_failed", 
            cn=cn, 
            type=system_type.value,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update system: {str(e)}",
        )


@router.delete(
    "/{system_type}/{cn}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a system",
)
async def delete_system(
    system_type: SystemType,
    cn: str,
    current_user: CurrentUser,
    service: SystemService = Depends(get_systems_service),
):
    """Delete a system."""
    try:
        await service.delete_system(cn, system_type)
    except SystemValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"System '{cn}' of type '{system_type.value}' not found",
            )
        logger.error(
            "delete_system_failed", 
            cn=cn, 
            type=system_type.value,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete system: {str(e)}",
        )


# =============================================================================
# Type-Specific Convenience Endpoints
# =============================================================================

@router.get(
    "/servers",
    response_model=SystemListResponse,
    summary="List servers",
)
async def list_servers(
    current_user: CurrentUser,
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: SystemService = Depends(get_systems_service),
):
    """List all servers."""
    return await service.list_systems(
        system_type=SystemType.SERVER,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/workstations",
    response_model=SystemListResponse,
    summary="List workstations",
)
async def list_workstations(
    current_user: CurrentUser,
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: SystemService = Depends(get_systems_service),
):
    """List all workstations."""
    return await service.list_systems(
        system_type=SystemType.WORKSTATION,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/terminals",
    response_model=SystemListResponse,
    summary="List terminals",
)
async def list_terminals(
    current_user: CurrentUser,
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: SystemService = Depends(get_systems_service),
):
    """List all terminals."""
    return await service.list_systems(
        system_type=SystemType.TERMINAL,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/printers",
    response_model=SystemListResponse,
    summary="List printers",
)
async def list_printers(
    current_user: CurrentUser,
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: SystemService = Depends(get_systems_service),
):
    """List all printers."""
    return await service.list_systems(
        system_type=SystemType.PRINTER,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/components",
    response_model=SystemListResponse,
    summary="List components",
)
async def list_components(
    current_user: CurrentUser,
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: SystemService = Depends(get_systems_service),
):
    """List all components (network devices, etc.)."""
    return await service.list_systems(
        system_type=SystemType.COMPONENT,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/phones",
    response_model=SystemListResponse,
    summary="List phones",
)
async def list_phones(
    current_user: CurrentUser,
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: SystemService = Depends(get_systems_service),
):
    """List all phones (IP phones)."""
    return await service.list_systems(
        system_type=SystemType.PHONE,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/mobile",
    response_model=SystemListResponse,
    summary="List mobile phones",
)
async def list_mobile_phones(
    current_user: CurrentUser,
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: SystemService = Depends(get_systems_service),
):
    """List all mobile phones."""
    return await service.list_systems(
        system_type=SystemType.MOBILE,
        search=search,
        page=page,
        page_size=page_size,
    )
