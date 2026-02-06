"""
Plugin Config Repository
========================

Data access layer for plugin_configs table.
"""

from typing import Any, Dict, Optional

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from heracles_api.models.config import ConfigHistory, PluginConfig


class PluginConfigRepository:
    """Repository for plugin configuration."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> list[PluginConfig]:
        stmt = select(PluginConfig).order_by(
            PluginConfig.priority, PluginConfig.plugin_name
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_name(self, plugin_name: str) -> Optional[PluginConfig]:
        stmt = select(PluginConfig).where(
            PluginConfig.plugin_name == plugin_name
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_config(
        self,
        plugin: PluginConfig,
        config: Dict[str, Any],
        changed_by: str,
    ) -> None:
        plugin.config = config
        plugin.updated_by = changed_by
        plugin.updated_at = func.now()

    async def toggle_enabled(
        self,
        plugin: PluginConfig,
        enabled: bool,
        changed_by: str,
    ) -> None:
        plugin.enabled = enabled
        plugin.updated_by = changed_by
        plugin.updated_at = func.now()

    async def upsert(
        self,
        plugin_name: str,
        priority: int,
        config: Dict[str, Any],
        version: str,
        description: str,
    ) -> None:
        stmt = pg_insert(PluginConfig).values(
            plugin_name=plugin_name,
            enabled=True,
            priority=priority,
            config=config,
            version=version,
            description=description,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["plugin_name"],
            set_={
                "version": stmt.excluded.version,
                "description": stmt.excluded.description,
                "config": func.coalesce(
                    PluginConfig.config, stmt.excluded.config
                ),
            },
        )
        await self.session.execute(stmt)

    async def insert_history(
        self,
        plugin_name: str,
        old_value: Any,
        new_value: Any,
        changed_by: str,
        reason: Optional[str],
    ) -> None:
        history = ConfigHistory(
            plugin_name=plugin_name,
            old_value=old_value,
            new_value=new_value,
            changed_by=changed_by,
            reason=reason,
        )
        self.session.add(history)
