"""
Plugin Configuration Manager
============================

Manages plugin-specific configuration with migration support.
"""

import json
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from heracles_api.repositories.plugin_config_repository import PluginConfigRepository
from heracles_api.schemas.config import PluginConfigResponse
from heracles_api.plugins.base import Plugin
from heracles_api.services.config.validators import convert_sections_to_response
from heracles_api.services.config.cache import invalidate_plugin_config_cache

if TYPE_CHECKING:
    from heracles_api.services.config.base import ConfigService

logger = structlog.get_logger(__name__)


class PluginConfigManager:
    """Manages plugin configuration with RDN migration support."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        plugin_registry: Dict[str, Plugin],
    ):
        self._session_factory = session_factory
        self._plugin_registry = plugin_registry

    async def get_all_plugin_configs(self) -> List[PluginConfigResponse]:
        """
        Get all plugin configurations.

        Returns plugins from database, augmented with registered plugins that
        aren't yet stored in the database.
        """
        db_plugins: Dict[str, PluginConfigResponse] = {}

        async with self._session_factory() as session:
            repo = PluginConfigRepository(session)
            rows = await repo.get_all()

            for row in rows:
                # Get schema from registered plugin if available
                plugin = self._plugin_registry.get(row.plugin_name)
                sections = []

                # Parse config JSON if it's a string
                config_data = row.config
                if isinstance(config_data, str):
                    try:
                        config_data = json.loads(config_data)
                    except (json.JSONDecodeError, TypeError):
                        config_data = {}
                config_data = config_data or {}

                if plugin:
                    schema_sections = plugin.config_schema()
                    sections = convert_sections_to_response(
                        schema_sections,
                        config_data,
                    )

                db_plugins[row.plugin_name] = PluginConfigResponse(
                    name=row.plugin_name,
                    enabled=row.enabled,
                    version=row.version or '',
                    description=row.description,
                    sections=sections,
                    config=config_data,
                    updated_at=row.updated_at,
                    updated_by=row.updated_by,
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

                sections = convert_sections_to_response(
                    schema_sections,
                    default_config,
                )

                db_plugins[plugin_name] = PluginConfigResponse(
                    name=plugin_name,
                    enabled=True,
                    version=info.version,
                    description=info.description,
                    sections=sections,
                    config=default_config,
                )

        return sorted(db_plugins.values(), key=lambda p: p.name)

    async def get_plugin_config(self, plugin_name: str) -> Optional[PluginConfigResponse]:
        """Get a single plugin's configuration."""
        async with self._session_factory() as session:
            repo = PluginConfigRepository(session)
            row = await repo.get_by_name(plugin_name)

            if not row:
                return None

            # Parse config JSON if it's a string
            config_data = row.config
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
                sections = convert_sections_to_response(
                    schema_sections,
                    config_data,
                )

            return PluginConfigResponse(
                name=row.plugin_name,
                enabled=row.enabled,
                version=row.version or '',
                description=row.description,
                sections=sections,
                config=config_data,
                updated_at=row.updated_at,
                updated_by=row.updated_by,
            )

    async def update_plugin_config(
        self,
        plugin_name: str,
        config: Dict[str, Any],
        changed_by: str,
        reason: Optional[str] = None,
    ) -> Tuple[bool, List[str]]:
        """Update plugin configuration."""
        # Get registered plugin for validation
        plugin = self._plugin_registry.get(plugin_name)
        if not plugin:
            return False, [f"Plugin '{plugin_name}' is not registered"]

        # Validate configuration using plugin's contract
        errors = plugin.validate_config(config)
        if errors:
            return False, errors

        async with self._session_factory() as session:
            repo = PluginConfigRepository(session)

            row = await repo.get_by_name(plugin_name)
            if not row:
                return False, [f"Plugin '{plugin_name}' not found in database"]

            # Parse config JSON if it's a string
            old_config = row.config
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
            await repo.update_config(row, merged_config, changed_by)

            # Record history
            await repo.insert_history(
                plugin_name=plugin_name,
                old_value=old_config,
                new_value=merged_config,
                changed_by=changed_by,
                reason=reason,
            )

            await session.commit()

            # Trigger hot-reload on plugin
            changed_keys = [
                key for key in set(list(old_config.keys()) + list(merged_config.keys()))
                if old_config.get(key) != merged_config.get(key)
            ]

            if changed_keys:
                plugin.on_config_change(old_config, merged_config, changed_keys)
                plugin._config = merged_config

            # Invalidate cache
            invalidate_plugin_config_cache(plugin_name)

            logger.info(
                "plugin_config_updated",
                plugin=plugin_name,
                changed_keys=changed_keys,
                changed_by=changed_by,
            )

            return True, []

    async def update_plugin_config_with_migration(
        self,
        plugin_name: str,
        config: Dict[str, Any],
        changed_by: str,
        config_service: "ConfigService",
        reason: Optional[str] = None,
        confirmed: bool = False,
        migrate_entries: bool = True,
    ) -> Dict[str, Any]:
        """Update plugin configuration with RDN migration support."""
        from heracles_api.services.ldap_service import get_ldap_service
        from heracles_api.services.ldap_migration_service import LdapMigrationService, MigrationMode

        # RDN settings that may require migration
        PLUGIN_RDN_SETTINGS = {
            ("dns", "dns_rdn"): "dNSZone",
            ("dhcp", "dhcp_rdn"): "dhcpService",
            ("sudo", "sudoers_rdn"): "sudoRole",
            ("systems", "systems_rdn"): "device",
        }

        # Validate config FIRST
        plugin = self._plugin_registry.get(plugin_name)
        if not plugin:
            return {"success": False, "errors": [f"Plugin '{plugin_name}' is not registered"]}

        validation_errors = plugin.validate_config(config)
        if validation_errors:
            return {"success": False, "errors": validation_errors}

        # Get current plugin config
        current_config_resp = await self.get_plugin_config(plugin_name)
        if not current_config_resp:
            return {"success": False, "errors": [f"Plugin '{plugin_name}' not found"]}

        current_config = current_config_resp.config or {}
        migration_results = []

        # Check each RDN setting that might be changing
        for key, new_value in config.items():
            setting_key = (plugin_name, key)
            if setting_key not in PLUGIN_RDN_SETTINGS:
                continue

            current_value = current_config.get(key)

            if current_value == new_value or current_value is None:
                continue

            try:
                ldap_service = get_ldap_service()
                migration_service = LdapMigrationService(ldap_service, config_service)

                object_class_filter = PLUGIN_RDN_SETTINGS[setting_key]

                check_result = await migration_service.check_rdn_change(
                    old_rdn=str(current_value),
                    new_rdn=str(new_value),
                    object_class_filter=object_class_filter,
                )

                if check_result.entries_count > 0 and not confirmed:
                    return {
                        "success": False,
                        "message": f"RDN change for '{key}' affects existing entries. Please confirm to proceed.",
                        "requires_confirmation": True,
                        "migration_check": {
                            "old_rdn": check_result.old_rdn,
                            "new_rdn": check_result.new_rdn,
                            "base_dn": check_result.base_dn,
                            "entries_count": check_result.entries_count,
                            "entries_dns": check_result.entries_dns,
                            "supports_modrdn": check_result.supports_modrdn,
                            "recommended_mode": check_result.recommended_mode.value,
                            "warnings": check_result.warnings,
                            "requires_confirmation": True,
                        },
                    }

                if check_result.entries_count > 0 and confirmed and migrate_entries:
                    mode = MigrationMode.MODRDN if check_result.supports_modrdn else MigrationMode.COPY_DELETE

                    result = await migration_service.migrate_entries(
                        old_rdn=str(current_value),
                        new_rdn=str(new_value),
                        object_class_filter=object_class_filter,
                        mode=mode,
                    )

                    migration_results.append({
                        "key": key,
                        "entries_migrated": result.entries_migrated,
                        "entries_failed": result.entries_failed,
                        "mode": result.mode.value,
                    })

                    logger.info(
                        "plugin_rdn_migration_complete",
                        plugin=plugin_name,
                        key=key,
                        old_rdn=current_value,
                        new_rdn=new_value,
                        entries_migrated=result.entries_migrated,
                        by=changed_by,
                    )

            except Exception as e:
                logger.error(
                    "plugin_rdn_migration_check_failed",
                    plugin=plugin_name,
                    key=key,
                    error=str(e),
                )

        # Proceed with the config update
        success, errors = await self.update_plugin_config(
            plugin_name=plugin_name,
            config=config,
            changed_by=changed_by,
            reason=reason,
        )

        if not success:
            return {"success": False, "errors": errors}

        response = {
            "success": True,
            "message": f"Plugin '{plugin_name}' configuration updated successfully",
        }
        if migration_results:
            response["migrations"] = migration_results

        return response

    async def toggle_plugin(
        self,
        plugin_name: str,
        enabled: bool,
        changed_by: str,
        reason: Optional[str] = None,
    ) -> Tuple[bool, List[str]]:
        """Enable or disable a plugin."""
        async with self._session_factory() as session:
            repo = PluginConfigRepository(session)

            row = await repo.get_by_name(plugin_name)
            if not row:
                return False, [f"Plugin '{plugin_name}' not found"]

            old_enabled = row.enabled

            await repo.toggle_enabled(row, enabled, changed_by)

            # Record history
            await repo.insert_history(
                plugin_name=plugin_name,
                old_value={"enabled": old_enabled},
                new_value={"enabled": enabled},
                changed_by=changed_by,
                reason=reason,
            )

            await session.commit()

            logger.info(
                "plugin_toggled",
                plugin=plugin_name,
                enabled=enabled,
                changed_by=changed_by,
            )

            return True, []

    async def register_plugin_config(self, plugin: Plugin) -> None:
        """Register a plugin's configuration schema in the database."""
        info = plugin.info()
        default_config = plugin.default_config()

        async with self._session_factory() as session:
            repo = PluginConfigRepository(session)
            await repo.upsert(
                plugin_name=info.name,
                priority=info.priority,
                config=default_config,
                version=info.version,
                description=info.description,
            )
            await session.commit()

        # Register in memory
        self._plugin_registry[info.name] = plugin

        logger.debug(
            "plugin_config_registered",
            plugin=info.name,
            version=info.version,
        )
