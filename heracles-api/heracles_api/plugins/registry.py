"""
Plugin Registry
===============

Manages loaded plugins and provides access to their services.
"""

from typing import Any, Dict, List, Optional, Type

import structlog

from .base import Plugin, PluginInfo, PluginFieldDefinition, PluginTemplateField, TabDefinition, TabService

logger = structlog.get_logger(__name__)


class PluginRegistry:
    """
    Central registry for all loaded plugins.
    
    Provides access to:
    - Plugin instances by name
    - Tabs by object type
    - Services by tab ID
    """
    
    _instance: Optional["PluginRegistry"] = None
    
    def __new__(cls) -> "PluginRegistry":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._plugins: Dict[str, Plugin] = {}
            cls._instance._tabs_by_object_type: Dict[str, List[TabDefinition]] = {}
            cls._instance._services: Dict[str, TabService] = {}
            cls._instance._ldap_service = None
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (for testing)."""
        cls._instance = None
    
    def set_ldap_service(self, ldap_service: Any) -> None:
        """Set the LDAP service for plugin use."""
        self._ldap_service = ldap_service
    
    def register(self, plugin: Plugin) -> None:
        """
        Register a plugin instance.
        
        Args:
            plugin: The plugin instance to register.
        """
        info = plugin.info()
        
        if info.name in self._plugins:
            logger.warning("plugin_already_registered", name=info.name)
            return
        
        self._plugins[info.name] = plugin
        
        # Register tabs
        for tab in plugin.tabs():
            if tab.object_type not in self._tabs_by_object_type:
                self._tabs_by_object_type[tab.object_type] = []
            self._tabs_by_object_type[tab.object_type].append(tab)
            
            # Instantiate and register service
            plugin_config = plugin._config
            service = tab.service_class(self._ldap_service, plugin_config)
            self._services[tab.id] = service
        
        # Also register standalone service if plugin provides service_class()
        # and no tabs registered a service with the plugin name
        if hasattr(plugin, 'service_class') and info.name not in self._services:
            service_cls = plugin.service_class()
            if service_cls is not None:
                plugin_config = plugin._config
                service = service_cls(self._ldap_service, plugin_config)
                self._services[info.name] = service
                logger.debug(
                    "plugin_standalone_service_registered",
                    name=info.name,
                    service_class=service_cls.__name__,
                )
        
        logger.info(
            "plugin_registered",
            name=info.name,
            version=info.version,
            tabs=len(plugin.tabs()),
        )
    
    def unregister(self, name: str) -> None:
        """
        Unregister a plugin.
        
        Args:
            name: Plugin name to unregister.
        """
        if name not in self._plugins:
            return
        
        plugin = self._plugins[name]
        
        # Remove tabs and services
        for tab in plugin.tabs():
            if tab.object_type in self._tabs_by_object_type:
                self._tabs_by_object_type[tab.object_type] = [
                    t for t in self._tabs_by_object_type[tab.object_type]
                    if t.id != tab.id
                ]
            if tab.id in self._services:
                del self._services[tab.id]
        
        plugin.on_deactivate()
        del self._plugins[name]
        
        logger.info("plugin_unregistered", name=name)
    
    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get plugin by name."""
        return self._plugins.get(name)
    
    def get_all_plugins(self) -> List[Plugin]:
        """Get all registered plugins."""
        return list(self._plugins.values())
    
    def get_tabs_for_object_type(self, object_type: str) -> List[TabDefinition]:
        """
        Get all tabs for a given object type.
        
        Args:
            object_type: 'user' or 'group'
            
        Returns:
            List of TabDefinition sorted by priority.
        """
        tabs = self._tabs_by_object_type.get(object_type, [])
        
        # Sort by plugin priority
        def get_priority(tab: TabDefinition) -> int:
            for plugin in self._plugins.values():
                for ptab in plugin.tabs():
                    if ptab.id == tab.id:
                        return plugin.info().priority
            return 50
        
        return sorted(tabs, key=get_priority)
    
    def get_service(self, tab_id: str) -> Optional[TabService]:
        """Get service instance by tab ID."""
        return self._services.get(tab_id)
    
    def get_service_for_plugin(
        self,
        plugin_name: str,
        object_type: str,
    ) -> Optional[TabService]:
        """
        Get service for a plugin's tab on an object type.
        
        Args:
            plugin_name: Plugin name (e.g., 'posix')
            object_type: Object type ('user' or 'group')
            
        Returns:
            TabService instance or None.
        """
        plugin = self._plugins.get(plugin_name)
        if not plugin:
            return None
        
        for tab in plugin.tabs():
            if tab.object_type == object_type:
                return self._services.get(tab.id)
        
        return None
    
    def get_plugin_info_list(self) -> List[Dict[str, Any]]:
        """
        Get info for all plugins.
        
        Returns:
            List of plugin info dictionaries.
        """
        result = []
        for plugin in self._plugins.values():
            info = plugin.info()
            result.append({
                "name": info.name,
                "version": info.version,
                "description": info.description,
                "author": info.author,
                "object_types": info.object_types,
                "object_classes": info.object_classes,
                "dependencies": info.dependencies,
                "priority": info.priority,
                "tabs": [
                    {
                        "id": tab.id,
                        "label": tab.label,
                        "icon": tab.icon,
                        "object_type": tab.object_type,
                    }
                    for tab in plugin.tabs()
                ],
            })
        return result

    # ------------------------------------------------------------------
    # Import / Export / Template aggregation
    # ------------------------------------------------------------------

    def get_import_fields_for_type(
        self, object_type: str
    ) -> List[PluginFieldDefinition]:
        """
        Collect import fields from all active plugins that attach to *object_type*.

        Each field is annotated with ``plugin_name`` so the import system
        can infer which plugin to activate.
        """
        fields: List[PluginFieldDefinition] = []
        seen: set[str] = set()

        for plugin in self._plugins.values():
            info = plugin.info()
            for tab in plugin.tabs():
                if tab.object_type != object_type:
                    continue
                service = self._services.get(tab.id)
                if service is None:
                    continue
                for f in service.get_import_fields():
                    if f.name not in seen:
                        f.plugin_name = info.name
                        fields.append(f)
                        seen.add(f.name)
        return fields

    def get_export_fields_for_type(
        self, object_type: str
    ) -> List[PluginFieldDefinition]:
        """Collect export fields from all active plugins for *object_type*."""
        fields: List[PluginFieldDefinition] = []
        seen: set[str] = set()

        for plugin in self._plugins.values():
            info = plugin.info()
            for tab in plugin.tabs():
                if tab.object_type != object_type:
                    continue
                service = self._services.get(tab.id)
                if service is None:
                    continue
                for f in service.get_export_fields():
                    if f.name not in seen:
                        f.plugin_name = info.name
                        fields.append(f)
                        seen.add(f.name)
        return fields

    def get_template_fields_for_type(
        self, object_type: str
    ) -> Dict[str, Any]:
        """
        Return template-configurable fields grouped by plugin.

        Returns::

            {
              "posix": {
                "label": "Unix Account",
                "object_classes": ["posixAccount", "shadowAccount"],
                "fields": [ PluginTemplateField(...), ... ]
              },
              ...
            }
        """
        result: Dict[str, Any] = {}

        for plugin in self._plugins.values():
            info = plugin.info()
            for tab in plugin.tabs():
                if tab.object_type != object_type:
                    continue
                service = self._services.get(tab.id)
                if service is None:
                    continue
                tmpl_fields = service.get_template_fields()
                if not tmpl_fields:
                    continue
                result[info.name] = {
                    "label": tab.label,
                    "icon": tab.icon,
                    "object_classes": service.OBJECT_CLASSES,
                    "fields": [
                        {
                            "key": f.key,
                            "label": f.label,
                            "fieldType": f.field_type,
                            "defaultValue": f.default_value,
                            "options": f.options,
                            "description": f.description,
                        }
                        for f in tmpl_fields
                    ],
                }
        return result


# Global registry instance
plugin_registry = PluginRegistry()
