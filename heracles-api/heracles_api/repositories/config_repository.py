"""
Config Repository
=================

Data access layer for config_categories and config_settings tables.
"""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from heracles_api.models.config import ConfigCategory, ConfigHistory, ConfigSetting


class ConfigRepository:
    """Repository for config categories and settings."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_categories(self) -> list[ConfigCategory]:
        stmt = select(ConfigCategory).order_by(ConfigCategory.display_order, ConfigCategory.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_settings_for_category(self, category_id: uuid.UUID) -> list[ConfigSetting]:
        stmt = (
            select(ConfigSetting)
            .where(ConfigSetting.category_id == category_id)
            .order_by(ConfigSetting.display_order, ConfigSetting.key)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_setting(self, category_name: str, key: str) -> ConfigSetting | None:
        """Get a setting by category name and key (with join)."""
        stmt = (
            select(ConfigSetting)
            .join(ConfigCategory, ConfigSetting.category_id == ConfigCategory.id)
            .where(ConfigCategory.name == category_name, ConfigSetting.key == key)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_setting_with_category_name(self, category_name: str, key: str) -> tuple[ConfigSetting, str] | None:
        """Get a setting along with its category name."""
        stmt = (
            select(ConfigSetting, ConfigCategory.name)
            .join(ConfigCategory, ConfigSetting.category_id == ConfigCategory.id)
            .where(ConfigCategory.name == category_name, ConfigSetting.key == key)
        )
        result = await self.session.execute(stmt)
        row = result.one_or_none()
        return (row[0], row[1]) if row else None

    async def update_setting_value(
        self,
        setting: ConfigSetting,
        value: Any,
        changed_by: str,
    ) -> None:
        """Update a setting's value and timestamp."""
        setting.value = value
        setting.updated_by = changed_by
        setting.updated_at = func.now()

    async def insert_setting_history(
        self,
        setting_id: uuid.UUID,
        category: str,
        key: str,
        old_value: Any,
        new_value: Any,
        changed_by: str,
        reason: str | None,
    ) -> None:
        history = ConfigHistory(
            setting_id=setting_id,
            category=category,
            setting_key=key,
            old_value=old_value,
            new_value=new_value,
            changed_by=changed_by,
            reason=reason,
        )
        self.session.add(history)
