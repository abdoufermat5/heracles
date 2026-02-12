"""
Plugin Base Classes
===================

Defines the base classes and interfaces for Heracles plugins.
"""

import inspect
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel

# =============================================================================
# Configuration Types
# =============================================================================


class ConfigFieldType(StrEnum):
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


@dataclass
class ConfigFieldOption:
    """Option for select/multiselect fields."""

    value: Any
    label: str
    description: str | None = None


@dataclass
class ConfigFieldValidation:
    """Validation rules for a configuration field."""

    required: bool = True
    min_value: int | float | None = None
    max_value: int | float | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None  # Regex pattern
    custom_validator: Callable[[Any], list[str]] | None = None


@dataclass
class ConfigField:
    """
    Definition of a configuration field.

    Used by plugins to declare their configuration schema.
    """

    key: str
    """Unique key for this field (e.g., 'uid_min')."""

    label: str
    """Human-readable label."""

    field_type: ConfigFieldType
    """Type of field."""

    default_value: Any
    """Default value if not configured."""

    description: str | None = None
    """Help text for UI."""

    validation: ConfigFieldValidation | None = None
    """Validation rules."""

    options: list[ConfigFieldOption] | None = None
    """Options for select/multiselect fields."""

    required: bool = True
    """Whether this field is required."""

    requires_restart: bool = False
    """Whether changes require service restart."""

    sensitive: bool = False
    """Whether this is sensitive data (e.g., passwords)."""

    group: str | None = None
    """Group name for UI organization."""

    depends_on: str | None = None
    """Key of field this depends on (for conditional display)."""

    depends_on_value: Any | None = None
    """Value the dependency must have for this field to show."""


@dataclass
class ConfigSection:
    """
    A section of configuration fields for UI organization.
    """

    id: str
    """Unique identifier for this section."""

    label: str
    """Human-readable section title."""

    description: str | None = None
    """Section description."""

    icon: str | None = None
    """Lucide icon name."""

    fields: list[ConfigField] = field(default_factory=list)
    """Fields in this section."""

    order: int = 50
    """Display order (lower = first)."""


class PluginConfigContract(ABC):
    """
    Contract for plugin configuration.

    Plugins must implement this contract to participate in the
    centralized configuration system. This provides:

    1. Schema declaration: What config fields exist
    2. Default values: Sane defaults for each field
    3. Validation: Both schema and business rule validation
    4. UI hints: How to render config in the settings UI
    5. Hot reload: Handle config changes at runtime

    Example implementation:

        class MyPlugin(Plugin):
            @staticmethod
            def config_schema() -> List[ConfigSection]:
                return [
                    ConfigSection(
                        id="general",
                        label="General Settings",
                        fields=[
                            ConfigField(
                                key="max_items",
                                label="Maximum Items",
                                field_type=ConfigFieldType.INTEGER,
                                default_value=100,
                                validation=ConfigFieldValidation(min_value=1, max_value=10000),
                            ),
                        ],
                    ),
                ]
    """

    @staticmethod
    def config_schema() -> list[ConfigSection]:
        """
        Declare the configuration schema for this plugin.

        Returns:
            List of ConfigSection objects defining all config fields.
            Return empty list if plugin has no configuration.
        """
        return []

    @staticmethod
    def default_config() -> dict[str, Any]:
        """
        Return default configuration values.

        This is derived from config_schema() by default but can be
        overridden for complex initialization logic.

        Returns:
            Dictionary of {key: default_value} for all config fields.
        """
        defaults = {}
        for section in PluginConfigContract.config_schema():
            for config_field in section.fields:
                defaults[config_field.key] = config_field.default_value
        return defaults

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        """
        Validate plugin configuration.

        Called when configuration is updated. Performs both:
        1. Schema validation (types, ranges, patterns)
        2. Business rule validation (cross-field dependencies)

        Args:
            config: Configuration dictionary to validate.

        Returns:
            List of error messages (empty if valid).
        """
        errors = []
        schema = self.config_schema()

        for section in schema:
            for field_def in section.fields:
                value = config.get(field_def.key)
                field_errors = self._validate_field(field_def, value)
                errors.extend(field_errors)

        # Call custom validation hook
        custom_errors = self.validate_config_business_rules(config)
        if custom_errors:
            if isinstance(custom_errors, str):
                errors.append(custom_errors)
            else:
                errors.extend(custom_errors)

        return errors

    def validate_config_business_rules(self, config: dict[str, Any]) -> list[str]:
        """
        Override this for custom business rule validation.

        Called after schema validation passes. Use for cross-field
        validation or external checks.

        Args:
            config: Configuration dictionary.

        Returns:
            List of error messages.
        """
        return []

    def _validate_field(self, field_def: ConfigField, value: Any) -> list[str]:
        """Validate a single field against its definition."""
        errors = []
        validation = field_def.validation or ConfigFieldValidation()

        # Required check - validation.required overrides field_def.required if explicitly set False
        # This allows plugins to mark fields as optional even when field-level required=True
        is_required = field_def.required
        if validation.required is False:
            is_required = False

        if is_required and value is None:
            errors.append(f"{field_def.label}: This field is required")
            return errors

        if value is None:
            return errors  # Optional field with no value

        # Type validation
        type_errors = self._validate_type(field_def, value)
        if type_errors:
            errors.extend(type_errors)
            return errors  # Skip further validation if type is wrong

        # Range validation for numbers
        if field_def.field_type in (ConfigFieldType.INTEGER, ConfigFieldType.FLOAT):
            if validation.min_value is not None and value < validation.min_value:
                errors.append(f"{field_def.label}: Must be at least {validation.min_value}")
            if validation.max_value is not None and value > validation.max_value:
                errors.append(f"{field_def.label}: Must be at most {validation.max_value}")

        # Length validation for strings
        if field_def.field_type == ConfigFieldType.STRING:
            if validation.min_length is not None and len(str(value)) < validation.min_length:
                errors.append(f"{field_def.label}: Must be at least {validation.min_length} characters")
            if validation.max_length is not None and len(str(value)) > validation.max_length:
                errors.append(f"{field_def.label}: Must be at most {validation.max_length} characters")

        # Pattern validation
        if validation.pattern:
            import re

            if not re.match(validation.pattern, str(value)):
                errors.append(f"{field_def.label}: Invalid format")

        # Custom validator
        if validation.custom_validator:
            custom_errors = validation.custom_validator(value)
            errors.extend(custom_errors)

        # Options validation for select fields
        if field_def.options and field_def.field_type == ConfigFieldType.SELECT:
            valid_values = [opt.value for opt in field_def.options]
            if value not in valid_values:
                errors.append(f"{field_def.label}: Invalid selection")

        return errors

    def _validate_type(self, field_def: ConfigField, value: Any) -> list[str]:
        """Validate value type matches field type."""
        errors = []

        type_checks = {
            ConfigFieldType.STRING: lambda v: isinstance(v, str),
            ConfigFieldType.INTEGER: lambda v: isinstance(v, int) and not isinstance(v, bool),
            ConfigFieldType.BOOLEAN: lambda v: isinstance(v, bool),
            ConfigFieldType.FLOAT: lambda v: isinstance(v, int | float) and not isinstance(v, bool),
            ConfigFieldType.LIST: lambda v: isinstance(v, list),
            ConfigFieldType.SELECT: lambda v: True,  # Any type for select
            ConfigFieldType.MULTISELECT: lambda v: isinstance(v, list),
            ConfigFieldType.PASSWORD: lambda v: isinstance(v, str),
            ConfigFieldType.PATH: lambda v: isinstance(v, str),
            ConfigFieldType.URL: lambda v: isinstance(v, str),
            ConfigFieldType.EMAIL: lambda v: isinstance(v, str),
            ConfigFieldType.JSON: lambda v: isinstance(v, dict | list),
        }

        checker = type_checks.get(field_def.field_type, lambda v: True)
        if not checker(value):
            expected = field_def.field_type.value
            actual = type(value).__name__
            errors.append(f"{field_def.label}: Expected {expected}, got {actual}")

        return errors

    def on_config_change(
        self,
        old_config: dict[str, Any],
        new_config: dict[str, Any],
        changed_keys: list[str],
    ) -> None:
        """
        Called when configuration changes at runtime.

        Use this to react to config changes without restart.
        For example: update internal caches, reconnect services, etc.

        Args:
            old_config: Previous configuration values.
            new_config: New configuration values.
            changed_keys: List of keys that changed.
        """
        pass

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value with global defaults and plugin override.

        Resolution order:
        1. Plugin-specific config (from _config)
        2. Global default (from default_config)
        3. Provided default parameter

        Args:
            key: Configuration key.
            default: Fallback if not found anywhere.

        Returns:
            Configuration value.
        """
        # Check plugin config first
        if hasattr(self, "_config") and key in self._config:
            return self._config[key]

        # Check default config
        defaults = self.default_config()
        if key in defaults:
            return defaults[key]

        return default


@dataclass
class PluginInfo:
    """Metadata about a plugin."""

    name: str
    """Unique identifier for the plugin."""

    version: str
    """Plugin version (semver format)."""

    description: str
    """Human-readable description."""

    author: str = "Heracles Team"
    """Plugin author."""

    object_types: list[str] = field(default_factory=list)
    """Object types this plugin attaches to (e.g., ['user', 'group'])."""

    object_classes: list[str] = field(default_factory=list)
    """LDAP objectClasses managed by this plugin."""

    dependencies: list[str] = field(default_factory=list)
    """Other plugins required by this one."""

    optional_dependencies: list[str] = field(default_factory=list)
    """Optional plugins that enhance this one's functionality."""

    required_config: list[str] = field(default_factory=list)
    """Configuration keys required by this plugin."""

    priority: int = 50
    """Display priority (lower = displayed first)."""

    minimum_api_version: str | None = None
    """Minimum heracles-api version required (semver). E.g., '0.8.0'."""


@dataclass
class PluginFieldDefinition:
    """Describes a single LDAP attribute contributed by a plugin.

    Used by the import/export system to dynamically discover
    fields beyond the core user/group schema.
    """

    name: str
    """LDAP attribute name (e.g. 'uidNumber')."""

    label: str
    """Human-readable label for the UI."""

    required: bool = False
    """Whether this field is required when the plugin is activated."""

    description: str | None = None
    """Short help text."""

    plugin_name: str | None = None
    """Owning plugin name (set automatically by the registry)."""


@dataclass
class PluginTemplateField:
    """Describes a template-configurable default for a plugin.

    When a template declares ``plugin_activations: {"posix": {"loginShell": "/bin/bash"}}``,
    the keys correspond to :attr:`key` of these fields.
    """

    key: str
    """Configuration key (maps to plugin activate-data field)."""

    label: str
    """Human-readable label."""

    field_type: str = "string"
    """UI hint: string | integer | boolean | select."""

    default_value: Any = None
    """Suggested default."""

    options: list[dict[str, str]] | None = None
    """For select fields: [{value, label}, …]."""

    description: str | None = None
    """Help text."""


@dataclass
class TabDefinition:
    """Defines a tab provided by a plugin."""

    id: str
    """Unique identifier for the tab."""

    label: str
    """Human-readable label displayed in UI."""

    icon: str
    """Icon name (e.g., 'terminal', 'key', 'users')."""

    object_type: str
    """Object type this tab attaches to ('user' or 'group')."""

    activation_filter: str
    """LDAP filter to check if tab is active on an object."""

    schema_file: str
    """JSON schema file for UI form generation."""

    service_class: type["TabService"]
    """Service class handling the business logic."""

    create_schema: type[BaseModel]
    """Pydantic schema for creating/activating."""

    read_schema: type[BaseModel]
    """Pydantic schema for reading data."""

    update_schema: type[BaseModel]
    """Pydantic schema for updating data."""

    required: bool = False
    """Whether this tab is required (cannot be deactivated)."""


class TabService(ABC):
    """
    Base class for plugin tab services.

    Each plugin tab must implement this interface to handle
    CRUD operations on the tab's data.
    """

    # ObjectClasses to add when activating the tab
    OBJECT_CLASSES: list[str] = []

    # Attributes managed by this tab
    MANAGED_ATTRIBUTES: list[str] = []

    def __init__(self, ldap_service: Any, config: dict[str, Any]):
        """
        Initialize the service.

        Args:
            ldap_service: The LDAP service instance.
            config: Plugin configuration dictionary.
        """
        self._ldap = ldap_service
        self._config = config
        self.logger = logging.getLogger(f"heracles.plugins.{self.__class__.__name__}")

    @abstractmethod
    async def is_active(self, dn: str) -> bool:
        """
        Check if the tab is active on the given object.

        Args:
            dn: Distinguished Name of the object.

        Returns:
            True if the tab is active (objectClasses present).
        """
        pass

    @abstractmethod
    async def read(self, dn: str) -> BaseModel | None:
        """
        Read tab data from the object.

        Args:
            dn: Distinguished Name of the object.

        Returns:
            Data as Pydantic model, or None if not active.
        """
        pass

    @abstractmethod
    async def activate(self, dn: str, data: BaseModel) -> BaseModel:
        """
        Activate the tab on an object.

        Args:
            dn: Distinguished Name of the object.
            data: Creation data.

        Returns:
            Created data as Pydantic model.

        Raises:
            ValidationError: If already active or invalid data.
        """
        pass

    @abstractmethod
    async def update(self, dn: str, data: BaseModel) -> BaseModel:
        """
        Update tab data on an object.

        Args:
            dn: Distinguished Name of the object.
            data: Update data.

        Returns:
            Updated data as Pydantic model.

        Raises:
            ValidationError: If not active or invalid data.
        """
        pass

    @abstractmethod
    async def deactivate(self, dn: str) -> None:
        """
        Deactivate the tab on an object.

        Removes the objectClasses and attributes managed by this tab.

        Args:
            dn: Distinguished Name of the object.

        Raises:
            ValidationError: If not active.
        """
        pass

    # ------------------------------------------------------------------
    # Import / Export / Template extension points
    # ------------------------------------------------------------------

    @classmethod
    def get_import_fields(cls) -> list["PluginFieldDefinition"]:
        """
        Return LDAP attributes this plugin can accept during import.

        Override in concrete services to expose plugin-specific fields
        to the CSV import system.  The default returns the plugin's
        ``MANAGED_ATTRIBUTES`` with auto-generated labels.
        """
        return [PluginFieldDefinition(name=attr, label=attr) for attr in cls.MANAGED_ATTRIBUTES]

    @classmethod
    def get_export_fields(cls) -> list["PluginFieldDefinition"]:
        """
        Return LDAP attributes this plugin can provide during export.

        Override for richer labels / descriptions.  Default mirrors
        ``get_import_fields``.
        """
        return cls.get_import_fields()

    @classmethod
    def get_template_fields(cls) -> list["PluginTemplateField"]:
        """
        Return fields that a *template* may pre-configure for this plugin.

        These are the keys accepted in
        ``template.plugin_activations[plugin_name]``.

        Override in concrete services.  Default returns empty list.
        """
        return []


class Plugin(PluginConfigContract, ABC):
    """
    Base class for all Heracles plugins.

    A plugin can provide:
    - Tabs for existing object types (user, group)
    - New management types (systems, sudo rules)
    - API endpoints
    - Background tasks
    - Configuration with hot-reload support

    Implements PluginConfigContract for centralized configuration.
    """

    def __init__(self, config: dict[str, Any] = None):
        """
        Initialize the plugin.

        Args:
            config: Plugin-specific configuration (merged with defaults).
        """
        # Merge provided config with defaults
        self._config = self._merge_config(config or {})
        info = self.info()
        self.logger = logging.getLogger(f"heracles.plugins.{info.name}")

    def _merge_config(self, provided: dict[str, Any]) -> dict[str, Any]:
        """Merge provided config with defaults."""
        defaults = self.default_config()
        merged = defaults.copy()
        merged.update(provided)
        return merged

    @staticmethod
    @abstractmethod
    def info() -> PluginInfo:
        """
        Return plugin metadata.

        Returns:
            PluginInfo with name, version, dependencies, etc.
        """
        pass

    @staticmethod
    def tabs() -> list[TabDefinition]:
        """
        Return tabs provided by this plugin.

        Override this method to add tabs to user/group objects.

        Returns:
            List of TabDefinition objects.
        """
        return []

    @staticmethod
    def routes() -> list[Any]:
        """
        Return API routers provided by this plugin.

        Override this method to add custom API endpoints.

        Returns:
            List of FastAPI APIRouter objects.
        """
        return []

    @classmethod
    def acl_file(cls) -> Path | None:
        """
        Return the path to this plugin's acl.json file.

        By default, looks for acl.json in the same directory as
        the plugin's module file. Override if needed.

        Returns:
            Path to acl.json if it exists, None otherwise.
        """
        # Get the directory where the plugin class is defined
        try:
            module = inspect.getmodule(cls)
            if module is None or not hasattr(module, "__file__") or module.__file__ is None:
                return None

            plugin_dir = Path(module.__file__).parent
            acl_path = plugin_dir / "acl.json"

            return acl_path if acl_path.exists() else None
        except Exception:
            return None

    def on_activate(self) -> None:
        """
        Called when the plugin is activated.

        Override for initialization logic.
        """
        self.logger.info(f"Plugin {self.info().name} activated")

    def on_deactivate(self) -> None:
        """
        Called when the plugin is deactivated.

        Override for cleanup logic.
        """
        self.logger.info(f"Plugin {self.info().name} deactivated")

    def validate_plugin_config(self) -> list[str]:
        """
        Validate plugin configuration using the schema.

        This combines:
        1. Required config checks from PluginInfo
        2. Schema-based validation from PluginConfigContract

        Returns:
            List of error messages (empty if valid).
        """
        errors = []
        info = self.info()

        # Check required_config from PluginInfo (backwards compatibility)
        for key in info.required_config:
            if key not in self._config:
                errors.append(f"Missing required config: {key}")

        # Use schema-based validation from PluginConfigContract
        schema_errors = super().validate_config(self._config)
        errors.extend(schema_errors)

        return errors

    def update_config(self, new_config: dict[str, Any]) -> list[str]:
        """
        Update plugin configuration at runtime.

        Validates the new config, updates internal state, and calls
        on_config_change hook for hot-reload support.

        Args:
            new_config: New configuration values.

        Returns:
            List of error messages (empty if valid and applied).
        """
        # Merge with defaults
        merged = self.default_config()
        merged.update(new_config)

        # Validate
        errors = super().validate_config(merged)
        if errors:
            return errors

        # Find changed keys
        old_config = self._config.copy()
        changed_keys = [
            key for key in set(list(old_config.keys()) + list(merged.keys())) if old_config.get(key) != merged.get(key)
        ]

        # Apply new config
        self._config = merged

        # Call hot-reload hook
        if changed_keys:
            self.on_config_change(old_config, merged, changed_keys)

        return []

    @property
    def config(self) -> dict[str, Any]:
        """Get the current plugin configuration."""
        return self._config.copy()
