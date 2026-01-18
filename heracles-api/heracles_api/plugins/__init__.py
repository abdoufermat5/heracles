"""
Heracles Plugin System
======================

This module provides the plugin infrastructure for Heracles.
Plugins can add tabs to existing objects (users, groups) or
provide entirely new object management capabilities.
"""

from .base import Plugin, PluginInfo, TabDefinition, TabService
from .registry import PluginRegistry
from .loader import discover_plugins, load_enabled_plugins

__all__ = [
    "Plugin",
    "PluginInfo",
    "TabDefinition",
    "TabService",
    "PluginRegistry",
    "discover_plugins",
    "load_enabled_plugins",
]
