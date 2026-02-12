"""
Configuration Cache
===================

Caching layer for configuration values with hot-reload support.
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Optional

import structlog

if TYPE_CHECKING:
    from heracles_api.services.config.base import ConfigService

logger = structlog.get_logger(__name__)

# Global config cache
_config_cache: dict[str, Any] = {}
_config_cache_time: datetime | None = None
_CONFIG_CACHE_TTL = 60  # seconds

# Plugin config cache (separate from global config cache)
_plugin_config_cache: dict[str, dict[str, Any]] = {}
_plugin_config_cache_time: dict[str, datetime] = {}
_PLUGIN_CONFIG_CACHE_TTL = 60  # seconds

# Reference to the config service (set by init_config_service)
_config_service: Optional["ConfigService"] = None


def set_config_service(service: Optional["ConfigService"]) -> None:
    """Set the global config service reference."""
    global _config_service
    _config_service = service


def get_config_service_ref() -> Optional["ConfigService"]:
    """Get the global config service reference."""
    return _config_service


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


def invalidate_config_cache(category: str | None = None, key: str | None = None) -> None:
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
    default: dict[str, Any] | None = None,
    use_cache: bool = True,
) -> dict[str, Any]:
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


def invalidate_plugin_config_cache(plugin_name: str | None = None) -> None:
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
