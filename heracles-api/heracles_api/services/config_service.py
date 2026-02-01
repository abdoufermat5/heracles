"""
Configuration Service
=====================

Service for managing application and plugin configuration.
Provides centralized access to settings with caching and hot-reload support.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import structlog
from pydantic import BaseModel

from heracles_api.schemas.config import (
    ConfigCategoryResponse,
    ConfigFieldResponse,
    ConfigFieldType,
    ConfigFieldValidation,
    ConfigFieldOption,
    ConfigHistoryEntry,
    ConfigHistoryResponse,
    ConfigSectionResponse,
    GlobalConfigResponse,
    PluginConfigResponse,
)
from heracles_api.plugins.base import (
    ConfigField,
    ConfigSection,
    ConfigFieldType as BaseConfigFieldType,
    Plugin,
)

logger = structlog.get_logger(__name__)


class ConfigService:
    """
    Service for managing application configuration.
    
    Features:
    - Centralized configuration storage in PostgreSQL
    - Per-plugin configuration with JSON Schema validation
    - Hot-reload support (immediate config updates)
    - Configuration history/audit trail
    - Caching for performance
    """
    
    def __init__(self, db_pool: Any, redis_client: Any = None):
        """
        Initialize the config service.
        
        Args:
            db_pool: asyncpg connection pool
            redis_client: Optional Redis client for caching
        """
        self._db = db_pool
        self._redis = redis_client
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 60  # seconds
        self._cache_time: Optional[datetime] = None
        self._plugin_registry: Dict[str, Plugin] = {}
    
    def register_plugin(self, plugin: Plugin) -> None:
        """Register a plugin for configuration management."""
        info = plugin.info()
        self._plugin_registry[info.name] = plugin
        logger.debug("plugin_registered_for_config", plugin=info.name)
    
    def unregister_plugin(self, plugin_name: str) -> None:
        """Unregister a plugin."""
        if plugin_name in self._plugin_registry:
            del self._plugin_registry[plugin_name]
    
    def _parse_json_value(self, value: Any) -> Any:
        """
        Parse a JSON value from database storage.
        
        Values are stored as JSON strings in the database.
        Returns the parsed value or the original if parsing fails.
        """
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return value
    
    # =========================================================================
    # Global Configuration
    # =========================================================================
    
    async def get_all_config(self) -> GlobalConfigResponse:
        """
        Get all configuration: categories and plugins.
        
        Returns:
            GlobalConfigResponse with all categories and plugin configs.
        """
        categories = await self.get_categories()
        plugins = await self.get_all_plugin_configs()
        
        return GlobalConfigResponse(
            categories=categories,
            plugins=plugins,
        )
    
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
                        value=self._parse_json_value(row['value']),
                        default_value=self._parse_json_value(row['default_value']),
                        description=row['description'],
                        validation=self._parse_validation(row['validation_rules']),
                        options=self._parse_options(row['options']),
                        requires_restart=row['requires_restart'],
                        sensitive=row['sensitive'],
                        depends_on=row['depends_on'],
                        depends_on_value=self._parse_json_value(row['depends_on_value']),
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
                value = self._parse_json_value(raw_value)
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
                errors = self._validate_value(
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
    
    # =========================================================================
    # Plugin Configuration
    # =========================================================================
    
    async def get_all_plugin_configs(self) -> List[PluginConfigResponse]:
        """
        Get all plugin configurations.
        
        Returns plugins from database, augmented with registered plugins that
        aren't yet stored in the database.
        
        Returns:
            List of PluginConfigResponse objects.
        """
        db_plugins: Dict[str, PluginConfigResponse] = {}
        
        async with self._db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT plugin_name, enabled, priority, config, config_schema,
                       version, description, updated_at, updated_by
                FROM plugin_configs
                ORDER BY priority, plugin_name
            """)
            
            for row in rows:
                # Get schema from registered plugin if available
                plugin = self._plugin_registry.get(row['plugin_name'])
                sections = []
                
                # Parse config JSON if it's a string
                config_data = row['config']
                if isinstance(config_data, str):
                    try:
                        config_data = json.loads(config_data)
                    except (json.JSONDecodeError, TypeError):
                        config_data = {}
                config_data = config_data or {}
                
                if plugin:
                    # Use plugin's config_schema method
                    schema_sections = plugin.config_schema()
                    sections = self._convert_sections_to_response(
                        schema_sections,
                        config_data,
                    )
                
                db_plugins[row['plugin_name']] = PluginConfigResponse(
                    name=row['plugin_name'],
                    enabled=row['enabled'],
                    version=row['version'] or '',
                    description=row['description'],
                    sections=sections,
                    config=config_data,
                    updated_at=row['updated_at'],
                    updated_by=row['updated_by'],
                )
        
        # Add registered plugins that aren't in the database
        for plugin_name, plugin in self._plugin_registry.items():
            if plugin_name not in db_plugins:
                info = plugin.info()
                schema_sections = plugin.config_schema()
                
                # Build default config from schema
                default_config = {}
                for section in schema_sections:
                    for field in section.fields:
                        default_config[field.key] = field.default_value
                
                sections = self._convert_sections_to_response(
                    schema_sections,
                    default_config,
                )
                
                db_plugins[plugin_name] = PluginConfigResponse(
                    name=plugin_name,
                    enabled=True,  # Default to enabled
                    version=info.version,
                    description=info.description,
                    sections=sections,
                    config=default_config,
                )
        
        # Return sorted by name
        return sorted(db_plugins.values(), key=lambda p: p.name)
    
    async def get_plugin_config(self, plugin_name: str) -> Optional[PluginConfigResponse]:
        """
        Get a single plugin's configuration.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            PluginConfigResponse or None if not found.
        """
        async with self._db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT plugin_name, enabled, priority, config, config_schema,
                       version, description, updated_at, updated_by
                FROM plugin_configs
                WHERE plugin_name = $1
            """, plugin_name)
            
            if not row:
                return None
            
            # Parse config JSON if it's a string
            config_data = row['config']
            if isinstance(config_data, str):
                try:
                    config_data = json.loads(config_data)
                except (json.JSONDecodeError, TypeError):
                    config_data = {}
            config_data = config_data or {}
            
            # Get schema from registered plugin
            plugin = self._plugin_registry.get(plugin_name)
            sections = []
            
            if plugin:
                schema_sections = plugin.config_schema()
                sections = self._convert_sections_to_response(
                    schema_sections,
                    config_data,
                )
            
            return PluginConfigResponse(
                name=row['plugin_name'],
                enabled=row['enabled'],
                version=row['version'] or '',
                description=row['description'],
                sections=sections,
                config=config_data,
                updated_at=row['updated_at'],
                updated_by=row['updated_by'],
            )
    
    async def update_plugin_config(
        self,
        plugin_name: str,
        config: Dict[str, Any],
        changed_by: str,
        reason: Optional[str] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Update plugin configuration.
        
        Validates against plugin's schema and triggers hot-reload.
        
        Args:
            plugin_name: Plugin name
            config: New configuration
            changed_by: DN of user making the change
            reason: Optional reason
            
        Returns:
            Tuple of (success, error_messages)
        """
        # Get registered plugin for validation
        plugin = self._plugin_registry.get(plugin_name)
        if not plugin:
            return False, [f"Plugin '{plugin_name}' is not registered"]
        
        # Validate configuration using plugin's contract
        errors = plugin.validate_config(config)
        if errors:
            return False, errors
        
        async with self._db.acquire() as conn:
            async with conn.transaction():
                # Get current config
                row = await conn.fetchrow("""
                    SELECT id, config FROM plugin_configs WHERE plugin_name = $1
                """, plugin_name)
                
                if not row:
                    return False, [f"Plugin '{plugin_name}' not found in database"]
                
                # Parse config JSON if it's a string
                old_config = row['config']
                if isinstance(old_config, str):
                    try:
                        old_config = json.loads(old_config)
                    except (json.JSONDecodeError, TypeError):
                        old_config = {}
                old_config = old_config or {}
                
                # Merge with defaults
                defaults = plugin.default_config()
                merged_config = {**defaults, **config}
                
                # Update database
                await conn.execute("""
                    UPDATE plugin_configs
                    SET config = $1, updated_by = $2, updated_at = NOW()
                    WHERE plugin_name = $3
                """, json.dumps(merged_config), changed_by, plugin_name)
                
                # Record history
                await conn.execute("""
                    INSERT INTO config_history 
                    (plugin_name, old_value, new_value, changed_by, reason)
                    VALUES ($1, $2, $3, $4, $5)
                """, plugin_name, json.dumps(old_config), json.dumps(merged_config), changed_by, reason)
                
                # Trigger hot-reload on plugin
                changed_keys = [
                    key for key in set(list(old_config.keys()) + list(merged_config.keys()))
                    if old_config.get(key) != merged_config.get(key)
                ]
                
                if changed_keys:
                    plugin.on_config_change(old_config, merged_config, changed_keys)
                    plugin._config = merged_config
                
                # Invalidate cache (both internal and global)
                self._invalidate_cache(f"plugin:{plugin_name}")
                invalidate_plugin_config_cache(plugin_name)
                
                logger.info(
                    "plugin_config_updated",
                    plugin=plugin_name,
                    changed_keys=changed_keys,
                    changed_by=changed_by,
                )
                
                logger.info(
                    "plugin_config_updated",
                    plugin=plugin_name,
                    changed_keys=changed_keys,
                    changed_by=changed_by,
                )
                
                return True, []
    
    async def toggle_plugin(
        self,
        plugin_name: str,
        enabled: bool,
        changed_by: str,
        reason: Optional[str] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Enable or disable a plugin.
        
        Args:
            plugin_name: Plugin name
            enabled: Whether to enable
            changed_by: DN of user
            reason: Optional reason
            
        Returns:
            Tuple of (success, error_messages)
        """
        async with self._db.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow("""
                    SELECT id, enabled FROM plugin_configs WHERE plugin_name = $1
                """, plugin_name)
                
                if not row:
                    return False, [f"Plugin '{plugin_name}' not found"]
                
                old_enabled = row['enabled']
                
                await conn.execute("""
                    UPDATE plugin_configs
                    SET enabled = $1, updated_by = $2, updated_at = NOW()
                    WHERE plugin_name = $3
                """, enabled, changed_by, plugin_name)
                
                # Record history
                await conn.execute("""
                    INSERT INTO config_history 
                    (plugin_name, old_value, new_value, changed_by, reason)
                    VALUES ($1, $2, $3, $4, $5)
                """, plugin_name, json.dumps({"enabled": old_enabled}), 
                    json.dumps({"enabled": enabled}), changed_by, reason)
                
                logger.info(
                    "plugin_toggled",
                    plugin=plugin_name,
                    enabled=enabled,
                    changed_by=changed_by,
                )
                
                return True, []
    
    async def register_plugin_config(
        self,
        plugin: Plugin,
    ) -> None:
        """
        Register a plugin's configuration schema in the database.
        
        Called during plugin loading to ensure the plugin has a DB record.
        
        Args:
            plugin: Plugin instance
        """
        info = plugin.info()
        default_config = plugin.default_config()
        
        async with self._db.acquire() as conn:
            # Upsert plugin config
            await conn.execute("""
                INSERT INTO plugin_configs (plugin_name, enabled, priority, config, version, description)
                VALUES ($1, true, $2, $3, $4, $5)
                ON CONFLICT (plugin_name) DO UPDATE
                SET version = EXCLUDED.version,
                    description = EXCLUDED.description,
                    config = COALESCE(plugin_configs.config, EXCLUDED.config)
            """, info.name, info.priority, json.dumps(default_config), 
                info.version, info.description)
        
        # Register in memory
        self.register_plugin(plugin)
        
        logger.debug(
            "plugin_config_registered",
            plugin=info.name,
            version=info.version,
        )
    
    # =========================================================================
    # Configuration History
    # =========================================================================
    
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
    
    # =========================================================================
    # Helpers
    # =========================================================================
    
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
    
    def _parse_validation(self, rules: Optional[Any]) -> Optional[ConfigFieldValidation]:
        """Parse validation rules from JSON/JSONB."""
        if not rules:
            return None
        
        # Handle case where rules might be a string (needs JSON parsing)
        if isinstance(rules, str):
            try:
                rules = json.loads(rules)
            except json.JSONDecodeError:
                logger.warning("invalid_validation_rules_json", rules=rules)
                return None
        
        if not isinstance(rules, dict):
            logger.warning("validation_rules_not_a_dict", type=type(rules).__name__)
            return None
        
        return ConfigFieldValidation(
            required=rules.get('required', True),
            min_value=rules.get('min'),
            max_value=rules.get('max'),
            min_length=rules.get('minLength'),
            max_length=rules.get('maxLength'),
            pattern=rules.get('pattern'),
        )
    
    def _parse_options(self, options: Optional[Any]) -> Optional[List[ConfigFieldOption]]:
        """Parse options from JSON/JSONB."""
        if not options:
            return None
        
        # Handle case where options might be a string (needs JSON parsing)
        if isinstance(options, str):
            try:
                options = json.loads(options)
            except json.JSONDecodeError:
                logger.warning("invalid_options_json", options=options)
                return None
        
        # Now options should be a list
        if not isinstance(options, list):
            logger.warning("options_not_a_list", type=type(options).__name__)
            return None
        
        return [
            ConfigFieldOption(
                value=opt['value'],
                label=opt['label'],
                description=opt.get('description'),
            )
            for opt in options
        ]
    
    def _validate_value(
        self,
        value: Any,
        data_type: str,
        validation_rules: Optional[Dict],
    ) -> List[str]:
        """Validate a value against its type and rules."""
        errors = []
        rules = validation_rules or {}
        
        # Type validation
        type_validators = {
            'string': lambda v: isinstance(v, str),
            'integer': lambda v: isinstance(v, int) and not isinstance(v, bool),
            'boolean': lambda v: isinstance(v, bool),
            'float': lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            'list': lambda v: isinstance(v, list),
            'select': lambda v: True,
            'multiselect': lambda v: isinstance(v, list),
        }
        
        validator = type_validators.get(data_type)
        if validator and not validator(value):
            errors.append(f"Invalid type: expected {data_type}")
            return errors
        
        # Range validation
        if data_type in ('integer', 'float'):
            if 'min' in rules and value < rules['min']:
                errors.append(f"Value must be at least {rules['min']}")
            if 'max' in rules and value > rules['max']:
                errors.append(f"Value must be at most {rules['max']}")
        
        # Length validation
        if data_type == 'string':
            if 'minLength' in rules and len(value) < rules['minLength']:
                errors.append(f"Must be at least {rules['minLength']} characters")
            if 'maxLength' in rules and len(value) > rules['maxLength']:
                errors.append(f"Must be at most {rules['maxLength']} characters")
        
        return errors
    
    def _convert_sections_to_response(
        self,
        sections: List[ConfigSection],
        current_config: Dict[str, Any],
    ) -> List[ConfigSectionResponse]:
        """Convert plugin ConfigSection objects to response format."""
        result = []
        
        for section in sections:
            fields = []
            for field in section.fields:
                # Get current value or default
                value = current_config.get(field.key, field.default_value)
                
                # Convert validation
                validation = None
                if field.validation:
                    validation = ConfigFieldValidation(
                        required=field.validation.required,
                        min_value=field.validation.min_value,
                        max_value=field.validation.max_value,
                        min_length=field.validation.min_length,
                        max_length=field.validation.max_length,
                        pattern=field.validation.pattern,
                    )
                
                # Convert options
                options = None
                if field.options:
                    options = [
                        ConfigFieldOption(
                            value=opt.value,
                            label=opt.label,
                            description=opt.description,
                        )
                        for opt in field.options
                    ]
                
                fields.append(ConfigFieldResponse(
                    key=field.key,
                    label=field.label,
                    field_type=ConfigFieldType(field.field_type.value),
                    value=value,
                    default_value=field.default_value,
                    description=field.description,
                    validation=validation,
                    options=options,
                    requires_restart=field.requires_restart,
                    sensitive=field.sensitive,
                    depends_on=field.depends_on,
                    depends_on_value=field.depends_on_value,
                ))
            
            result.append(ConfigSectionResponse(
                id=section.id,
                label=section.label,
                description=section.description,
                icon=section.icon,
                fields=fields,
                order=section.order,
            ))
        
        return result


# Global service instance (initialized at startup)
_config_service: Optional[ConfigService] = None

# In-memory cache for synchronous access (hot-reload friendly)
_config_cache: Dict[str, Any] = {}
_config_cache_time: Optional[datetime] = None
_CONFIG_CACHE_TTL = 60  # seconds


def get_config_service() -> ConfigService:
    """Get the global config service instance."""
    if _config_service is None:
        raise RuntimeError("Config service not initialized")
    return _config_service


def init_config_service(db_pool: Any, redis_client: Any = None) -> ConfigService:
    """Initialize the global config service."""
    global _config_service
    _config_service = ConfigService(db_pool, redis_client)
    return _config_service


def is_config_service_available() -> bool:
    """Check if the config service is initialized and available."""
    return _config_service is not None


async def get_config_value(
    category: str,
    key: str,
    default: Any = None,
    use_cache: bool = True,
) -> Any:
    """
    Get a configuration value from the database with fallback support.
    
    This is the primary way for other services to read configuration.
    Supports caching and graceful fallback to default values.
    
    Args:
        category: Configuration category (e.g., 'session', 'password', 'security')
        key: Configuration key within the category
        default: Default value to return if config service unavailable or key not found
        use_cache: Whether to use the in-memory cache (default: True)
        
    Returns:
        Configuration value or default if not found/unavailable
    """
    global _config_cache, _config_cache_time
    
    cache_key = f"{category}:{key}"
    
    # Check cache first if enabled
    if use_cache and _config_cache_time is not None:
        if datetime.now() - _config_cache_time < timedelta(seconds=_CONFIG_CACHE_TTL):
            if cache_key in _config_cache:
                return _config_cache[cache_key]
    
    # Try to get from config service
    if _config_service is None:
        logger.warning(
            "config_service_unavailable_fallback",
            category=category,
            key=key,
            default=default,
        )
        return default
    
    try:
        value = await _config_service.get_setting(category, key)
        
        if value is None:
            logger.debug(
                "config_key_not_found_fallback",
                category=category,
                key=key,
                default=default,
            )
            return default
        
        # Update cache
        _config_cache[cache_key] = value
        _config_cache_time = datetime.now()
        
        return value
        
    except Exception as e:
        logger.warning(
            "config_service_error_fallback",
            category=category,
            key=key,
            error=str(e),
            default=default,
        )
        return default


def invalidate_config_cache(category: Optional[str] = None, key: Optional[str] = None) -> None:
    """
    Invalidate the config cache for hot-reload support.
    
    Called when configuration is updated to ensure services pick up new values.
    
    Args:
        category: Optional category to invalidate (invalidates all if None)
        key: Optional key within category to invalidate
    """
    global _config_cache, _config_cache_time
    
    if category and key:
        cache_key = f"{category}:{key}"
        _config_cache.pop(cache_key, None)
        logger.debug("config_cache_invalidated", key=cache_key)
    elif category:
        # Remove all keys in this category
        keys_to_remove = [k for k in _config_cache if k.startswith(f"{category}:")]
        for k in keys_to_remove:
            _config_cache.pop(k, None)
        logger.debug("config_cache_category_invalidated", category=category)
    else:
        _config_cache.clear()
        _config_cache_time = None
        logger.debug("config_cache_cleared")


# =============================================================================
# Plugin Configuration Helpers
# =============================================================================

# Plugin config cache (separate from global config cache)
_plugin_config_cache: Dict[str, Dict[str, Any]] = {}
_plugin_config_cache_time: Dict[str, datetime] = {}
_PLUGIN_CONFIG_CACHE_TTL = 60  # seconds


async def get_plugin_config_value(
    plugin_name: str,
    key: str,
    default: Any = None,
    use_cache: bool = True,
) -> Any:
    """
    Get a plugin configuration value from the database with fallback support.
    
    This is the primary way for plugin services to read their configuration
    at runtime with hot-reload support.
    
    Args:
        plugin_name: Name of the plugin (e.g., 'ssh', 'sudo', 'systems')
        key: Configuration key within the plugin's config
        default: Default value to return if config unavailable or key not found
        use_cache: Whether to use the in-memory cache (default: True)
        
    Returns:
        Configuration value or default if not found/unavailable
    """
    global _plugin_config_cache, _plugin_config_cache_time
    
    # Check cache first if enabled
    if use_cache and plugin_name in _plugin_config_cache_time:
        if datetime.now() - _plugin_config_cache_time[plugin_name] < timedelta(seconds=_PLUGIN_CONFIG_CACHE_TTL):
            if plugin_name in _plugin_config_cache:
                config = _plugin_config_cache[plugin_name]
                return config.get(key, default)
    
    # Try to get from config service
    if _config_service is None:
        logger.warning(
            "config_service_unavailable_fallback",
            plugin=plugin_name,
            key=key,
            default=default,
        )
        return default
    
    try:
        plugin_config = await _config_service.get_plugin_config(plugin_name)
        
        if plugin_config is None:
            logger.debug(
                "plugin_config_not_found_fallback",
                plugin=plugin_name,
                key=key,
                default=default,
            )
            return default
        
        # Update cache with full plugin config
        _plugin_config_cache[plugin_name] = plugin_config.config
        _plugin_config_cache_time[plugin_name] = datetime.now()
        
        return plugin_config.config.get(key, default)
        
    except Exception as e:
        logger.warning(
            "plugin_config_error_fallback",
            plugin=plugin_name,
            key=key,
            error=str(e),
            default=default,
        )
        return default


async def get_full_plugin_config(
    plugin_name: str,
    default: Optional[Dict[str, Any]] = None,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """
    Get the full configuration dictionary for a plugin.
    
    Args:
        plugin_name: Name of the plugin
        default: Default config to return if unavailable
        use_cache: Whether to use the in-memory cache
        
    Returns:
        Plugin configuration dictionary or default
    """
    global _plugin_config_cache, _plugin_config_cache_time
    
    default = default or {}
    
    # Check cache
    if use_cache and plugin_name in _plugin_config_cache_time:
        if datetime.now() - _plugin_config_cache_time[plugin_name] < timedelta(seconds=_PLUGIN_CONFIG_CACHE_TTL):
            if plugin_name in _plugin_config_cache:
                return _plugin_config_cache[plugin_name]
    
    if _config_service is None:
        return default
    
    try:
        plugin_config = await _config_service.get_plugin_config(plugin_name)
        
        if plugin_config is None:
            return default
        
        _plugin_config_cache[plugin_name] = plugin_config.config
        _plugin_config_cache_time[plugin_name] = datetime.now()
        
        return plugin_config.config
        
    except Exception:
        return default


def invalidate_plugin_config_cache(plugin_name: Optional[str] = None) -> None:
    """
    Invalidate the plugin config cache for hot-reload support.
    
    Args:
        plugin_name: Optional plugin name to invalidate (all if None)
    """
    global _plugin_config_cache, _plugin_config_cache_time
    
    if plugin_name:
        _plugin_config_cache.pop(plugin_name, None)
        _plugin_config_cache_time.pop(plugin_name, None)
        logger.debug("plugin_config_cache_invalidated", plugin=plugin_name)
    else:
        _plugin_config_cache.clear()
        _plugin_config_cache_time.clear()
        logger.debug("plugin_config_cache_cleared")
