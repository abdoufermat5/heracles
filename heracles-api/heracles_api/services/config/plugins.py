"""
Plugin Configuration Manager
============================

Manages plugin-specific configuration with migration support.
"""

import json
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

import structlog

from heracles_api.schemas.config import PluginConfigResponse
from heracles_api.plugins.base import Plugin
from heracles_api.services.config.validators import convert_sections_to_response
from heracles_api.services.config.cache import invalidate_plugin_config_cache

if TYPE_CHECKING:
    from heracles_api.services.config.base import ConfigService

logger = structlog.get_logger(__name__)


class PluginConfigManager:
    """Manages plugin configuration with RDN migration support."""

    def __init__(self, db_pool: Any, plugin_registry: Dict[str, Plugin]):
        """
        Initialize the plugin config manager.

        Args:
            db_pool: asyncpg connection pool
            plugin_registry: Reference to the plugin registry
        """
        self._db = db_pool
        self._plugin_registry = plugin_registry

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
                    sections = convert_sections_to_response(
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

                sections = convert_sections_to_response(
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
                sections = convert_sections_to_response(
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
        """
        Update plugin configuration with RDN migration support.

        For RDN settings (like sudoers_rdn, dns_rdn, systems_rdn), this method
        checks if existing entries would be affected and handles migration.

        Args:
            plugin_name: Plugin name
            config: New configuration values
            changed_by: DN of user making the change
            config_service: Reference to ConfigService for nested calls
            reason: Optional reason for the change
            confirmed: Whether user confirmed the migration
            migrate_entries: Whether to migrate entries when RDN changes

        Returns:
            Dict with success status, message, and optional migration info
        """
        from heracles_api.services.ldap_service import get_ldap_service
        from heracles_api.services.ldap_migration_service import LdapMigrationService, MigrationMode

        # RDN settings that may require migration: (plugin_name, key) -> objectClass filter
        PLUGIN_RDN_SETTINGS = {
            ("dns", "dns_rdn"): "dNSZone",
            ("dhcp", "dhcp_rdn"): "dhcpService",
            ("sudo", "sudoers_rdn"): "sudoRole",
            ("systems", "systems_rdn"): "device",
        }

        # IMPORTANT: Validate config FIRST before any migrations
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

            # Only check if value is actually changing
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

                # If entries exist and not confirmed, return warning
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

                # If confirmed and should migrate, perform migration
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
                # Don't block the update, just log the error

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

    async def register_plugin_config(self, plugin: Plugin) -> None:
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
        self._plugin_registry[info.name] = plugin

        logger.debug(
            "plugin_config_registered",
            plugin=info.name,
            version=info.version,
        )
