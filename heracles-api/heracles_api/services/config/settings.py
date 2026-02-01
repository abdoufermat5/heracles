"""
Global Settings Manager
=======================

Manages global configuration settings (categories, sections, fields).
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import structlog

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

    def __init__(self, db_pool: Any):
        """
        Initialize the settings manager.

        Args:
            db_pool: asyncpg connection pool
        """
        self._db = db_pool
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
        """
        Get all configuration categories with their settings.

        Returns:
            List of ConfigCategoryResponse objects.
        """
        async with self._db.acquire() as conn:
            # Get categories
            cat_rows = await conn.fetch("""
                SELECT id, name, label, description, icon, display_order
                FROM config_categories
                ORDER BY display_order, name
            """)

            categories = []
            for cat_row in cat_rows:
                # Get settings for this category
                setting_rows = await conn.fetch("""
                    SELECT key, value, default_value, label, description, data_type,
                           validation_rules, options, requires_restart, sensitive,
                           section, display_order, depends_on, depends_on_value
                    FROM config_settings
                    WHERE category_id = $1
                    ORDER BY display_order, key
                """, cat_row['id'])

                # Group settings by section
                sections: Dict[str, List[ConfigFieldResponse]] = {}
                for row in setting_rows:
                    section_name = row['section'] or 'default'

                    field = ConfigFieldResponse(
                        key=row['key'],
                        label=row['label'],
                        field_type=ConfigFieldType(row['data_type']),
                        value=parse_json_value(row['value']),
                        default_value=parse_json_value(row['default_value']),
                        description=row['description'],
                        validation=parse_validation(row['validation_rules']),
                        options=parse_options(row['options']),
                        requires_restart=row['requires_restart'],
                        sensitive=row['sensitive'],
                        depends_on=row['depends_on'],
                        depends_on_value=parse_json_value(row['depends_on_value']),
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
                    name=cat_row['name'],
                    label=cat_row['label'],
                    description=cat_row['description'],
                    icon=cat_row['icon'],
                    sections=section_list,
                    settings=all_settings,
                    display_order=cat_row['display_order'],
                ))

            return categories

    async def get_setting(self, category: str, key: str) -> Any:
        """
        Get a single setting value.

        Args:
            category: Category name
            key: Setting key

        Returns:
            Setting value or None if not found.
        """
        cache_key = f"config:{category}:{key}"

        # Check cache
        if self._is_cache_valid() and cache_key in self._cache:
            return self._cache[cache_key]

        async with self._db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT cs.value, cs.default_value
                FROM config_settings cs
                JOIN config_categories cc ON cs.category_id = cc.id
                WHERE cc.name = $1 AND cs.key = $2
            """, category, key)

            if row:
                raw_value = row['value'] if row['value'] is not None else row['default_value']
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
        """
        Update a configuration setting.

        Args:
            category: Category name
            key: Setting key
            value: New value
            changed_by: DN of user making the change
            reason: Optional reason for the change

        Returns:
            Tuple of (success, error_messages)
        """
        async with self._db.acquire() as conn:
            async with conn.transaction():
                # Get current setting
                row = await conn.fetchrow("""
                    SELECT cs.id, cs.value, cs.data_type, cs.validation_rules,
                           cs.read_only, cc.name as category
                    FROM config_settings cs
                    JOIN config_categories cc ON cs.category_id = cc.id
                    WHERE cc.name = $1 AND cs.key = $2
                """, category, key)

                if not row:
                    return False, [f"Setting {category}.{key} not found"]

                if row['read_only']:
                    return False, [f"Setting {category}.{key} is read-only"]

                # Validate value
                errors = validate_value(
                    value,
                    row['data_type'],
                    row['validation_rules'],
                )
                if errors:
                    return False, errors

                old_value = row['value']

                # Update setting
                await conn.execute("""
                    UPDATE config_settings
                    SET value = $1, updated_by = $2, updated_at = NOW()
                    WHERE id = $3
                """, json.dumps(value), changed_by, row['id'])

                # Record history
                await conn.execute("""
                    INSERT INTO config_history
                    (setting_id, category, setting_key, old_value, new_value, changed_by, reason)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, row['id'], category, key, old_value, json.dumps(value), changed_by, reason)

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
        """
        Update multiple settings at once.

        Args:
            settings: Dict of {category: {key: value}}
            changed_by: DN of user making the change
            reason: Optional reason

        Returns:
            Tuple of (updated_count, error_messages)
        """
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
