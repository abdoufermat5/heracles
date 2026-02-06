"""
Configuration Service Package
=============================

Modular configuration management for Heracles.
"""

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from heracles_api.services.config.base import ConfigService
from heracles_api.services.config.settings import SettingsManager
from heracles_api.services.config.plugins import PluginConfigManager
from heracles_api.services.config.history import HistoryManager
from heracles_api.services.config.cache import (
    get_config_value,
    get_plugin_config_value,
    get_full_plugin_config,
    invalidate_config_cache,
    invalidate_plugin_config_cache,
    set_config_service,
)
from heracles_api.services.config.validators import (
    parse_json_value,
    parse_options,
    parse_validation,
    validate_value,
    convert_sections_to_response,
)

# Global service instance
_config_service: Optional[ConfigService] = None


def get_config_service() -> ConfigService:
    """Get the global config service instance."""
    if _config_service is None:
        raise RuntimeError("Config service not initialized")
    return _config_service


def init_config_service(
    session_factory: async_sessionmaker[AsyncSession],
    redis_client: Any = None,
) -> ConfigService:
    """Initialize the global config service."""
    global _config_service
    _config_service = ConfigService(session_factory, redis_client)
    # Set reference in cache module
    set_config_service(_config_service)
    return _config_service


def is_config_service_available() -> bool:
    """Check if the config service is initialized and available."""
    return _config_service is not None


__all__ = [
    # Main service
    "ConfigService",
    "get_config_service",
    "init_config_service",
    "is_config_service_available",
    # Managers
    "SettingsManager",
    "PluginConfigManager",
    "HistoryManager",
    # Cache functions
    "get_config_value",
    "get_plugin_config_value",
    "get_full_plugin_config",
    "invalidate_config_cache",
    "invalidate_plugin_config_cache",
    # Validators
    "parse_json_value",
    "parse_options",
    "parse_validation",
    "validate_value",
    "convert_sections_to_response",
]
