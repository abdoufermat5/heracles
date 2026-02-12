"""
Configuration API Endpoints
===========================

API routes for managing application and plugin configuration.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status

from heracles_api.acl import AclGuard
from heracles_api.config import settings
from heracles_api.core.dependencies import get_acl_guard, get_current_user
from heracles_api.schemas.config import (
    ConfigBulkUpdateRequest,
    ConfigCategoryResponse,
    ConfigHistoryResponse,
    ConfigUpdateRequest,
    GlobalConfigResponse,
    PluginConfigResponse,
    PluginConfigUpdateRequest,
    PluginConfigUpdateResponse,
    PluginToggleRequest,
    RdnChangeCheckRequest,
    RdnChangeCheckResponse,
    RdnMigrationRequest,
    RdnMigrationResponse,
    SettingUpdateResponse,
    SettingUpdateWithConfirmation,
)
from heracles_api.services.config import ConfigService, get_config_service

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
    guard: AclGuard = Depends(get_acl_guard),
    config_service: ConfigService = Depends(get_config_svc),
):
    """
    Get all configuration (categories + plugins).

    Requires: config:read
    """
    guard.require(settings.LDAP_BASE_DN, "config:read")
    return await config_service.get_all_config()


@router.get(
    "/categories",
    response_model=list[ConfigCategoryResponse],
    summary="Get configuration categories",
    description="Get all configuration categories with their settings.",
)
async def get_categories(
    current_user=Depends(get_current_user),
    guard: AclGuard = Depends(get_acl_guard),
    config_service: ConfigService = Depends(get_config_svc),
):
    """
    Get all configuration categories.

    Requires: config:read
    """
    guard.require(settings.LDAP_BASE_DN, "config:read")
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
    guard: AclGuard = Depends(get_acl_guard),
    config_service: ConfigService = Depends(get_config_svc),
):
    """
    Get a specific configuration category.

    Requires: config:read
    """
    guard.require(settings.LDAP_BASE_DN, "config:read")
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
    guard: AclGuard = Depends(get_acl_guard),
    config_service: ConfigService = Depends(get_config_svc),
):
    """
    Update a single configuration setting.

    Requires: config:write
    """
    guard.require(settings.LDAP_BASE_DN, "config:write")
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
    guard: AclGuard = Depends(get_acl_guard),
    config_service: ConfigService = Depends(get_config_svc),
):
    """
    Bulk update configuration settings.

    Requires: config:write
    """
    guard.require(settings.LDAP_BASE_DN, "config:write")
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
    response_model=list[PluginConfigResponse],
    summary="Get all plugin configurations",
    description="Get configuration for all registered plugins.",
)
async def get_all_plugin_configs(
    current_user=Depends(get_current_user),
    guard: AclGuard = Depends(get_acl_guard),
    config_service: ConfigService = Depends(get_config_svc),
):
    """
    Get all plugin configurations.

    Requires: config:read
    """
    guard.require(settings.LDAP_BASE_DN, "config:read")
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
    guard: AclGuard = Depends(get_acl_guard),
    config_service: ConfigService = Depends(get_config_svc),
):
    """
    Get a specific plugin's configuration.

    Requires: config:read
    """
    guard.require(settings.LDAP_BASE_DN, "config:read")
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
    response_model=PluginConfigUpdateResponse,
)
async def update_plugin_config(
    plugin_name: str,
    request: PluginConfigUpdateRequest,
    current_user=Depends(get_current_user),
    guard: AclGuard = Depends(get_acl_guard),
    config_service: ConfigService = Depends(get_config_svc),
):
    """
    Update a plugin's configuration.

    For RDN settings (like sudoers_rdn, dns_rdn, systems_rdn), this endpoint
    will check if existing entries would be affected and require confirmation.

    Requires: config:write
    """
    guard.require(settings.LDAP_BASE_DN, "config:write")
    result = await config_service.update_plugin_config_with_migration(
        plugin_name=plugin_name,
        config=request.config,
        changed_by=current_user.user_dn,
        reason=request.reason,
        confirmed=request.confirmed,
        migrate_entries=request.migrate_entries,
    )

    # Check if migration confirmation is required
    if result.get("requires_confirmation"):
        return PluginConfigUpdateResponse(**result)

    if not result.get("success", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": result.get("errors", [])},
        )

    return PluginConfigUpdateResponse(**result)


@router.post(
    "/plugins/{plugin_name}/enable",
    summary="Enable a plugin",
    description="Enable a previously disabled plugin.",
)
async def enable_plugin(
    plugin_name: str,
    request: PluginToggleRequest | None = None,
    current_user=Depends(get_current_user),
    guard: AclGuard = Depends(get_acl_guard),
    config_service: ConfigService = Depends(get_config_svc),
):
    """
    Enable a plugin.

    Requires: config:write
    """
    guard.require(settings.LDAP_BASE_DN, "config:write")
    reason = request.reason if request else None
    success, errors = await config_service.toggle_plugin(
        plugin_name=plugin_name,
        enabled=True,
        changed_by=current_user.user_dn,
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
    request: PluginToggleRequest | None = None,
    current_user=Depends(get_current_user),
    guard: AclGuard = Depends(get_acl_guard),
    config_service: ConfigService = Depends(get_config_svc),
):
    """
    Disable a plugin.

    Requires: config:write
    """
    guard.require(settings.LDAP_BASE_DN, "config:write")
    reason = request.reason if request else None
    success, errors = await config_service.toggle_plugin(
        plugin_name=plugin_name,
        enabled=False,
        changed_by=current_user.user_dn,
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
    category: str | None = Query(None, description="Filter by category"),
    plugin_name: str | None = Query(None, description="Filter by plugin"),
    current_user=Depends(get_current_user),
    guard: AclGuard = Depends(get_acl_guard),
    config_service: ConfigService = Depends(get_config_svc),
):
    """
    Get configuration change history.

    Requires: config:read
    """
    guard.require(settings.LDAP_BASE_DN, "config:read")
    return await config_service.get_history(
        page=page,
        page_size=page_size,
        category=category,
        plugin_name=plugin_name,
    )


# =============================================================================
# RDN Change Validation
# =============================================================================


@router.post(
    "/rdn/check",
    response_model=RdnChangeCheckResponse,
    summary="Check RDN change impact",
    description="Check what entries would be affected by an RDN change before applying it.",
)
async def check_rdn_change(
    request: RdnChangeCheckRequest,
    current_user=Depends(get_current_user),
    config_service: ConfigService = Depends(get_config_svc),
):
    """
    Check the impact of an RDN change.

    This should be called before changing any RDN setting to warn the user
    about affected entries and migration options.
    """
    from heracles_api.services.ldap_migration_service import LdapMigrationService
    from heracles_api.services.ldap_service import get_ldap_service

    try:
        ldap_service = get_ldap_service()
        migration_service = LdapMigrationService(ldap_service, config_service)

        check_result = await migration_service.check_rdn_change(
            old_rdn=request.old_rdn,
            new_rdn=request.new_rdn,
            base_dn=request.base_dn,
            object_class_filter=request.object_class_filter,
        )

        # Determine if confirmation is required
        requires_confirmation = check_result.entries_count > 0

        return RdnChangeCheckResponse(
            old_rdn=check_result.old_rdn,
            new_rdn=check_result.new_rdn,
            base_dn=check_result.base_dn,
            entries_count=check_result.entries_count,
            entries_dns=check_result.entries_dns,
            supports_modrdn=check_result.supports_modrdn,
            recommended_mode=check_result.recommended_mode.value,
            warnings=check_result.warnings,
            requires_confirmation=requires_confirmation,
        )

    except Exception as e:
        logger.error("rdn_check_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check RDN change impact: {str(e)}",
        )


@router.post(
    "/rdn/migrate",
    response_model=RdnMigrationResponse,
    summary="Migrate entries after RDN change",
    description="Migrate entries from old RDN location to new location.",
)
async def migrate_rdn_entries(
    request: RdnMigrationRequest,
    current_user=Depends(get_current_user),
    config_service: ConfigService = Depends(get_config_svc),
):
    """
    Migrate entries after an RDN change.

    This should only be called after the user has confirmed the migration.
    """
    from heracles_api.services.ldap_migration_service import LdapMigrationService, MigrationMode
    from heracles_api.services.ldap_service import get_ldap_service

    # Require confirmation
    if not request.confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Migration must be confirmed. Set 'confirmed: true' after reviewing warnings.",
        )

    try:
        ldap_service = get_ldap_service()
        migration_service = LdapMigrationService(ldap_service, config_service)

        # Parse mode
        try:
            mode = MigrationMode(request.mode)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid migration mode: {request.mode}. Use 'modrdn', 'copy_delete', or 'leave_orphaned'.",
            )

        result = await migration_service.migrate_entries(
            old_rdn=request.old_rdn,
            new_rdn=request.new_rdn,
            base_dn=request.base_dn,
            mode=mode,
            object_class_filter=request.object_class_filter,
        )

        # Log the migration
        logger.info(
            "rdn_migration_completed",
            old_rdn=request.old_rdn,
            new_rdn=request.new_rdn,
            mode=mode.value,
            migrated=result.entries_migrated,
            failed=result.entries_failed,
            user=current_user.user_dn,
        )

        return RdnMigrationResponse(
            success=result.success,
            mode=result.mode.value,
            entries_migrated=result.entries_migrated,
            entries_failed=result.entries_failed,
            failed_entries=result.failed_entries,
            warnings=result.warnings,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("rdn_migration_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration failed: {str(e)}",
        )


@router.patch(
    "/settings/{category}/{key}/with-migration",
    response_model=SettingUpdateResponse,
    summary="Update setting with RDN migration support",
    description="Update a setting that may be an RDN, with automatic migration support.",
)
async def update_setting_with_migration(
    category: str,
    key: str,
    request: SettingUpdateWithConfirmation,
    current_user=Depends(get_current_user),
    config_service: ConfigService = Depends(get_config_svc),
):
    """
    Update a setting with RDN migration support.

    For RDN settings (like user_rdn, group_rdn, etc.), this endpoint:
    1. Checks if entries exist in the old location
    2. If entries exist and not confirmed, returns warning with migration check
    3. If confirmed and migrate_entries is true, performs migration
    4. Updates the setting value
    """
    from heracles_api.services.ldap_migration_service import LdapMigrationService, MigrationMode
    from heracles_api.services.ldap_service import get_ldap_service

    # List of RDN settings that may require migration
    rdn_settings = {
        ("ldap", "user_rdn"): None,
        ("ldap", "group_rdn"): None,
        ("dns", "dns_rdn"): "dNSZone",
        ("dhcp", "dhcp_rdn"): "dhcpService",
        ("sudo", "sudoers_rdn"): "sudoRole",
        ("systems", "systems_rdn"): "device",
    }

    setting_key = (category, key)
    is_rdn_setting = setting_key in rdn_settings or key.endswith("_rdn")

    migration_check = None
    migration_result = None

    if is_rdn_setting:
        # Get current value
        current_value = await config_service.get_setting(category, key)
        new_value = request.value

        # Only check if value is actually changing
        if current_value != new_value and current_value is not None:
            try:
                ldap_service = get_ldap_service()
                migration_service = LdapMigrationService(ldap_service, config_service)

                object_class_filter = rdn_settings.get(setting_key)

                check_result = await migration_service.check_rdn_change(
                    old_rdn=str(current_value),
                    new_rdn=str(new_value),
                    object_class_filter=object_class_filter,
                )

                migration_check = RdnChangeCheckResponse(
                    old_rdn=check_result.old_rdn,
                    new_rdn=check_result.new_rdn,
                    base_dn=check_result.base_dn,
                    entries_count=check_result.entries_count,
                    entries_dns=check_result.entries_dns,
                    supports_modrdn=check_result.supports_modrdn,
                    recommended_mode=check_result.recommended_mode.value,
                    warnings=check_result.warnings,
                    requires_confirmation=check_result.entries_count > 0,
                )

                # If entries exist and not confirmed, return warning
                if check_result.entries_count > 0 and not request.confirmed:
                    return SettingUpdateResponse(
                        success=False,
                        message="RDN change affects existing entries. Please confirm to proceed.",
                        requires_confirmation=True,
                        migration_check=migration_check,
                    )

                # If confirmed and should migrate, perform migration
                if check_result.entries_count > 0 and request.confirmed and request.migrate_entries:
                    mode = MigrationMode.MODRDN if check_result.supports_modrdn else MigrationMode.COPY_DELETE

                    result = await migration_service.migrate_entries(
                        old_rdn=str(current_value),
                        new_rdn=str(new_value),
                        object_class_filter=object_class_filter,
                        mode=mode,
                    )

                    migration_result = RdnMigrationResponse(
                        success=result.success,
                        mode=result.mode.value,
                        entries_migrated=result.entries_migrated,
                        entries_failed=result.entries_failed,
                        failed_entries=result.failed_entries,
                        warnings=result.warnings,
                    )

                    # If migration failed, don't update the setting
                    if not result.success:
                        return SettingUpdateResponse(
                            success=False,
                            message=f"Migration failed: {result.entries_failed} entries could not be migrated.",
                            requires_confirmation=False,
                            migration_check=migration_check,
                            migration_result=migration_result,
                        )

            except Exception as e:
                logger.error("rdn_check_error", error=str(e))
                # Continue with update but log the error

    # Update the setting
    success, errors = await config_service.update_setting(
        category=category,
        key=key,
        value=request.value,
        changed_by=current_user.user_dn,
        reason=request.reason,
    )

    if not success:
        return SettingUpdateResponse(
            success=False,
            message=f"Failed to update setting: {', '.join(errors)}",
            requires_confirmation=False,
            migration_check=migration_check,
            migration_result=migration_result,
        )

    return SettingUpdateResponse(
        success=True,
        message="Setting updated successfully",
        requires_confirmation=False,
        migration_check=migration_check,
        migration_result=migration_result,
    )
