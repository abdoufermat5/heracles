"""
Sudo Plugin Definition
======================

Main plugin class that registers sudo functionality.
"""

from typing import Any, Dict, List, Optional

from heracles_api.plugins.base import (
    ConfigField,
    ConfigFieldOption,
    ConfigFieldType,
    ConfigFieldValidation,
    ConfigSection,
    Plugin,
    PluginInfo,
    TabDefinition,
)

from .schemas import (
    SudoRoleCreate,
    SudoRoleRead,
    SudoRoleUpdate,
)
from .service import SudoService
from .routes import router


class SudoPlugin(Plugin):
    """
    Sudo role management plugin.
    
    Provides sudo rules management via LDAP sudoRole entries.
    
    Compatible with standard sudo-ldap implementation.
    
    Configuration:
        - sudoers_rdn: Base RDN for sudoers entries (default: ou=sudoers)
        - validate_users: Validate referenced users exist
        - validate_hosts: Validate referenced hosts exist
        - default_options: Default sudo options for new rules
        - requiretty_default: Default for requiretty option
    """
    
    @staticmethod
    def info() -> PluginInfo:
        """Return plugin metadata."""
        return PluginInfo(
            name="sudo",
            version="1.0.0",
            description="Sudo role management (sudoers via LDAP)",
            author="Heracles Team",
            object_types=["sudo-role"],
            object_classes=["sudoRole"],
            dependencies=[],  # No dependencies
            optional_dependencies=["posix", "systems"],  # For user/host validation
            required_config=[],
            priority=20,  # After POSIX
        )
    
    @staticmethod
    def tabs() -> List[TabDefinition]:
        """Define tabs provided by this plugin."""
        return [
            TabDefinition(
                id="sudo",
                label="Sudo Role",
                icon="shield",
                object_type="sudo-role",
                activation_filter="(objectClass=sudoRole)",
                schema_file="schema_sudo_role.json",
                service_class=SudoService,
                create_schema=SudoRoleCreate,
                read_schema=SudoRoleRead,
                update_schema=SudoRoleUpdate,
                required=True,  # Standalone object type
            ),
        ]
    
    @staticmethod
    def config_schema() -> List[ConfigSection]:
        """
        Define configuration schema for Sudo plugin.
        
        Returns:
            List of configuration sections with fields.
        """
        return [
            ConfigSection(
                id="general",
                label="General Settings",
                description="Basic sudo plugin configuration",
                fields=[
                    ConfigField(
                        key="sudoers_rdn",
                        label="Sudoers RDN",
                        description="Base RDN for sudoers entries in LDAP",
                        field_type=ConfigFieldType.STRING,
                        default_value="ou=sudoers",
                        required=True,
                        requires_restart=True,
                        validation=ConfigFieldValidation(
                            pattern=r"^[a-z]+=.+$",
                        ),
                    ),
                ],
            ),
            ConfigSection(
                id="validation",
                label="Validation",
                description="Reference validation settings",
                fields=[
                    ConfigField(
                        key="validate_users",
                        label="Validate Users",
                        description="Validate that referenced users exist in LDAP",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=False,
                    ),
                    ConfigField(
                        key="validate_hosts",
                        label="Validate Hosts",
                        description="Validate that referenced hosts exist in systems",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=False,
                    ),
                    ConfigField(
                        key="validate_commands",
                        label="Validate Commands",
                        description="Check command paths for basic validity",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=False,
                    ),
                ],
            ),
            ConfigSection(
                id="defaults",
                label="Default Values",
                description="Default values for new sudo rules",
                fields=[
                    ConfigField(
                        key="default_sudo_host",
                        label="Default Host",
                        description="Default host value for new rules",
                        field_type=ConfigFieldType.STRING,
                        default_value="ALL",
                    ),
                    ConfigField(
                        key="default_run_as_user",
                        label="Default Run As User",
                        description="Default run-as user for new rules",
                        field_type=ConfigFieldType.STRING,
                        default_value="ALL",
                    ),
                    ConfigField(
                        key="default_run_as_group",
                        label="Default Run As Group",
                        description="Default run-as group for new rules",
                        field_type=ConfigFieldType.STRING,
                        default_value="",
                    ),
                ],
            ),
            ConfigSection(
                id="options",
                label="Default Options",
                description="Default sudo options for new rules",
                fields=[
                    ConfigField(
                        key="requiretty_default",
                        label="Require TTY",
                        description="Default setting for requiretty option",
                        field_type=ConfigFieldType.SELECT,
                        default_value="unset",
                        options=[
                            ConfigFieldOption(value="unset", label="Not Set"),
                            ConfigFieldOption(value="true", label="Required"),
                            ConfigFieldOption(value="false", label="Not Required"),
                        ],
                    ),
                    ConfigField(
                        key="nopasswd_default",
                        label="No Password",
                        description="Default setting for NOPASSWD option",
                        field_type=ConfigFieldType.SELECT,
                        default_value="unset",
                        options=[
                            ConfigFieldOption(value="unset", label="Not Set (Password Required)"),
                            ConfigFieldOption(value="true", label="NOPASSWD"),
                            ConfigFieldOption(value="false", label="PASSWD (Explicit)"),
                        ],
                    ),
                    ConfigField(
                        key="noexec_default",
                        label="No Exec",
                        description="Default setting for NOEXEC option",
                        field_type=ConfigFieldType.SELECT,
                        default_value="unset",
                        options=[
                            ConfigFieldOption(value="unset", label="Not Set"),
                            ConfigFieldOption(value="true", label="NOEXEC"),
                            ConfigFieldOption(value="false", label="EXEC (Explicit)"),
                        ],
                    ),
                    ConfigField(
                        key="setenv_default",
                        label="Set Environment",
                        description="Default setting for SETENV option",
                        field_type=ConfigFieldType.SELECT,
                        default_value="unset",
                        options=[
                            ConfigFieldOption(value="unset", label="Not Set"),
                            ConfigFieldOption(value="true", label="SETENV"),
                            ConfigFieldOption(value="false", label="NOSETENV"),
                        ],
                    ),
                ],
            ),
            ConfigSection(
                id="security",
                label="Security Settings",
                description="Security-related configuration",
                fields=[
                    ConfigField(
                        key="allow_all_commands",
                        label="Allow ALL Commands",
                        description="Allow rules with ALL as command (not recommended)",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=True,
                    ),
                    ConfigField(
                        key="warn_all_commands",
                        label="Warn on ALL",
                        description="Show warning when creating rules with ALL commands",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=True,
                    ),
                    ConfigField(
                        key="allow_root_nopasswd",
                        label="Allow Root NOPASSWD",
                        description="Allow NOPASSWD for rules running as root",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=True,
                    ),
                ],
            ),
        ]
    
    @staticmethod
    def default_config() -> Dict[str, Any]:
        """
        Return default configuration values.
        
        Returns:
            Dictionary of default configuration values.
        """
        return {
            # General
            "sudoers_rdn": "ou=sudoers",
            # Validation
            "validate_users": False,
            "validate_hosts": False,
            "validate_commands": False,
            # Defaults
            "default_sudo_host": "ALL",
            "default_run_as_user": "ALL",
            "default_run_as_group": "",
            # Options
            "requiretty_default": "unset",
            "nopasswd_default": "unset",
            "noexec_default": "unset",
            "setenv_default": "unset",
            # Security
            "allow_all_commands": True,
            "warn_all_commands": True,
            "allow_root_nopasswd": True,
        }
    
    @staticmethod
    def validate_config_business_rules(config: Dict[str, Any]) -> Optional[str]:
        """
        Validate configuration business rules.
        
        Args:
            config: Configuration dictionary to validate.
            
        Returns:
            Error message if validation fails, None otherwise.
        """
        # No complex business rules for sudo config
        return None

    def on_config_change(
        self,
        old_config: Dict[str, Any],
        new_config: Dict[str, Any],
        changed_keys: List[str],
    ) -> None:
        """
        Handle configuration changes.
        
        Args:
            old_config: Previous configuration.
            new_config: New configuration.
            changed_keys: List of changed configuration keys.
        """
        self.logger.info(f"Sudo plugin configuration updated: {changed_keys}")
        
        # Log security-related changes
        if "allow_all_commands" in changed_keys:
            self.logger.warning(
                f"Security setting changed: allow_all_commands = {new_config.get('allow_all_commands')}"
            )
        
        if "allow_root_nopasswd" in changed_keys:
            self.logger.warning(
                f"Security setting changed: allow_root_nopasswd = {new_config.get('allow_root_nopasswd')}"
            )
    
    def on_activate(self) -> None:
        """Called when plugin is activated."""
        sudoers_rdn = self.get_config_value("sudoers_rdn", "ou=sudoers")
        self.logger.info(f"Sudo plugin activated (sudoers RDN: {sudoers_rdn})")
    
    def on_deactivate(self) -> None:
        """Called when plugin is deactivated."""
        self.logger.info("Sudo plugin deactivated")

    @staticmethod
    def routes() -> List[Any]:
        """Return API routers for sudo endpoints."""
        return [router]
