"""
Audit Service
==============

Business logic for audit logging and retrieval.
Provides a simple API for logging actions from any service layer.
"""

from typing import Any, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from heracles_api.repositories.audit_repository import AuditRepository
from heracles_api.schemas.audit import (
    AuditLogEntry,
    AuditLogFilters,
    AuditLogListResponse,
    mask_sensitive_data,
)

logger = structlog.get_logger(__name__)


class AuditService:
    """Service for recording and querying audit events."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def log_action(
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
    ) -> None:
        """
        Log an audit event.

        This is fire-and-forget — errors are logged but never raised
        to avoid disrupting the main operation.
        """
        try:
            # Mask sensitive fields before storing
            masked_changes = mask_sensitive_data(changes)

            async with self._session_factory() as session:
                repo = AuditRepository(session)
                await repo.create(
                    actor_dn=actor_dn,
                    actor_name=actor_name,
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity_name=entity_name,
                    changes=masked_changes,
                    department_dn=department_dn,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    status=status,
                    error_message=error_message,
                )
                await session.commit()

            logger.debug(
                "audit_logged",
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                actor=actor_dn,
            )
        except Exception as e:
            # Never let audit failures break the main flow
            logger.error(
                "audit_log_failed",
                action=action,
                entity_type=entity_type,
                error=str(e),
            )

    async def get_logs(
        self, filters: AuditLogFilters
    ) -> AuditLogListResponse:
        """Query audit logs with filtering and pagination."""
        async with self._session_factory() as session:
            repo = AuditRepository(session)
            entries, total = await repo.list_entries(
                page=filters.page,
                page_size=filters.page_size,
                actor_dn=filters.actor_dn,
                action=filters.action,
                entity_type=filters.entity_type,
                entity_id=filters.entity_id,
                department_dn=filters.department_dn,
                status=filters.status,
                from_ts=filters.from_ts,
                to_ts=filters.to_ts,
                search=filters.search,
            )

            items = [
                AuditLogEntry(
                    id=e.id,
                    timestamp=e.timestamp,
                    actor_dn=e.actor_dn,
                    actor_name=e.actor_name,
                    action=e.action,
                    entity_type=e.entity_type,
                    entity_id=e.entity_id,
                    entity_name=e.entity_name,
                    changes=e.changes,
                    department_dn=e.department_dn,
                    ip_address=e.ip_address,
                    status=e.status,
                    error_message=e.error_message,
                )
                for e in entries
            ]

            return AuditLogListResponse(
                entries=items,
                total=total,
                page=filters.page,
                page_size=filters.page_size,
                has_more=(filters.page * filters.page_size) < total,
            )

    async def get_entity_history(
        self,
        entity_type: str,
        entity_id: str,
        limit: int = 50,
    ) -> list[AuditLogEntry]:
        """Get audit trail for a specific entity."""
        async with self._session_factory() as session:
            repo = AuditRepository(session)
            entries = await repo.get_entity_history(
                entity_type=entity_type,
                entity_id=entity_id,
                limit=limit,
            )
            return [
                AuditLogEntry(
                    id=e.id,
                    timestamp=e.timestamp,
                    actor_dn=e.actor_dn,
                    actor_name=e.actor_name,
                    action=e.action,
                    entity_type=e.entity_type,
                    entity_id=e.entity_id,
                    entity_name=e.entity_name,
                    changes=e.changes,
                    department_dn=e.department_dn,
                    ip_address=e.ip_address,
                    status=e.status,
                    error_message=e.error_message,
                )
                for e in entries
            ]


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_audit_service: Optional[AuditService] = None


def init_audit_service(
    session_factory: async_sessionmaker[AsyncSession],
) -> AuditService:
    """Initialize the global audit service."""
    global _audit_service
    _audit_service = AuditService(session_factory)
    return _audit_service


def get_audit_service() -> AuditService:
    """Get the global audit service instance."""
    if _audit_service is None:
        raise RuntimeError("Audit service not initialized")
    return _audit_service
