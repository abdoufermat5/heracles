"""
Config History Repository
=========================

Data access layer for config_history table.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from heracles_api.models.config import ConfigHistory


class ConfigHistoryRepository:
    """Repository for configuration change history."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_history(
        self,
        page: int,
        page_size: int,
        category: str | None = None,
        plugin_name: str | None = None,
    ) -> tuple[list[ConfigHistory], int]:
        conditions = []
        if category:
            conditions.append(ConfigHistory.category == category)
        if plugin_name:
            conditions.append(ConfigHistory.plugin_name == plugin_name)

        count_stmt = select(func.count()).select_from(ConfigHistory)
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total = (await self.session.execute(count_stmt)).scalar_one()

        query_stmt = (
            select(ConfigHistory)
            .order_by(ConfigHistory.changed_at.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        if conditions:
            query_stmt = query_stmt.where(*conditions)

        result = await self.session.execute(query_stmt)
        return list(result.scalars().all()), total
