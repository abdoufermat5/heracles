"""
DNS Plugin API Routes
=====================

FastAPI endpoints for DNS zone and record management.
"""

from typing import List

from fastapi import APIRouter, HTTPException, status, Depends, Query

import structlog

from .schemas import (
    DnsZoneCreate,
    DnsZoneRead,
    DnsZoneUpdate,
    DnsZoneListResponse,
    DnsRecordCreate,
    DnsRecordRead,
    DnsRecordUpdate,
    DnsRecordListItem,
)
from .service import DnsService, DnsValidationError

logger = structlog.get_logger(__name__)

# Router for DNS operations
router = APIRouter(prefix="/dns", tags=["dns"])


# =============================================================================
# Dependencies
# =============================================================================

def get_dns_service() -> DnsService:
    """Get the DNS service from the plugin registry."""
    from heracles_api.plugins.registry import plugin_registry

    service = plugin_registry.get_service("dns")
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DNS plugin is not loaded",
        )
    return service


# Import CurrentUser and AclGuardDep from core dependencies
from heracles_api.core.dependencies import CurrentUser, AclGuardDep  # noqa: E402


# =============================================================================
# Zone Endpoints
# =============================================================================

@router.get(
    "/zones",
    response_model=DnsZoneListResponse,
    summary="List all DNS zones",
)
async def list_zones(
    current_user: CurrentUser,
    guard: AclGuardDep,
    base_dn: str = Query(None, description="Base DN context"),
    service: DnsService = Depends(get_dns_service),
):
    """
    List all DNS zones.

    Returns all zones with their names, types, and record counts.
    
    Requires: dns:read
    """
    guard.require(service.get_dns_dn(), "dns:read")
    try:
        return await service.list_zones(base_dn=base_dn)
    except Exception as e:
        logger.error("list_zones_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list zones: {str(e)}",
        )


@router.post(
    "/zones",
    response_model=DnsZoneRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a DNS zone",
)
async def create_zone(
    data: DnsZoneCreate,
    current_user: CurrentUser,
    guard: AclGuardDep,
    base_dn: str = Query(None, description="Base DN context"),
    service: DnsService = Depends(get_dns_service),
):
    """
    Create a new DNS zone.

    Creates a zone with the specified SOA parameters. The zone apex (@)
    entry is created automatically with the SOA record.
    
    Requires: dns:create
    """
    guard.require(service.get_dns_dn(), "dns:create")
    try:
        return await service.create_zone(data, base_dn=base_dn)
    except DnsValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "create_zone_failed",
            zone_name=data.zone_name,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create zone: {str(e)}",
        )


@router.get(
    "/zones/{zone_name}",
    response_model=DnsZoneRead,
    summary="Get a DNS zone",
)
async def get_zone(
    zone_name: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    base_dn: str = Query(None, description="Base DN context"),
    service: DnsService = Depends(get_dns_service),
):
    """Get a specific DNS zone by name.
    
    Requires: dns:read
    """
    guard.require(service.get_dns_dn(), "dns:read")
    try:
        zone = await service.get_zone(zone_name, base_dn=base_dn)
        if zone is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone '{zone_name}' not found",
            )
        return zone
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_zone_failed", zone_name=zone_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get zone: {str(e)}",
        )


@router.put(
    "/zones/{zone_name}",
    response_model=DnsZoneRead,
    summary="Update a DNS zone",
)
async def update_zone(
    zone_name: str,
    data: DnsZoneUpdate,
    current_user: CurrentUser,
    guard: AclGuardDep,
    base_dn: str = Query(None, description="Base DN context"),
    service: DnsService = Depends(get_dns_service),
):
    """
    Update a DNS zone.

    Updates the zone's SOA parameters. The serial number is automatically
    incremented on each update.
    
    Requires: dns:write
    """
    guard.require(service.get_dns_dn(), "dns:write")
    try:
        return await service.update_zone(zone_name, data, base_dn=base_dn)
    except DnsValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone '{zone_name}' not found",
            )
        logger.error("update_zone_failed", zone_name=zone_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update zone: {str(e)}",
        )


@router.delete(
    "/zones/{zone_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a DNS zone",
)
async def delete_zone(
    zone_name: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    base_dn: str = Query(None, description="Base DN context"),
    service: DnsService = Depends(get_dns_service),
):
    """
    Delete a DNS zone and all its records.

    This is a destructive operation that removes all records within the zone.
    
    Requires: dns:delete
    """
    guard.require(service.get_dns_dn(), "dns:delete")
    try:
        await service.delete_zone(zone_name, base_dn=base_dn)
    except DnsValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone '{zone_name}' not found",
            )
        logger.error("delete_zone_failed", zone_name=zone_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete zone: {str(e)}",
        )


# =============================================================================
# Record Endpoints
# =============================================================================

@router.get(
    "/zones/{zone_name}/records",
    response_model=List[DnsRecordListItem],
    summary="List records in a zone",
)
async def list_records(
    zone_name: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    base_dn: str = Query(None, description="Base DN context"),
    service: DnsService = Depends(get_dns_service),
):
    """
    List all records in a DNS zone.

    Returns records from all relativeDomainName entries within the zone.
    
    Requires: dns:read
    """
    guard.require(service.get_dns_dn(), "dns:read")
    try:
        return await service.list_records(zone_name, base_dn=base_dn)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone '{zone_name}' not found",
            )
        logger.error("list_records_failed", zone_name=zone_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list records: {str(e)}",
        )


@router.post(
    "/zones/{zone_name}/records",
    response_model=DnsRecordRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a DNS record",
)
async def create_record(
    zone_name: str,
    data: DnsRecordCreate,
    current_user: CurrentUser,
    guard: AclGuardDep,
    base_dn: str = Query(None, description="Base DN context"),
    service: DnsService = Depends(get_dns_service),
):
    """
    Create a new DNS record in a zone.

    Use '@' as the name for zone apex records.
    MX and SRV records require a priority value.
    
    Requires: dns:create
    """
    guard.require(service.get_dns_dn(), "dns:create")
    try:
        return await service.create_record(zone_name, data, base_dn=base_dn)
    except DnsValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone '{zone_name}' not found",
            )
        logger.error(
            "create_record_failed",
            zone_name=zone_name,
            name=data.name,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create record: {str(e)}",
        )


@router.put(
    "/zones/{zone_name}/records/{name}/{record_type}",
    response_model=DnsRecordRead,
    summary="Update a DNS record",
)
async def update_record(
    zone_name: str,
    name: str,
    record_type: str,
    data: DnsRecordUpdate,
    current_user: CurrentUser,
    guard: AclGuardDep,
    old_value: str = Query(..., description="Current record value to update"),
    base_dn: str = Query(None, description="Base DN context"),
    service: DnsService = Depends(get_dns_service),
):
    """
    Update an existing DNS record.

    The old_value parameter is required to identify which specific record
    to update when multiple records of the same type exist.
    
    Requires: dns:write
    """
    guard.require(service.get_dns_dn(), "dns:write")
    try:
        return await service.update_record(zone_name, name, record_type, old_value, data, base_dn=base_dn)
    except DnsValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        logger.error(
            "update_record_failed",
            zone_name=zone_name,
            name=name,
            record_type=record_type,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update record: {str(e)}",
        )


@router.delete(
    "/zones/{zone_name}/records/{name}/{record_type}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a DNS record",
)
async def delete_record(
    zone_name: str,
    name: str,
    record_type: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    value: str = Query(..., description="Record value to delete"),
    base_dn: str = Query(None, description="Base DN context"),
    service: DnsService = Depends(get_dns_service),
):
    """
    Delete a DNS record.

    The value parameter is required to identify which specific record
    to delete when multiple records of the same type exist.
    
    Requires: dns:delete
    """
    guard.require(service.get_dns_dn(), "dns:delete")
    try:
        await service.delete_record(zone_name, name, record_type, value, base_dn=base_dn)
    except DnsValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        logger.error(
            "delete_record_failed",
            zone_name=zone_name,
            name=name,
            record_type=record_type,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete record: {str(e)}",
        )
