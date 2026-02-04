"""
Configuration Schemas
=====================

Pydantic models for configuration API requests and responses.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ConfigFieldType(str, Enum):
    """Types of configuration fields."""
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    FLOAT = "float"
    LIST = "list"
    SELECT = "select"
    MULTISELECT = "multiselect"
    PASSWORD = "password"
    PATH = "path"
    URL = "url"
    EMAIL = "email"
    JSON = "json"


class ConfigFieldOption(BaseModel):
    """Option for select/multiselect fields."""
    value: Any
    label: str
    description: Optional[str] = None
    
    class Config:
        populate_by_name = True


class ConfigFieldValidation(BaseModel):
    """Validation rules for a configuration field."""
    required: bool = True
    min_value: Optional[Union[int, float]] = Field(None, alias="minValue")
    max_value: Optional[Union[int, float]] = Field(None, alias="maxValue")
    min_length: Optional[int] = Field(None, alias="minLength")
    max_length: Optional[int] = Field(None, alias="maxLength")
    pattern: Optional[str] = None
    
    class Config:
        populate_by_name = True


class ConfigFieldResponse(BaseModel):
    """A configuration field definition."""
    key: str
    label: str
    field_type: ConfigFieldType = Field(..., alias="fieldType")
    value: Any
    default_value: Any = Field(..., alias="defaultValue")
    description: Optional[str] = None
    validation: Optional[ConfigFieldValidation] = None
    options: Optional[List[ConfigFieldOption]] = None
    requires_restart: bool = Field(False, alias="requiresRestart")
    sensitive: bool = False
    group: Optional[str] = None
    depends_on: Optional[str] = Field(None, alias="dependsOn")
    depends_on_value: Optional[Any] = Field(None, alias="dependsOnValue")
    
    class Config:
        populate_by_name = True


class ConfigSectionResponse(BaseModel):
    """A section of configuration settings."""
    id: str
    label: str
    description: Optional[str] = None
    icon: Optional[str] = None
    fields: List[ConfigFieldResponse] = []
    order: int = 50
    
    class Config:
        populate_by_name = True


class ConfigCategoryResponse(BaseModel):
    """A category of configuration (e.g., 'general', 'ldap')."""
    name: str
    label: str
    description: Optional[str] = None
    icon: Optional[str] = None
    sections: List[ConfigSectionResponse] = []
    settings: List[ConfigFieldResponse] = []  # Flat list of all settings for easy access
    display_order: int = Field(0, alias="displayOrder")
    
    class Config:
        populate_by_name = True


class PluginConfigResponse(BaseModel):
    """Plugin configuration response."""
    name: str
    enabled: bool
    version: str
    description: Optional[str] = None
    sections: List[ConfigSectionResponse] = []
    config: Dict[str, Any] = {}
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")
    updated_by: Optional[str] = Field(None, alias="updatedBy")
    
    class Config:
        populate_by_name = True


class ConfigUpdateRequest(BaseModel):
    """Request to update a single configuration value."""
    value: Any
    reason: Optional[str] = None
    
    class Config:
        populate_by_name = True


class ConfigBulkUpdateRequest(BaseModel):
    """Request to update multiple configuration values."""
    settings: Dict[str, Any]
    reason: Optional[str] = None
    
    class Config:
        populate_by_name = True


class PluginConfigUpdateRequest(BaseModel):
    """Request to update plugin configuration."""
    config: Dict[str, Any]
    reason: Optional[str] = None
    confirmed: bool = False  # User confirms migration if RDN setting changes
    migrate_entries: bool = True  # Whether to migrate entries when RDN changes
    
    class Config:
        populate_by_name = True


class PluginToggleRequest(BaseModel):
    """Request to enable/disable a plugin."""
    enabled: bool
    reason: Optional[str] = None
    
    class Config:
        populate_by_name = True


class ConfigHistoryEntry(BaseModel):
    """A configuration change history entry."""
    id: str
    category: Optional[str] = None
    plugin_name: Optional[str] = Field(None, alias="pluginName")
    setting_key: Optional[str] = Field(None, alias="settingKey")
    old_value: Optional[Any] = Field(None, alias="oldValue")
    new_value: Any = Field(..., alias="newValue")
    changed_by: str = Field(..., alias="changedBy")
    changed_at: datetime = Field(..., alias="changedAt")
    reason: Optional[str] = None
    
    class Config:
        populate_by_name = True


class ConfigHistoryResponse(BaseModel):
    """Paginated configuration history response."""
    items: List[ConfigHistoryEntry]
    total: int
    page: int
    page_size: int = Field(..., alias="pageSize")
    
    class Config:
        populate_by_name = True


class GlobalConfigResponse(BaseModel):
    """Full configuration response with all categories and plugins."""
    categories: List[ConfigCategoryResponse]
    plugins: List[PluginConfigResponse]
    
    class Config:
        populate_by_name = True


# =============================================================================
# Global Configuration Settings
# =============================================================================

class GeneralSettings(BaseModel):
    """General application settings."""
    language: str = "en"
    timezone: str = "UTC"
    date_format: str = Field("YYYY-MM-DD", alias="dateFormat")
    time_format: str = Field("HH:mm:ss", alias="timeFormat")
    items_per_page: int = Field(25, alias="itemsPerPage")
    theme: str = "system"  # light, dark, system
    
    class Config:
        populate_by_name = True


class LdapSettings(BaseModel):
    """LDAP connection settings (read-only info + configurable RDNs)."""
    # Read-only (from environment)
    uri: Optional[str] = None
    base_dn: Optional[str] = Field(None, alias="baseDn")
    
    # Configurable RDNs
    user_rdn: str = Field("ou=people", alias="userRdn")
    group_rdn: str = Field("ou=groups", alias="groupRdn")
    role_rdn: str = Field("ou=roles", alias="roleRdn")
    system_rdn: str = Field("ou=systems", alias="systemRdn")
    dns_rdn: str = Field("ou=dns", alias="dnsRdn")
    dhcp_rdn: str = Field("ou=dhcp", alias="dhcpRdn")
    sudo_rdn: str = Field("ou=sudoers", alias="sudoRdn")
    
    # Limits
    size_limit: int = Field(1000, alias="sizeLimit")
    time_limit: int = Field(30, alias="timeLimit")
    
    class Config:
        populate_by_name = True


class SecuritySettings(BaseModel):
    """Security settings."""
    force_https: bool = Field(False, alias="forceHttps")
    csrf_protection: bool = Field(True, alias="csrfProtection")
    rate_limiting_enabled: bool = Field(True, alias="rateLimitingEnabled")
    rate_limit_requests: int = Field(100, alias="rateLimitRequests")
    rate_limit_window: int = Field(60, alias="rateLimitWindow")  # seconds
    
    class Config:
        populate_by_name = True


class PasswordPolicySettings(BaseModel):
    """Password policy settings."""
    min_length: int = Field(8, alias="minLength")
    require_uppercase: bool = Field(True, alias="requireUppercase")
    require_lowercase: bool = Field(True, alias="requireLowercase")
    require_numbers: bool = Field(True, alias="requireNumbers")
    require_special: bool = Field(False, alias="requireSpecial")
    default_hash_method: str = Field("ssha", alias="defaultHashMethod")
    expiration_days: int = Field(0, alias="expirationDays")  # 0 = never expires
    warning_days: int = Field(14, alias="warningDays")
    
    class Config:
        populate_by_name = True


class SessionSettings(BaseModel):
    """Session management settings."""
    session_timeout: int = Field(3600, alias="sessionTimeout")  # seconds
    max_concurrent_sessions: int = Field(5, alias="maxConcurrentSessions")  # 0 = unlimited
    remember_me_duration: int = Field(604800, alias="rememberMeDuration")  # 7 days
    idle_timeout: int = Field(1800, alias="idleTimeout")  # 30 minutes
    
    class Config:
        populate_by_name = True


class AuditSettings(BaseModel):
    """Audit and logging settings."""
    enable_audit_log: bool = Field(True, alias="enableAuditLog")
    log_level: str = Field("INFO", alias="logLevel")
    retention_days: int = Field(90, alias="retentionDays")
    log_user_actions: bool = Field(True, alias="logUserActions")
    log_system_events: bool = Field(True, alias="logSystemEvents")
    
    class Config:
        populate_by_name = True


class SnapshotSettings(BaseModel):
    """Snapshot (backup) settings."""
    enable_snapshots: bool = Field(False, alias="enableSnapshots")
    enable_auto_snapshots: bool = Field(False, alias="enableAutoSnapshots")
    snapshot_retention_days: int = Field(30, alias="snapshotRetentionDays")
    max_snapshots_per_object: int = Field(10, alias="maxSnapshotsPerObject")
    
    class Config:
        populate_by_name = True


# =============================================================================
# RDN Change Validation
# =============================================================================

class RdnChangeCheckRequest(BaseModel):
    """Request to check the impact of an RDN change."""
    old_rdn: str = Field(..., alias="oldRdn", description="Current RDN value")
    new_rdn: str = Field(..., alias="newRdn", description="New RDN value")
    base_dn: Optional[str] = Field(None, alias="baseDn", description="Base DN (optional)")
    object_class_filter: Optional[str] = Field(
        None, 
        alias="objectClassFilter", 
        description="Filter for specific objectClass"
    )
    
    class Config:
        populate_by_name = True


class RdnChangeCheckResponse(BaseModel):
    """Response for RDN change impact check."""
    old_rdn: str = Field(..., alias="oldRdn")
    new_rdn: str = Field(..., alias="newRdn")
    base_dn: str = Field(..., alias="baseDn")
    entries_count: int = Field(..., alias="entriesCount", description="Number of entries affected")
    entries_dns: List[str] = Field(
        default_factory=list, 
        alias="entriesDns", 
        description="Sample of affected entry DNs"
    )
    supports_modrdn: bool = Field(..., alias="supportsModrdn", description="Whether modRDN is supported")
    recommended_mode: str = Field(..., alias="recommendedMode", description="Recommended migration mode")
    warnings: List[str] = Field(default_factory=list, description="Warnings about the change")
    requires_confirmation: bool = Field(
        ..., 
        alias="requiresConfirmation", 
        description="Whether confirmation is required"
    )
    
    class Config:
        populate_by_name = True


class RdnMigrationRequest(BaseModel):
    """Request to migrate entries after RDN change."""
    old_rdn: str = Field(..., alias="oldRdn")
    new_rdn: str = Field(..., alias="newRdn")
    base_dn: Optional[str] = Field(None, alias="baseDn")
    mode: str = Field(
        "modrdn", 
        description="Migration mode: 'modrdn', 'copy_delete', or 'leave_orphaned'"
    )
    object_class_filter: Optional[str] = Field(None, alias="objectClassFilter")
    confirmed: bool = Field(
        False, 
        description="User has confirmed the migration after seeing warnings"
    )
    
    class Config:
        populate_by_name = True


class RdnMigrationResponse(BaseModel):
    """Response for RDN migration operation."""
    success: bool
    mode: str = Field(..., description="Migration mode used")
    entries_migrated: int = Field(..., alias="entriesMigrated")
    entries_failed: int = Field(..., alias="entriesFailed")
    failed_entries: List[Dict[str, str]] = Field(
        default_factory=list, 
        alias="failedEntries",
        description="List of {dn, error} for failed entries"
    )
    warnings: List[str] = Field(default_factory=list)
    
    class Config:
        populate_by_name = True


class SettingUpdateWithConfirmation(BaseModel):
    """Setting update request that may require confirmation for RDN changes."""
    value: Any
    reason: Optional[str] = None
    confirmed: bool = Field(
        False, 
        description="User has confirmed the change after seeing warnings"
    )
    migrate_entries: bool = Field(
        True, 
        alias="migrateEntries",
        description="Whether to migrate existing entries (for RDN changes)"
    )
    
    class Config:
        populate_by_name = True


class SettingUpdateResponse(BaseModel):
    """Response for setting update, possibly with migration info."""
    success: bool
    message: str
    requires_confirmation: bool = Field(False, alias="requiresConfirmation")
    migration_check: Optional[RdnChangeCheckResponse] = Field(None, alias="migrationCheck")
    migration_result: Optional[RdnMigrationResponse] = Field(None, alias="migrationResult")
    
    class Config:
        populate_by_name = True


class PluginMigrationResult(BaseModel):
    """Result of a single RDN migration."""
    key: str
    entries_migrated: int = Field(alias="entriesMigrated")
    entries_failed: int = Field(alias="entriesFailed")
    mode: str
    
    class Config:
        populate_by_name = True


class PluginConfigUpdateResponse(BaseModel):
    """Response for plugin config update, possibly with migration info."""
    success: bool = True
    message: Optional[str] = None
    errors: Optional[List[str]] = None
    requires_confirmation: bool = Field(False, alias="requiresConfirmation")
    migration_check: Optional[RdnChangeCheckResponse] = Field(None, alias="migrationCheck")
    migrations: Optional[List[PluginMigrationResult]] = None
    
    class Config:
        populate_by_name = True
