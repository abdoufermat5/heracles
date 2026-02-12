"""
DHCP Plugin API Routes
======================

FastAPI endpoints for DHCP configuration management.
"""

from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, Depends, Query, Path

import structlog

from .schemas import (
    DhcpObjectType,
    # Service
    DhcpServiceCreate,
    DhcpServiceUpdate,
    DhcpServiceRead,
    DhcpServiceListResponse,
    # Subnet
    SubnetCreate,
    SubnetUpdate,
    SubnetRead,
    SubnetListResponse,
    # Pool
    PoolCreate,
    PoolUpdate,
    PoolRead,
    PoolListResponse,
    # Host
    HostCreate,
    HostUpdate,
    HostRead,
    HostListResponse,
    # Shared Network
    SharedNetworkCreate,
    SharedNetworkUpdate,
    SharedNetworkRead,
    SharedNetworkListResponse,
    # Group
    GroupCreate,
    GroupUpdate,
    GroupRead,
    GroupListResponse,
    # Class
    DhcpClassCreate,
    DhcpClassUpdate,
    DhcpClassRead,
    DhcpClassListResponse,
    # SubClass
    TsigKeyCreate,
    TsigKeyRead,
    TsigKeyListResponse,
    # DNS Zone
    DnsZoneCreate,
    DnsZoneRead,
    DnsZoneListResponse,
    # Failover Peer
    FailoverPeerCreate,
    FailoverPeerUpdate,
    FailoverPeerRead,
    FailoverPeerListResponse,
    # Tree
    DhcpTreeResponse,
)
from .service import DhcpService, DhcpValidationError

logger = structlog.get_logger(__name__)

# Router for DHCP operations
router = APIRouter(prefix="/dhcp", tags=["dhcp"])


# =============================================================================
# Dependencies
# =============================================================================

def get_dhcp_service() -> DhcpService:
    """Get the DHCP service from the plugin registry."""
    from heracles_api.plugins.registry import plugin_registry
    
    service = plugin_registry.get_service("dhcp")
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DHCP plugin is not loaded",
        )
    return service


# Import CurrentUser and AclGuardDep from core dependencies
from heracles_api.core.dependencies import CurrentUser, AclGuardDep  # noqa: E402


# =============================================================================
# Service Endpoints
# =============================================================================

@router.get(
    "",
    response_model=DhcpServiceListResponse,
    summary="List DHCP services",
)
async def list_services(
    current_user: CurrentUser,
    guard: AclGuardDep,
    search: Optional[str] = Query(None, description="Search in name and comments"),
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    service: DhcpService = Depends(get_dhcp_service),
):
    """List all DHCP service configurations."""
    guard.require(service.get_dhcp_dn(), "dhcp:read")
    try:
        return await service.list_services(
            search=search,
            base_dn=base_dn,
            page=page,
            page_size=page_size,
        )
    except Exception as e:
        logger.error("list_dhcp_services_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list DHCP services: {str(e)}",
        )


@router.post(
    "",
    response_model=DhcpServiceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create DHCP service",
)
async def create_service(
    data: DhcpServiceCreate,
    current_user: CurrentUser,
    guard: AclGuardDep,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: DhcpService = Depends(get_dhcp_service),
):
    """Create a new DHCP service configuration."""
    guard.require(service.get_dhcp_dn(), "dhcp:create")
    try:
        return await service.create_service(data, base_dn=base_dn)
    except DhcpValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("create_dhcp_service_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create DHCP service: {str(e)}",
        )


@router.get(
    "/{service_cn}",
    response_model=DhcpServiceRead,
    summary="Get DHCP service",
)
async def get_service(
    service_cn: str = Path(..., description="Service name"),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: DhcpService = Depends(get_dhcp_service),
):
    """Get a DHCP service by name."""
    guard.require(service.get_dhcp_dn(), "dhcp:read")
    try:
        return await service.get_service(service_cn, base_dn=base_dn)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"DHCP service not found: {service_cn}",
            )
        logger.error("get_dhcp_service_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get DHCP service: {str(e)}",
        )


@router.patch(
    "/{service_cn}",
    response_model=DhcpServiceRead,
    summary="Update DHCP service",
)
async def update_service(
    data: DhcpServiceUpdate,
    service_cn: str = Path(..., description="Service name"),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: DhcpService = Depends(get_dhcp_service),
):
    """Update a DHCP service configuration."""
    guard.require(service.get_dhcp_dn(), "dhcp:write")
    try:
        return await service.update_service(service_cn, data, base_dn=base_dn)
    except DhcpValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"DHCP service not found: {service_cn}",
            )
        logger.error("update_dhcp_service_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update DHCP service: {str(e)}",
        )


@router.delete(
    "/{service_cn}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete DHCP service",
)
async def delete_service(
    service_cn: str = Path(..., description="Service name"),
    recursive: bool = Query(False, description="Delete all children"),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: DhcpService = Depends(get_dhcp_service),
):
    """Delete a DHCP service and optionally all its children."""
    guard.require(service.get_dhcp_dn(), "dhcp:delete")
    try:
        await service.delete_service(service_cn, recursive=recursive, base_dn=base_dn)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"DHCP service not found: {service_cn}",
            )
        logger.error("delete_dhcp_service_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete DHCP service: {str(e)}",
        )


@router.get(
    "/{service_cn}/tree",
    response_model=DhcpTreeResponse,
    summary="Get DHCP configuration tree",
)
async def get_service_tree(
    service_cn: str = Path(..., description="Service name"),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Get the full DHCP configuration tree for a service."""
    guard.require(service.get_dhcp_dn(), "dhcp:read")
    try:
        return await service.get_service_tree(service_cn)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"DHCP service not found: {service_cn}",
            )
        logger.error("get_dhcp_tree_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get DHCP tree: {str(e)}",
        )


# =============================================================================
# Subnet Endpoints
# =============================================================================

@router.get(
    "/{service_cn}/subnets",
    response_model=SubnetListResponse,
    summary="List subnets",
)
async def list_subnets(
    service_cn: str = Path(..., description="Service name"),
    parent_dn: Optional[str] = Query(None, description="Parent DN (service or shared network)"),
    search: Optional[str] = Query(None, description="Search in network and comments"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: DhcpService = Depends(get_dhcp_service),
):
    """List subnets under a service or parent."""
    guard.require(service.get_dhcp_dn(), "dhcp:read")
    try:
        return await service.list_subnets(
            service_cn=service_cn,
            parent_dn=parent_dn,
            search=search,
            page=page,
            page_size=page_size,
            base_dn=base_dn,
        )
    except Exception as e:
        logger.error("list_subnets_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list subnets: {str(e)}",
        )


@router.post(
    "/{service_cn}/subnets",
    response_model=SubnetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create subnet",
)
async def create_subnet(
    data: SubnetCreate,
    service_cn: str = Path(..., description="Service name"),
    parent_dn: Optional[str] = Query(None, description="Parent DN (defaults to service)"),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: DhcpService = Depends(get_dhcp_service),
):
    """Create a new subnet under a service or shared network."""
    guard.require(service.get_dhcp_dn(), "dhcp:create")
    try:
        # Get parent DN
        if parent_dn is None:
            parent_dn = service._get_service_dn(service_cn, base_dn=base_dn)
        
        return await service.create_subnet(parent_dn, data)
    except DhcpValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("create_subnet_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create subnet: {str(e)}",
        )


@router.get(
    "/{service_cn}/subnets/{subnet_cn}",
    response_model=SubnetRead,
    summary="Get subnet",
)
async def get_subnet(
    service_cn: str = Path(..., description="Service name"),
    subnet_cn: str = Path(..., description="Subnet network address"),
    dn: Optional[str] = Query(None, description="Full DN (if known)"),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: DhcpService = Depends(get_dhcp_service),
):
    """Get a subnet by name."""
    guard.require(service.get_dhcp_dn(), "dhcp:read")
    try:
        if dn:
            return await service.get_subnet(dn)
        else:
            # Try to find by cn under service
            parent_dn = service._get_service_dn(service_cn, base_dn=base_dn)
            subnet_dn = f"cn={subnet_cn},{parent_dn}"
            return await service.get_subnet(subnet_dn)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subnet not found: {subnet_cn}",
            )
        logger.error("get_subnet_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get subnet: {str(e)}",
        )


@router.patch(
    "/{service_cn}/subnets/{subnet_cn}",
    response_model=SubnetRead,
    summary="Update subnet",
)
async def update_subnet(
    data: SubnetUpdate,
    service_cn: str = Path(...),
    subnet_cn: str = Path(...),
    dn: Optional[str] = Query(None, description="Full DN"),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    base_dn: Optional[str] = Query(None, description="Base DN context"),
    service: DhcpService = Depends(get_dhcp_service),
):
    """Update a subnet."""
    guard.require(service.get_dhcp_dn(), "dhcp:write")
    try:
        if dn is None:
            parent_dn = service._get_service_dn(service_cn, base_dn=base_dn)
            dn = f"cn={subnet_cn},{parent_dn}"
        return await service.update_subnet(dn, data)
    except DhcpValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Subnet not found: {subnet_cn}")
        logger.error("update_subnet_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update subnet: {str(e)}")


@router.delete(
    "/{service_cn}/subnets/{subnet_cn}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete subnet",
)
async def delete_subnet(
    service_cn: str = Path(...),
    subnet_cn: str = Path(...),
    dn: Optional[str] = Query(None),
    recursive: bool = Query(False),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Delete a subnet and optionally its children."""
    guard.require(service.get_dhcp_dn(), "dhcp:delete")
    try:
        if dn is None:
            parent_dn = service._get_service_dn(service_cn)
            dn = f"cn={subnet_cn},{parent_dn}"
        await service.delete_subnet(dn, recursive=recursive)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Subnet not found: {subnet_cn}")
        logger.error("delete_subnet_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete subnet: {str(e)}")


# =============================================================================
# Pool Endpoints
# =============================================================================

@router.get(
    "/{service_cn}/pools",
    response_model=PoolListResponse,
    summary="List pools",
)
async def list_pools(
    service_cn: str = Path(...),
    parent_dn: str = Query(..., description="Parent DN (subnet or shared network)"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """List pools under a parent."""
    guard.require(service.get_dhcp_dn(), "dhcp:read")
    try:
        return await service.list_pools(parent_dn, search=search, page=page, page_size=page_size)
    except Exception as e:
        logger.error("list_pools_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to list pools: {str(e)}")


@router.post(
    "/{service_cn}/pools",
    response_model=PoolRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create pool",
)
async def create_pool(
    data: PoolCreate,
    service_cn: str = Path(...),
    parent_dn: str = Query(..., description="Parent DN (subnet or shared network)"),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Create a new pool under a subnet or shared network."""
    guard.require(service.get_dhcp_dn(), "dhcp:create")
    try:
        return await service.create_pool(parent_dn, data)
    except DhcpValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("create_pool_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create pool: {str(e)}")


@router.get(
    "/{service_cn}/pools/{pool_cn}",
    response_model=PoolRead,
    summary="Get pool",
)
async def get_pool(
    service_cn: str = Path(...),
    pool_cn: str = Path(...),
    dn: str = Query(..., description="Full DN"),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Get a pool by DN."""
    guard.require(service.get_dhcp_dn(), "dhcp:read")
    try:
        return await service.get_pool(dn)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Pool not found: {pool_cn}")
        logger.error("get_pool_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get pool: {str(e)}")


@router.patch(
    "/{service_cn}/pools/{pool_cn}",
    response_model=PoolRead,
    summary="Update pool",
)
async def update_pool(
    data: PoolUpdate,
    service_cn: str = Path(...),
    pool_cn: str = Path(...),
    dn: str = Query(...),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Update a pool."""
    guard.require(service.get_dhcp_dn(), "dhcp:write")
    try:
        return await service.update_pool(dn, data)
    except DhcpValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Pool not found: {pool_cn}")
        logger.error("update_pool_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update pool: {str(e)}")


@router.delete(
    "/{service_cn}/pools/{pool_cn}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete pool",
)
async def delete_pool(
    service_cn: str = Path(...),
    pool_cn: str = Path(...),
    dn: str = Query(...),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Delete a pool."""
    guard.require(service.get_dhcp_dn(), "dhcp:delete")
    try:
        await service.delete_pool(dn)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Pool not found: {pool_cn}")
        logger.error("delete_pool_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete pool: {str(e)}")


# =============================================================================
# Host Endpoints
# =============================================================================

@router.get(
    "/{service_cn}/hosts",
    response_model=HostListResponse,
    summary="List hosts",
)
async def list_hosts(
    service_cn: str = Path(...),
    parent_dn: Optional[str] = Query(None, description="Parent DN (defaults to service)"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """List DHCP hosts."""
    guard.require(service.get_dhcp_dn(), "dhcp:read")
    try:
        if parent_dn is None:
            parent_dn = service._get_service_dn(service_cn)
        return await service.list_hosts(parent_dn, search=search, page=page, page_size=page_size)
    except Exception as e:
        logger.error("list_hosts_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to list hosts: {str(e)}")


@router.post(
    "/{service_cn}/hosts",
    response_model=HostRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create host",
)
async def create_host(
    data: HostCreate,
    service_cn: str = Path(...),
    parent_dn: Optional[str] = Query(None),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Create a new DHCP host reservation."""
    guard.require(service.get_dhcp_dn(), "dhcp:create")
    try:
        if parent_dn is None:
            parent_dn = service._get_service_dn(service_cn)
        return await service.create_host(parent_dn, data)
    except DhcpValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("create_host_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create host: {str(e)}")


@router.get(
    "/{service_cn}/hosts/{host_cn}",
    response_model=HostRead,
    summary="Get host",
)
async def get_host(
    service_cn: str = Path(...),
    host_cn: str = Path(...),
    dn: str = Query(...),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Get a DHCP host by DN."""
    guard.require(service.get_dhcp_dn(), "dhcp:read")
    try:
        return await service.get_host(dn)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Host not found: {host_cn}")
        logger.error("get_host_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get host: {str(e)}")


@router.patch(
    "/{service_cn}/hosts/{host_cn}",
    response_model=HostRead,
    summary="Update host",
)
async def update_host(
    data: HostUpdate,
    service_cn: str = Path(...),
    host_cn: str = Path(...),
    dn: str = Query(...),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Update a DHCP host."""
    guard.require(service.get_dhcp_dn(), "dhcp:write")
    try:
        return await service.update_host(dn, data)
    except DhcpValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Host not found: {host_cn}")
        logger.error("update_host_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update host: {str(e)}")


@router.delete(
    "/{service_cn}/hosts/{host_cn}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete host",
)
async def delete_host(
    service_cn: str = Path(...),
    host_cn: str = Path(...),
    dn: str = Query(...),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Delete a DHCP host."""
    guard.require(service.get_dhcp_dn(), "dhcp:delete")
    try:
        await service.delete_host(dn)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Host not found: {host_cn}")
        logger.error("delete_host_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete host: {str(e)}")


@router.get(
    "/{service_cn}/hosts/by-mac/{mac_address}",
    response_model=HostRead,
    summary="Find host by MAC",
)
async def get_host_by_mac(
    service_cn: str = Path(...),
    mac_address: str = Path(..., description="MAC address"),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Find a DHCP host by MAC address."""
    guard.require(service.get_dhcp_dn(), "dhcp:read")
    try:
        host = await service.get_host_by_mac(mac_address)
        if host is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Host with MAC {mac_address} not found")
        return host
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_host_by_mac_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to find host: {str(e)}")


# =============================================================================
# Shared Network Endpoints
# =============================================================================

@router.get(
    "/{service_cn}/shared-networks",
    response_model=SharedNetworkListResponse,
    summary="List shared networks",
)
async def list_shared_networks(
    service_cn: str = Path(...),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """List shared networks under a service."""
    guard.require(service.get_dhcp_dn(), "dhcp:read")
    try:
        return await service.list_shared_networks(service_cn, search=search, page=page, page_size=page_size)
    except Exception as e:
        logger.error("list_shared_networks_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to list shared networks: {str(e)}")


@router.post(
    "/{service_cn}/shared-networks",
    response_model=SharedNetworkRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create shared network",
)
async def create_shared_network(
    data: SharedNetworkCreate,
    service_cn: str = Path(...),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Create a new shared network."""
    guard.require(service.get_dhcp_dn(), "dhcp:create")
    try:
        return await service.create_shared_network(service_cn, data)
    except DhcpValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("create_shared_network_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create shared network: {str(e)}")


@router.get(
    "/{service_cn}/shared-networks/{network_cn}",
    response_model=SharedNetworkRead,
    summary="Get shared network",
)
async def get_shared_network(
    service_cn: str = Path(...),
    network_cn: str = Path(...),
    dn: Optional[str] = Query(None),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Get a shared network."""
    guard.require(service.get_dhcp_dn(), "dhcp:read")
    try:
        if dn is None:
            parent_dn = service._get_service_dn(service_cn)
            dn = f"cn={network_cn},{parent_dn}"
        return await service.get_shared_network(dn)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Shared network not found: {network_cn}")
        logger.error("get_shared_network_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get shared network: {str(e)}")


@router.patch(
    "/{service_cn}/shared-networks/{network_cn}",
    response_model=SharedNetworkRead,
    summary="Update shared network",
)
async def update_shared_network(
    data: SharedNetworkUpdate,
    service_cn: str = Path(...),
    network_cn: str = Path(...),
    dn: Optional[str] = Query(None),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Update a shared network."""
    guard.require(service.get_dhcp_dn(), "dhcp:write")
    try:
        if dn is None:
            parent_dn = service._get_service_dn(service_cn)
            dn = f"cn={network_cn},{parent_dn}"
        return await service.update_shared_network(dn, data)
    except DhcpValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Shared network not found: {network_cn}")
        logger.error("update_shared_network_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update shared network: {str(e)}")


@router.delete(
    "/{service_cn}/shared-networks/{network_cn}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete shared network",
)
async def delete_shared_network(
    service_cn: str = Path(...),
    network_cn: str = Path(...),
    dn: Optional[str] = Query(None),
    recursive: bool = Query(False),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Delete a shared network."""
    guard.require(service.get_dhcp_dn(), "dhcp:delete")
    try:
        if dn is None:
            parent_dn = service._get_service_dn(service_cn)
            dn = f"cn={network_cn},{parent_dn}"
        await service.delete_shared_network(dn, recursive=recursive)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Shared network not found: {network_cn}")
        logger.error("delete_shared_network_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete shared network: {str(e)}")


# =============================================================================
# Group Endpoints
# =============================================================================

@router.get(
    "/{service_cn}/groups",
    response_model=GroupListResponse,
    summary="List groups",
)
async def list_groups(
    service_cn: str = Path(...),
    parent_dn: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """List groups."""
    guard.require(service.get_dhcp_dn(), "dhcp:read")
    try:
        if parent_dn is None:
            parent_dn = service._get_service_dn(service_cn)
        return await service.list_groups(parent_dn, search=search, page=page, page_size=page_size)
    except Exception as e:
        logger.error("list_groups_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to list groups: {str(e)}")


@router.post(
    "/{service_cn}/groups",
    response_model=GroupRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create group",
)
async def create_group(
    data: GroupCreate,
    service_cn: str = Path(...),
    parent_dn: Optional[str] = Query(None),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Create a new group."""
    guard.require(service.get_dhcp_dn(), "dhcp:create")
    try:
        if parent_dn is None:
            parent_dn = service._get_service_dn(service_cn)
        return await service.create_group(parent_dn, data)
    except DhcpValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("create_group_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create group: {str(e)}")


@router.get(
    "/{service_cn}/groups/{group_cn}",
    response_model=GroupRead,
    summary="Get group",
)
async def get_group(
    service_cn: str = Path(...),
    group_cn: str = Path(...),
    dn: str = Query(...),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Get a group by DN."""
    guard.require(service.get_dhcp_dn(), "dhcp:read")
    try:
        return await service.get_group(dn)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Group not found: {group_cn}")
        logger.error("get_group_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get group: {str(e)}")


@router.patch(
    "/{service_cn}/groups/{group_cn}",
    response_model=GroupRead,
    summary="Update group",
)
async def update_group(
    data: GroupUpdate,
    service_cn: str = Path(...),
    group_cn: str = Path(...),
    dn: str = Query(...),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Update a group."""
    guard.require(service.get_dhcp_dn(), "dhcp:write")
    try:
        return await service.update_group(dn, data)
    except DhcpValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Group not found: {group_cn}")
        logger.error("update_group_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update group: {str(e)}")


@router.delete(
    "/{service_cn}/groups/{group_cn}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete group",
)
async def delete_group(
    service_cn: str = Path(...),
    group_cn: str = Path(...),
    dn: str = Query(...),
    recursive: bool = Query(False),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Delete a group."""
    guard.require(service.get_dhcp_dn(), "dhcp:delete")
    try:
        await service.delete_group(dn, recursive=recursive)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Group not found: {group_cn}")
        logger.error("delete_group_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete group: {str(e)}")


# =============================================================================
# Class Endpoints
# =============================================================================

@router.get(
    "/{service_cn}/classes",
    response_model=DhcpClassListResponse,
    summary="List classes",
)
async def list_classes(
    service_cn: str = Path(...),
    parent_dn: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """List DHCP classes."""
    guard.require(service.get_dhcp_dn(), "dhcp:read")
    try:
        if parent_dn is None:
            parent_dn = service._get_service_dn(service_cn)
        return await service.list_classes(parent_dn, search=search, page=page, page_size=page_size)
    except Exception as e:
        logger.error("list_classes_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to list classes: {str(e)}")


@router.post(
    "/{service_cn}/classes",
    response_model=DhcpClassRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create class",
)
async def create_class(
    data: DhcpClassCreate,
    service_cn: str = Path(...),
    parent_dn: Optional[str] = Query(None),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Create a new DHCP class."""
    guard.require(service.get_dhcp_dn(), "dhcp:create")
    try:
        if parent_dn is None:
            parent_dn = service._get_service_dn(service_cn)
        return await service.create_class(parent_dn, data)
    except DhcpValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("create_class_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create class: {str(e)}")


@router.get(
    "/{service_cn}/classes/{class_cn}",
    response_model=DhcpClassRead,
    summary="Get class",
)
async def get_class(
    service_cn: str = Path(...),
    class_cn: str = Path(...),
    dn: str = Query(...),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Get a DHCP class by DN."""
    guard.require(service.get_dhcp_dn(), "dhcp:read")
    try:
        return await service.get_class(dn)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Class not found: {class_cn}")
        logger.error("get_class_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get class: {str(e)}")


@router.patch(
    "/{service_cn}/classes/{class_cn}",
    response_model=DhcpClassRead,
    summary="Update class",
)
async def update_class(
    data: DhcpClassUpdate,
    service_cn: str = Path(...),
    class_cn: str = Path(...),
    dn: str = Query(...),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Update a DHCP class."""
    guard.require(service.get_dhcp_dn(), "dhcp:write")
    try:
        return await service.update_class(dn, data)
    except DhcpValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Class not found: {class_cn}")
        logger.error("update_class_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update class: {str(e)}")


@router.delete(
    "/{service_cn}/classes/{class_cn}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete class",
)
async def delete_class(
    service_cn: str = Path(...),
    class_cn: str = Path(...),
    dn: str = Query(...),
    recursive: bool = Query(False),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Delete a DHCP class."""
    guard.require(service.get_dhcp_dn(), "dhcp:delete")
    try:
        await service.delete_class(dn, recursive=recursive)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Class not found: {class_cn}")
        logger.error("delete_class_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete class: {str(e)}")


# =============================================================================
# TSIG Key Endpoints
# =============================================================================

@router.get(
    "/{service_cn}/tsig-keys",
    response_model=TsigKeyListResponse,
    summary="List TSIG keys",
)
async def list_tsig_keys(
    service_cn: str = Path(...),
    parent_dn: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """List TSIG keys."""
    guard.require(service.get_dhcp_dn(), "dhcp:read")
    try:
        if parent_dn is None:
            parent_dn = service._get_service_dn(service_cn)
        return await service.list_tsig_keys(parent_dn, search=search, page=page, page_size=page_size)
    except Exception as e:
        logger.error("list_tsig_keys_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to list TSIG keys: {str(e)}")


@router.post(
    "/{service_cn}/tsig-keys",
    response_model=TsigKeyRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create TSIG key",
)
async def create_tsig_key(
    data: TsigKeyCreate,
    service_cn: str = Path(...),
    parent_dn: Optional[str] = Query(None),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Create a new TSIG key."""
    guard.require(service.get_dhcp_dn(), "dhcp:create")
    try:
        if parent_dn is None:
            parent_dn = service._get_service_dn(service_cn)
        return await service.create_tsig_key(parent_dn, data)
    except DhcpValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("create_tsig_key_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create TSIG key: {str(e)}")


@router.delete(
    "/{service_cn}/tsig-keys/{key_cn}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete TSIG key",
)
async def delete_tsig_key(
    service_cn: str = Path(...),
    key_cn: str = Path(...),
    dn: str = Query(...),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Delete a TSIG key."""
    guard.require(service.get_dhcp_dn(), "dhcp:delete")
    try:
        await service.delete_tsig_key(dn)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"TSIG key not found: {key_cn}")
        logger.error("delete_tsig_key_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete TSIG key: {str(e)}")


# =============================================================================
# DNS Zone Endpoints
# =============================================================================

@router.get(
    "/{service_cn}/dns-zones",
    response_model=DnsZoneListResponse,
    summary="List DNS zones",
)
async def list_dns_zones(
    service_cn: str = Path(...),
    parent_dn: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """List DNS zones for dynamic updates."""
    guard.require(service.get_dhcp_dn(), "dhcp:read")
    try:
        if parent_dn is None:
            parent_dn = service._get_service_dn(service_cn)
        return await service.list_dns_zones(parent_dn, search=search, page=page, page_size=page_size)
    except Exception as e:
        logger.error("list_dns_zones_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to list DNS zones: {str(e)}")


@router.post(
    "/{service_cn}/dns-zones",
    response_model=DnsZoneRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create DNS zone",
)
async def create_dns_zone(
    data: DnsZoneCreate,
    service_cn: str = Path(...),
    parent_dn: Optional[str] = Query(None),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Create a new DNS zone for dynamic updates."""
    guard.require(service.get_dhcp_dn(), "dhcp:create")
    try:
        if parent_dn is None:
            parent_dn = service._get_service_dn(service_cn)
        return await service.create_dns_zone(parent_dn, data)
    except DhcpValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("create_dns_zone_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create DNS zone: {str(e)}")


@router.delete(
    "/{service_cn}/dns-zones/{zone_cn}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete DNS zone",
)
async def delete_dns_zone(
    service_cn: str = Path(...),
    zone_cn: str = Path(...),
    dn: str = Query(...),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Delete a DNS zone."""
    guard.require(service.get_dhcp_dn(), "dhcp:delete")
    try:
        await service.delete_dns_zone(dn)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"DNS zone not found: {zone_cn}")
        logger.error("delete_dns_zone_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete DNS zone: {str(e)}")


# =============================================================================
# Failover Peer Endpoints
# =============================================================================

@router.get(
    "/{service_cn}/failover-peers",
    response_model=FailoverPeerListResponse,
    summary="List failover peers",
)
async def list_failover_peers(
    service_cn: str = Path(...),
    parent_dn: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """List failover peer configurations."""
    guard.require(service.get_dhcp_dn(), "dhcp:read")
    try:
        if parent_dn is None:
            parent_dn = service._get_service_dn(service_cn)
        return await service.list_failover_peers(parent_dn, search=search, page=page, page_size=page_size)
    except Exception as e:
        logger.error("list_failover_peers_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to list failover peers: {str(e)}")


@router.post(
    "/{service_cn}/failover-peers",
    response_model=FailoverPeerRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create failover peer",
)
async def create_failover_peer(
    data: FailoverPeerCreate,
    service_cn: str = Path(...),
    parent_dn: Optional[str] = Query(None),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Create a new failover peer configuration."""
    guard.require(service.get_dhcp_dn(), "dhcp:create")
    try:
        if parent_dn is None:
            parent_dn = service._get_service_dn(service_cn)
        return await service.create_failover_peer(parent_dn, data)
    except DhcpValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("create_failover_peer_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create failover peer: {str(e)}")


@router.get(
    "/{service_cn}/failover-peers/{peer_cn}",
    response_model=FailoverPeerRead,
    summary="Get failover peer",
)
async def get_failover_peer(
    service_cn: str = Path(...),
    peer_cn: str = Path(...),
    dn: str = Query(...),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Get a failover peer configuration."""
    guard.require(service.get_dhcp_dn(), "dhcp:read")
    try:
        return await service.get_failover_peer(dn)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Failover peer not found: {peer_cn}")
        logger.error("get_failover_peer_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get failover peer: {str(e)}")


@router.patch(
    "/{service_cn}/failover-peers/{peer_cn}",
    response_model=FailoverPeerRead,
    summary="Update failover peer",
)
async def update_failover_peer(
    data: FailoverPeerUpdate,
    service_cn: str = Path(...),
    peer_cn: str = Path(...),
    dn: str = Query(...),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Update a failover peer configuration."""
    guard.require(service.get_dhcp_dn(), "dhcp:write")
    try:
        return await service.update_failover_peer(dn, data)
    except DhcpValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Failover peer not found: {peer_cn}")
        logger.error("update_failover_peer_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update failover peer: {str(e)}")


@router.delete(
    "/{service_cn}/failover-peers/{peer_cn}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete failover peer",
)
async def delete_failover_peer(
    service_cn: str = Path(...),
    peer_cn: str = Path(...),
    dn: str = Query(...),
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Delete a failover peer configuration."""
    guard.require(service.get_dhcp_dn(), "dhcp:delete")
    try:
        await service.delete_failover_peer(dn)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Failover peer not found: {peer_cn}")
        logger.error("delete_failover_peer_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete failover peer: {str(e)}")


# =============================================================================
# Object Types Endpoint
# =============================================================================

@router.get(
    "/types",
    response_model=List[dict],
    summary="Get available DHCP object types",
)
async def get_dhcp_object_types(
    current_user: CurrentUser = None,
    guard: AclGuardDep = None,
    service: DhcpService = Depends(get_dhcp_service),
):
    """Get the list of available DHCP object types."""
    guard.require(service.get_dhcp_dn(), "dhcp:read")
    return [
        {
            "value": t.value,
            "label": t.value.replace("-", " ").title(),
            "objectClass": DhcpObjectType.get_object_class(t),
            "allowedChildren": [c.value for c in DhcpObjectType.get_allowed_children(t)],
        }
        for t in DhcpObjectType
    ]
