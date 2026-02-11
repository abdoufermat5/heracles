"""
Audit Log Repository
====================

Database operations for the audit_logs table.
"""

from datetime import datetime
from typing import Any, Optional

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from heracles_api.models.audit import AuditLog

logger = structlog.get_logger(__name__)


class AuditRepository:
    """Repository for audit log CRUD operations."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        *,
        actor_dn: str,
        action: str,
        entity_type: str,
        actor_name: Optional[str] = None,
        entity_id: Optional[str] = None,
        entity_name: Optional[str] = None,
        changes: Optional[dict[str, Any]] = None,
        department_dn: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> AuditLog:
        """Insert a new audit log entry."""
        entry = AuditLog(
            actor_dn=actor_dn,
            actor_name=actor_name,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            changes=changes,
            department_dn=department_dn,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def list_entries(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        actor_dn: Optional[str] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        department_dn: Optional[str] = None,
        status: Optional[str] = None,
        from_ts: Optional[datetime] = None,
        to_ts: Optional[datetime] = None,
        search: Optional[str] = None,
    ) -> tuple[list[AuditLog], int]:
        """List audit entries with filtering and pagination."""
        query = select(AuditLog)
        count_query = select(func.count()).select_from(AuditLog)

        # Apply filters
        if actor_dn:
            query = query.where(AuditLog.actor_dn.ilike(f"%{actor_dn}%"))
            count_query = count_query.where(AuditLog.actor_dn.ilike(f"%{actor_dn}%"))
        if action:
            query = query.where(AuditLog.action == action)
            count_query = count_query.where(AuditLog.action == action)
        if entity_type:
            query = query.where(AuditLog.entity_type == entity_type)
            count_query = count_query.where(AuditLog.entity_type == entity_type)
        if entity_id:
            query = query.where(AuditLog.entity_id.ilike(f"%{entity_id}%"))
            count_query = count_query.where(AuditLog.entity_id.ilike(f"%{entity_id}%"))
        if department_dn:
            query = query.where(AuditLog.department_dn.ilike(f"%{department_dn}%"))
            count_query = count_query.where(
                AuditLog.department_dn.ilike(f"%{department_dn}%")
            )
        if status:
            query = query.where(AuditLog.status == status)
            count_query = count_query.where(AuditLog.status == status)
        if from_ts:
            query = query.where(AuditLog.timestamp >= from_ts)
            count_query = count_query.where(AuditLog.timestamp >= from_ts)
        if to_ts:
            query = query.where(AuditLog.timestamp <= to_ts)
            count_query = count_query.where(AuditLog.timestamp <= to_ts)
        if search:
            pattern = f"%{search}%"
            search_filter = (
                AuditLog.entity_name.ilike(pattern)
                | AuditLog.actor_name.ilike(pattern)
                | AuditLog.entity_id.ilike(pattern)
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        # Count
        total_result = await self._session.execute(count_query)
        total = total_result.scalar() or 0

        # Order and paginate
        query = query.order_by(AuditLog.timestamp.desc())
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self._session.execute(query)
        entries = list(result.scalars().all())

        return entries, total

    async def get_entity_history(
        self,
        entity_type: str,
        entity_id: str,
        limit: int = 50,
    ) -> list[AuditLog]:
        """Get audit history for a specific entity."""
        query = (
            select(AuditLog)
            .where(AuditLog.entity_type == entity_type)
            .where(AuditLog.entity_id == entity_id)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())
