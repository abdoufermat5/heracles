"""
Configuration API Endpoints
===========================

API routes for managing application and plugin configuration.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
import structlog

from heracles_api.schemas.config import (
    ConfigBulkUpdateRequest,
    ConfigCategoryResponse,
    ConfigHistoryResponse,
    ConfigUpdateRequest,
    GlobalConfigResponse,
    PluginConfigResponse,
    PluginConfigUpdateRequest,
    PluginToggleRequest,
)
from heracles_api.services.config_service import get_config_service, ConfigService
from heracles_api.core.dependencies import get_current_user

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/config", tags=["Configuration"])


# =============================================================================
# Dependencies
# =============================================================================

async def get_config_svc() -> ConfigService:
    """Get the config service instance."""
    try:
        return get_config_service()
    except RuntimeError as e:
        logger.error("config_service_not_available", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Configuration service not available: {str(e)}",
        )


# =============================================================================
# Global Configuration
# =============================================================================

@router.get(
    "",
    response_model=GlobalConfigResponse,
    summary="Get all configuration",
    description="Get all configuration categories and plugin configurations.",
)
async def get_all_config(
    current_user=Depends(get_current_user),
    config_service: ConfigService = Depends(get_config_svc),
):
    """Get all configuration (categories + plugins)."""
    return await config_service.get_all_config()


@router.get(
    "/categories",
    response_model=List[ConfigCategoryResponse],
    summary="Get configuration categories",
    description="Get all configuration categories with their settings.",
)
async def get_categories(
    current_user=Depends(get_current_user),
    config_service: ConfigService = Depends(get_config_svc),
):
    """Get all configuration categories."""
    return await config_service.get_categories()


@router.get(
    "/categories/{category_name}",
    response_model=ConfigCategoryResponse,
    summary="Get a configuration category",
    description="Get a specific configuration category with its settings.",
)
async def get_category(
    category_name: str,
    current_user=Depends(get_current_user),
    config_service: ConfigService = Depends(get_config_svc),
):
    """Get a specific configuration category."""
    categories = await config_service.get_categories()
    for cat in categories:
        if cat.name == category_name:
            return cat
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Category '{category_name}' not found",
    )


@router.patch(
    "/settings/{category}/{key}",
    summary="Update a configuration setting",
    description="Update a single configuration setting value.",
)
async def update_setting(
    category: str,
    key: str,
    request: ConfigUpdateRequest,
    current_user=Depends(get_current_user),
    config_service: ConfigService = Depends(get_config_svc),
):
    """Update a single configuration setting."""
    success, errors = await config_service.update_setting(
        category=category,
        key=key,
        value=request.value,
        changed_by=current_user.user_dn,
        reason=request.reason,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": errors},
        )
    
    return {"message": "Setting updated successfully"}


@router.put(
    "/settings",
    summary="Bulk update settings",
    description="Update multiple configuration settings at once.",
)
async def bulk_update_settings(
    request: ConfigBulkUpdateRequest,
    current_user=Depends(get_current_user),
    config_service: ConfigService = Depends(get_config_svc),
):
    """Bulk update configuration settings."""
    updated, errors = await config_service.bulk_update_settings(
        settings=request.settings,
        changed_by=current_user.user_dn,
        reason=request.reason,
    )
    
    result = {"updated": updated}
    if errors:
        result["errors"] = errors
    
    return result


# =============================================================================
# Plugin Configuration
# =============================================================================

@router.get(
    "/plugins",
    response_model=List[PluginConfigResponse],
    summary="Get all plugin configurations",
    description="Get configuration for all registered plugins.",
)
async def get_all_plugin_configs(
    current_user=Depends(get_current_user),
    config_service: ConfigService = Depends(get_config_svc),
):
    """Get all plugin configurations."""
    return await config_service.get_all_plugin_configs()


@router.get(
    "/plugins/{plugin_name}",
    response_model=PluginConfigResponse,
    summary="Get plugin configuration",
    description="Get configuration for a specific plugin.",
)
async def get_plugin_config(
    plugin_name: str,
    current_user=Depends(get_current_user),
    config_service: ConfigService = Depends(get_config_svc),
):
    """Get a specific plugin's configuration."""
    config = await config_service.get_plugin_config(plugin_name)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{plugin_name}' not found",
        )
    return config


@router.patch(
    "/plugins/{plugin_name}",
    summary="Update plugin configuration",
    description="Update configuration for a specific plugin.",
)
async def update_plugin_config(
    plugin_name: str,
    request: PluginConfigUpdateRequest,
    current_user=Depends(get_current_user),
    config_service: ConfigService = Depends(get_config_svc),
):
    """Update a plugin's configuration."""
    success, errors = await config_service.update_plugin_config(
        plugin_name=plugin_name,
        config=request.config,
        changed_by=current_user.dn,
        reason=request.reason,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": errors},
        )
    
    return {"message": f"Plugin '{plugin_name}' configuration updated successfully"}


@router.post(
    "/plugins/{plugin_name}/enable",
    summary="Enable a plugin",
    description="Enable a previously disabled plugin.",
)
async def enable_plugin(
    plugin_name: str,
    request: Optional[PluginToggleRequest] = None,
    current_user=Depends(get_current_user),
    config_service: ConfigService = Depends(get_config_svc),
):
    """Enable a plugin."""
    reason = request.reason if request else None
    success, errors = await config_service.toggle_plugin(
        plugin_name=plugin_name,
        enabled=True,
        changed_by=current_user.dn,
        reason=reason,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": errors},
        )
    
    return {"message": f"Plugin '{plugin_name}' enabled successfully"}


@router.post(
    "/plugins/{plugin_name}/disable",
    summary="Disable a plugin",
    description="Disable an active plugin.",
)
async def disable_plugin(
    plugin_name: str,
    request: Optional[PluginToggleRequest] = None,
    current_user=Depends(get_current_user),
    config_service: ConfigService = Depends(get_config_svc),
):
    """Disable a plugin."""
    reason = request.reason if request else None
    success, errors = await config_service.toggle_plugin(
        plugin_name=plugin_name,
        enabled=False,
        changed_by=current_user.dn,
        reason=reason,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": errors},
        )
    
    return {"message": f"Plugin '{plugin_name}' disabled successfully"}


# =============================================================================
# Configuration History
# =============================================================================

@router.get(
    "/history",
    response_model=ConfigHistoryResponse,
    summary="Get configuration change history",
    description="Get audit trail of configuration changes.",
)
async def get_config_history(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    plugin_name: Optional[str] = Query(None, description="Filter by plugin"),
    current_user=Depends(get_current_user),
    config_service: ConfigService = Depends(get_config_svc),
):
    """Get configuration change history."""
    return await config_service.get_history(
        page=page,
        page_size=page_size,
        category=category,
        plugin_name=plugin_name,
    )
