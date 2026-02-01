"""
Plugin Loader
=============

Discovers and loads plugins from the heracles_plugins package.
Integrates with ConfigService for plugin configuration management.
"""

import importlib
import pkgutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

import structlog

from .base import Plugin
from .registry import plugin_registry

logger = structlog.get_logger(__name__)


def discover_plugins(plugins_package: str = "heracles_plugins") -> List[Type[Plugin]]:
    """
    Discover all available plugins.
    
    Scans the plugins package for modules with a __plugin__ export.
    
    Args:
        plugins_package: Package name to scan for plugins.
        
    Returns:
        List of plugin classes found.
    """
    plugins = []
    
    try:
        package = importlib.import_module(plugins_package)
    except ImportError:
        logger.warning("plugins_package_not_found", package=plugins_package)
        return plugins
    
    package_path = getattr(package, "__path__", None)
    if not package_path:
        return plugins
    
    for finder, name, ispkg in pkgutil.iter_modules(package_path):
        if not ispkg:
            continue
        
        try:
            module = importlib.import_module(f"{plugins_package}.{name}")
            
            if hasattr(module, "__plugin__"):
                plugin_class = module.__plugin__
                
                if isinstance(plugin_class, type) and issubclass(plugin_class, Plugin):
                    plugins.append(plugin_class)
                    logger.debug("plugin_discovered", name=name)
                else:
                    logger.warning(
                        "invalid_plugin_export",
                        name=name,
                        type=type(plugin_class).__name__,
                    )
            else:
                logger.debug("no_plugin_export", name=name)
                
        except ImportError as e:
            logger.warning("plugin_import_failed", name=name, error=str(e))
        except Exception as e:
            logger.error("plugin_discovery_error", name=name, error=str(e))
    
    return plugins


def load_enabled_plugins(
    config: Dict[str, Any],
    ldap_service: Any,
    plugins_package: str = "heracles_plugins",
) -> List[Plugin]:
    """
    Load and activate enabled plugins.
    
    Args:
        config: Application configuration with plugins section.
        ldap_service: LDAP service instance for plugin use.
        plugins_package: Package name to scan for plugins.
        
    Returns:
        List of loaded and activated plugin instances.
        
    Raises:
        ValueError: If a required plugin or dependency is missing.
    """
    # Get configuration
    plugins_config = config.get("plugins", {})
    enabled_names = plugins_config.get("enabled", [])
    plugin_configs = plugins_config.get("config", {})
    
    if not enabled_names:
        logger.info("no_plugins_enabled")
        return []
    
    # Set LDAP service on registry
    plugin_registry.set_ldap_service(ldap_service)
    
    # Discover available plugins
    available = {}
    for plugin_class in discover_plugins(plugins_package):
        info = plugin_class.info()
        available[info.name] = plugin_class
    
    logger.info(
        "plugins_available",
        available=list(available.keys()),
        enabled=enabled_names,
    )
    
    # Verify all enabled plugins are available
    for name in enabled_names:
        if name not in available:
            raise ValueError(f"Plugin '{name}' not found in {plugins_package}")
    
    # Build dependency graph and load order
    load_order = _resolve_dependencies(enabled_names, available)
    
    # Load plugins in order
    loaded = []
    for name in load_order:
        plugin_class = available[name]
        
        # Get plugin configuration (from file config or database)
        plugin_config = plugin_configs.get(name, {})
        
        # Merge with plugin's default configuration
        default_config = {}
        try:
            # Get defaults from the plugin class's config_schema
            schema = plugin_class.config_schema()
            if schema is not None:
                for section in schema:
                    if section and section.fields:
                        for field in section.fields:
                            default_config[field.key] = field.default_value
        except Exception as e:
            logger.debug("plugin_config_schema_error", plugin=name, error=str(e))
        
        # Merge: defaults < file config
        merged_config = {**default_config, **plugin_config}
        
        # Instantiate plugin with merged config
        instance = plugin_class(merged_config)
        
        # Validate configuration using the contract
        errors = instance.validate_plugin_config()
        if errors:
            raise ValueError(
                f"Plugin '{name}' configuration invalid: {', '.join(errors)}"
            )
        
        # Note: Plugin database registration is handled in main.py lifespan
        # after all plugins are loaded, where we have proper async context
        
        # Register and activate
        plugin_registry.register(instance)
        instance.on_activate()
        loaded.append(instance)
        
        logger.info(
            "plugin_loaded",
            name=name,
            version=plugin_class.info().version,
            config_keys=list(merged_config.keys()),
        )
    
    return loaded


def _resolve_dependencies(
    enabled: List[str],
    available: Dict[str, Type[Plugin]],
) -> List[str]:
    """
    Resolve plugin dependencies and return load order.
    
    Uses topological sort to ensure dependencies are loaded first.
    
    Args:
        enabled: List of enabled plugin names.
        available: Dictionary of available plugin classes.
        
    Returns:
        List of plugin names in load order.
        
    Raises:
        ValueError: If a dependency is missing or circular.
    """
    # Build dependency graph
    graph: Dict[str, List[str]] = {}
    
    for name in enabled:
        plugin_class = available[name]
        info = plugin_class.info()
        
        # Check all dependencies are enabled
        for dep in info.dependencies:
            if dep not in enabled:
                raise ValueError(
                    f"Plugin '{name}' requires '{dep}' which is not enabled"
                )
        
        graph[name] = info.dependencies
    
    # Topological sort (Kahn's algorithm)
    in_degree = {name: 0 for name in enabled}
    for name, deps in graph.items():
        for dep in deps:
            if dep in in_degree:
                in_degree[name] += 1
    
    # Start with nodes that have no dependencies
    queue = [name for name, degree in in_degree.items() if degree == 0]
    result = []
    
    while queue:
        node = queue.pop(0)
        result.append(node)
        
        # Reduce in-degree for dependents
        for name, deps in graph.items():
            if node in deps:
                in_degree[name] -= 1
                if in_degree[name] == 0:
                    queue.append(name)
    
    if len(result) != len(enabled):
        # Circular dependency detected
        remaining = set(enabled) - set(result)
        raise ValueError(f"Circular dependency detected in plugins: {remaining}")
    
    return result


def unload_all_plugins() -> None:
    """Unload all registered plugins."""
    for plugin in list(plugin_registry.get_all_plugins()):
        info = plugin.info()
        plugin_registry.unregister(info.name)
    
    logger.info("all_plugins_unloaded")
