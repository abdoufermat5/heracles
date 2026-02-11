"""
Plugin Endpoints
================

Endpoints for plugin management and plugin-provided routes.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, status

from heracles_api.plugins.registry import plugin_registry

router = APIRouter()


@router.get(
    "/plugins",
    summary="List loaded plugins",
    tags=["Plugins"],
)
async def list_plugins():
    """
    List all loaded plugins and their information.
    """
    plugins = plugin_registry.get_plugin_info_list()
    return {
        "plugins": plugins,
        "total": len(plugins),
    }


@router.get(
    "/plugins/{name}",
    summary="Get plugin info",
    tags=["Plugins"],
)
async def get_plugin(name: str):
    """
    Get information about a specific plugin.
    """
    plugin = plugin_registry.get_plugin(name)
    if plugin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{name}' not found",
        )
    
    info = plugin.info()
    return {
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
    }


@router.get(
    "/tabs/{object_type}",
    summary="Get tabs for object type",
    tags=["Plugins"],
)
async def get_tabs_for_object(object_type: str):
    """
    Get all available tabs for an object type (user or group).
    """
    if object_type not in ["user", "group"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="object_type must be 'user' or 'group'",
        )
    
    tabs = plugin_registry.get_tabs_for_object_type(object_type)

    # Resolve plugin name for each tab
    def _plugin_name_for_tab(tab_id: str) -> Optional[str]:
        for plugin in plugin_registry.get_all_plugins():
            for ptab in plugin.tabs():
                if ptab.id == tab_id:
                    return plugin.info().name
        return None

    return {
        "tabs": [
            {
                "id": tab.id,
                "label": tab.label,
                "icon": tab.icon,
                "required": tab.required,
                "pluginName": _plugin_name_for_tab(tab.id),
            }
            for tab in tabs
        ],
        "total": len(tabs),
    }
