"""
Configuration Service
=====================

Core configuration service that orchestrates settings, plugins, and history.
"""

from typing import Any, Dict, List, Optional, Tuple

import structlog

from heracles_api.schemas.config import (
    ConfigCategoryResponse,
    ConfigHistoryResponse,
    GlobalConfigResponse,
    PluginConfigResponse,
)
from heracles_api.plugins.base import Plugin
from heracles_api.services.config.settings import SettingsManager
from heracles_api.services.config.plugins import PluginConfigManager
from heracles_api.services.config.history import HistoryManager

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
        self._plugin_registry: Dict[str, Plugin] = {}

        # Initialize managers
        self._settings = SettingsManager(db_pool)
        self._plugins = PluginConfigManager(db_pool, self._plugin_registry)
        self._history = HistoryManager(db_pool)

    # =========================================================================
    # Plugin Registry
    # =========================================================================

    def register_plugin(self, plugin: Plugin) -> None:
        """Register a plugin for configuration management."""
        info = plugin.info()
        self._plugin_registry[info.name] = plugin
        logger.debug("plugin_registered_for_config", plugin=info.name)

    def unregister_plugin(self, plugin_name: str) -> None:
        """Unregister a plugin."""
        if plugin_name in self._plugin_registry:
            del self._plugin_registry[plugin_name]

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
        """Get all configuration categories with their settings."""
        return await self._settings.get_categories()

    async def get_setting(self, category: str, key: str) -> Any:
        """Get a single setting value."""
        return await self._settings.get_setting(category, key)

    async def update_setting(
        self,
        category: str,
        key: str,
        value: Any,
        changed_by: str,
        reason: Optional[str] = None,
    ) -> Tuple[bool, List[str]]:
        """Update a configuration setting."""
        return await self._settings.update_setting(
            category, key, value, changed_by, reason
        )

    async def bulk_update_settings(
        self,
        settings: Dict[str, Dict[str, Any]],
        changed_by: str,
        reason: Optional[str] = None,
    ) -> Tuple[int, List[str]]:
        """Update multiple settings at once."""
        return await self._settings.bulk_update_settings(
            settings, changed_by, reason
        )

    # =========================================================================
    # Plugin Configuration
    # =========================================================================

    async def get_all_plugin_configs(self) -> List[PluginConfigResponse]:
        """Get all plugin configurations."""
        return await self._plugins.get_all_plugin_configs()

    async def get_plugin_config(self, plugin_name: str) -> Optional[PluginConfigResponse]:
        """Get a single plugin's configuration."""
        return await self._plugins.get_plugin_config(plugin_name)

    async def update_plugin_config(
        self,
        plugin_name: str,
        config: Dict[str, Any],
        changed_by: str,
        reason: Optional[str] = None,
    ) -> Tuple[bool, List[str]]:
        """Update plugin configuration."""
        return await self._plugins.update_plugin_config(
            plugin_name, config, changed_by, reason
        )

    async def update_plugin_config_with_migration(
        self,
        plugin_name: str,
        config: Dict[str, Any],
        changed_by: str,
        reason: Optional[str] = None,
        confirmed: bool = False,
        migrate_entries: bool = True,
    ) -> Dict[str, Any]:
        """Update plugin configuration with RDN migration support."""
        return await self._plugins.update_plugin_config_with_migration(
            plugin_name=plugin_name,
            config=config,
            changed_by=changed_by,
            config_service=self,
            reason=reason,
            confirmed=confirmed,
            migrate_entries=migrate_entries,
        )

    async def toggle_plugin(
        self,
        plugin_name: str,
        enabled: bool,
        changed_by: str,
        reason: Optional[str] = None,
    ) -> Tuple[bool, List[str]]:
        """Enable or disable a plugin."""
        return await self._plugins.toggle_plugin(
            plugin_name, enabled, changed_by, reason
        )

    async def register_plugin_config(self, plugin: Plugin) -> None:
        """Register a plugin's configuration schema in the database."""
        await self._plugins.register_plugin_config(plugin)
        # Also register in the main registry
        self.register_plugin(plugin)

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
        """Get configuration change history."""
        return await self._history.get_history(
            page, page_size, category, plugin_name
        )
