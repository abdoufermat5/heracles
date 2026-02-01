"""
Configuration History
=====================

Audit trail for configuration changes.
"""

from typing import Any, Optional

import structlog

from heracles_api.schemas.config import ConfigHistoryEntry, ConfigHistoryResponse

logger = structlog.get_logger(__name__)


class HistoryManager:
    """Manages configuration change history and audit trail."""

    def __init__(self, db_pool: Any):
        """
        Initialize the history manager.

        Args:
            db_pool: asyncpg connection pool
        """
        self._db = db_pool

    async def get_history(
        self,
        page: int = 1,
        page_size: int = 50,
        category: Optional[str] = None,
        plugin_name: Optional[str] = None,
    ) -> ConfigHistoryResponse:
        """
        Get configuration change history.

        Args:
            page: Page number (1-indexed)
            page_size: Items per page
            category: Filter by category
            plugin_name: Filter by plugin

        Returns:
            ConfigHistoryResponse with paginated results.
        """
        offset = (page - 1) * page_size

        async with self._db.acquire() as conn:
            # Build query
            where_clauses = []
            params = []
            param_idx = 1

            if category:
                where_clauses.append(f"category = ${param_idx}")
                params.append(category)
                param_idx += 1

            if plugin_name:
                where_clauses.append(f"plugin_name = ${param_idx}")
                params.append(plugin_name)
                param_idx += 1

            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            # Count total
            count_sql = f"SELECT COUNT(*) FROM config_history {where_sql}"
            total = await conn.fetchval(count_sql, *params)

            # Get items
            params.extend([page_size, offset])
            items_sql = f"""
                SELECT id, setting_id, plugin_name, category, setting_key,
                       old_value, new_value, changed_by, changed_at, reason
                FROM config_history
                {where_sql}
                ORDER BY changed_at DESC
                LIMIT ${param_idx} OFFSET ${param_idx + 1}
            """
            rows = await conn.fetch(items_sql, *params)

            items = [
                ConfigHistoryEntry(
                    id=str(row['id']),
                    plugin_name=row['plugin_name'],
                    category=row['category'],
                    setting_key=row['setting_key'],
                    old_value=row['old_value'],
                    new_value=row['new_value'],
                    changed_by=row['changed_by'],
                    changed_at=row['changed_at'],
                    reason=row['reason'],
                )
                for row in rows
            ]

            return ConfigHistoryResponse(
                items=items,
                total=total,
                page=page,
                page_size=page_size,
            )
