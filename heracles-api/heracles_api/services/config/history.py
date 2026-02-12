"""
Configuration History
=====================

Audit trail for configuration changes.
"""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from heracles_api.repositories.config_history_repository import ConfigHistoryRepository
from heracles_api.schemas.config import ConfigHistoryEntry, ConfigHistoryResponse

logger = structlog.get_logger(__name__)


class HistoryManager:
    """Manages configuration change history and audit trail."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def get_history(
        self,
        page: int = 1,
        page_size: int = 50,
        category: str | None = None,
        plugin_name: str | None = None,
    ) -> ConfigHistoryResponse:
        """Get configuration change history."""
        async with self._session_factory() as session:
            repo = ConfigHistoryRepository(session)
            rows, total = await repo.list_history(
                page=page,
                page_size=page_size,
                category=category,
                plugin_name=plugin_name,
            )

            items = [
                ConfigHistoryEntry(
                    id=str(row.id),
                    plugin_name=row.plugin_name,
                    category=row.category,
                    setting_key=row.setting_key,
                    old_value=row.old_value,
                    new_value=row.new_value,
                    changed_by=row.changed_by,
                    changed_at=row.changed_at,
                    reason=row.reason,
                )
                for row in rows
            ]

            return ConfigHistoryResponse(
                items=items,
                total=total,
                page=page,
                page_size=page_size,
            )
