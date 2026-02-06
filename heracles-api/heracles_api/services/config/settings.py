"""
Global Settings Manager
=======================

Manages global configuration settings (categories, sections, fields).
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from heracles_api.repositories.config_repository import ConfigRepository
from heracles_api.schemas.config import (
    ConfigCategoryResponse,
    ConfigFieldResponse,
    ConfigFieldType,
    ConfigSectionResponse,
)
from heracles_api.services.config.validators import (
    parse_json_value,
    parse_options,
    parse_validation,
    validate_value,
)
from heracles_api.services.config.cache import invalidate_config_cache

logger = structlog.get_logger(__name__)


class SettingsManager:
    """Manages global configuration settings."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 60  # seconds
        self._cache_time: Optional[datetime] = None

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if self._cache_time is None:
            return False
        return datetime.now() - self._cache_time < timedelta(seconds=self._cache_ttl)

    def _invalidate_cache(self, key: Optional[str] = None) -> None:
        """Invalidate cache."""
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()
        self._cache_time = datetime.now()

    async def get_categories(self) -> List[ConfigCategoryResponse]:
        """Get all configuration categories with their settings."""
        async with self._session_factory() as session:
            repo = ConfigRepository(session)

            cat_rows = await repo.get_all_categories()

            categories = []
            for cat in cat_rows:
                setting_rows = await repo.get_settings_for_category(cat.id)

                # Group settings by section
                sections: Dict[str, List[ConfigFieldResponse]] = {}
                for setting in setting_rows:
                    section_name = setting.section or 'default'

                    field = ConfigFieldResponse(
                        key=setting.key,
                        label=setting.label,
                        field_type=ConfigFieldType(setting.data_type),
                        value=parse_json_value(setting.value),
                        default_value=parse_json_value(setting.default_value),
                        description=setting.description,
                        validation=parse_validation(setting.validation_rules),
                        options=parse_options(setting.options),
                        requires_restart=setting.requires_restart,
                        sensitive=setting.sensitive,
                        depends_on=setting.depends_on,
                        depends_on_value=parse_json_value(setting.depends_on_value),
                    )

                    if section_name not in sections:
                        sections[section_name] = []
                    sections[section_name].append(field)

                # Build sections list
                section_list = [
                    ConfigSectionResponse(
                        id=name,
                        label=name.replace('_', ' ').title() if name != 'default' else 'General',
                        fields=fields,
                    )
                    for name, fields in sections.items()
                ]

                # Build flat settings list for easy frontend access
                all_settings = []
                for fields_list in sections.values():
                    all_settings.extend(fields_list)

                categories.append(ConfigCategoryResponse(
                    name=cat.name,
                    label=cat.label,
                    description=cat.description,
                    icon=cat.icon,
                    sections=section_list,
                    settings=all_settings,
                    display_order=cat.display_order,
                ))

            return categories

    async def get_setting(self, category: str, key: str) -> Any:
        """Get a single setting value."""
        cache_key = f"config:{category}:{key}"

        # Check cache
        if self._is_cache_valid() and cache_key in self._cache:
            return self._cache[cache_key]

        async with self._session_factory() as session:
            repo = ConfigRepository(session)
            setting = await repo.get_setting(category, key)

            if setting:
                raw_value = setting.value if setting.value is not None else setting.default_value
                value = parse_json_value(raw_value)
                self._cache[cache_key] = value
                return value

            return None

    async def update_setting(
        self,
        category: str,
        key: str,
        value: Any,
        changed_by: str,
        reason: Optional[str] = None,
    ) -> Tuple[bool, List[str]]:
        """Update a configuration setting."""
        async with self._session_factory() as session:
            repo = ConfigRepository(session)

            setting = await repo.get_setting(category, key)

            if not setting:
                return False, [f"Setting {category}.{key} not found"]

            if getattr(setting, 'read_only', False):
                return False, [f"Setting {category}.{key} is read-only"]

            # Validate value
            errors = validate_value(
                value,
                setting.data_type,
                setting.validation_rules,
            )
            if errors:
                return False, errors

            old_value = setting.value

            # Update setting
            await repo.update_setting_value(setting, value, changed_by)

            # Record history
            await repo.insert_setting_history(
                setting_id=setting.id,
                category=category,
                key=key,
                old_value=old_value,
                new_value=value,
                changed_by=changed_by,
                reason=reason,
            )

            await session.commit()

            # Invalidate internal cache
            self._invalidate_cache(f"config:{category}:{key}")

            # Invalidate global config cache for hot-reload
            invalidate_config_cache(category, key)

            # Invalidate rate limit cache if security settings changed
            if category == "security" and key.startswith("rate_limit"):
                try:
                    from heracles_api.middleware.rate_limit import invalidate_rate_limit_cache
                    invalidate_rate_limit_cache()
                except ImportError:
                    pass

            logger.info(
                "config_setting_updated",
                category=category,
                key=key,
                changed_by=changed_by,
            )

            return True, []

    async def bulk_update_settings(
        self,
        settings: Dict[str, Dict[str, Any]],
        changed_by: str,
        reason: Optional[str] = None,
    ) -> Tuple[int, List[str]]:
        """Update multiple settings at once."""
        errors = []
        updated = 0

        for category, category_settings in settings.items():
            for key, value in category_settings.items():
                success, setting_errors = await self.update_setting(
                    category, key, value, changed_by, reason
                )
                if success:
                    updated += 1
                else:
                    errors.extend(setting_errors)

        return updated, errors
