"""
Audit Log API Endpoint
=======================

Unified audit log endpoint for querying all entity operations.
"""

from datetime import datetime

from fastapi import APIRouter, Query

from heracles_api.schemas.audit import AuditLogFilters, AuditLogListResponse
from heracles_api.services.audit_service import get_audit_service

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, alias="pageSize", description="Items per page"),
    actor_dn: str | None = Query(None, alias="actorDn", description="Filter by actor DN"),
    action: str | None = Query(None, description="Filter by action (create, update, delete, login, etc.)"),
    entity_type: str | None = Query(None, alias="entityType", description="Filter by entity type (user, group, etc.)"),
    entity_id: str | None = Query(None, alias="entityId", description="Filter by entity ID/DN"),
    department_dn: str | None = Query(None, alias="departmentDn", description="Filter by department DN"),
    status: str | None = Query(None, description="Filter by status (success, failure)"),
    from_ts: datetime | None = Query(None, alias="fromTs", description="Start of date range"),
    to_ts: datetime | None = Query(None, alias="toTs", description="End of date range"),
    search: str | None = Query(None, description="Free-text search in entity name/actor"),
) -> AuditLogListResponse:
    """
    Query the unified audit log.

    Returns all tracked operations across users, groups, departments,
    systems, templates, configuration changes, and more.
    """
    audit_service = get_audit_service()
    filters = AuditLogFilters(
        page=page,
        page_size=page_size,
        actor_dn=actor_dn,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        department_dn=department_dn,
        status=status,
        from_ts=from_ts,
        to_ts=to_ts,
        search=search,
    )
    return await audit_service.get_logs(filters)


@router.get("/logs/{entity_type}/{entity_id:path}")
async def get_entity_audit_history(
    entity_type: str,
    entity_id: str,
    limit: int = Query(50, ge=1, le=200),
):
    """
    Get audit history for a specific entity.

    Useful for showing change timeline on entity detail pages.
    """
    audit_service = get_audit_service()
    entries = await audit_service.get_entity_history(
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
    )
    return {"entries": [e.model_dump(by_alias=True) for e in entries]}
