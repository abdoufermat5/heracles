"""
POSIX Plugin Definition
=======================

Main plugin class that registers POSIX functionality.
"""

from typing import Any, Dict, List

from heracles_api.plugins.base import (
    Plugin,
    PluginInfo,
    TabDefinition,
    ConfigSection,
    ConfigField,
    ConfigFieldType,
    ConfigFieldValidation,
    ConfigFieldOption,
)

from .schemas import (
    PosixAccountCreate,
    PosixAccountRead,
    PosixAccountUpdate,
    PosixGroupCreate,
    PosixGroupRead,
    PosixGroupUpdate,
    MixedGroupCreate,
    MixedGroupRead,
    MixedGroupUpdate,
)
from .service import PosixService, PosixGroupService, MixedGroupService
from .routes import router


class PosixPlugin(Plugin):
    """
    POSIX account management plugin.
    
    Provides Unix account attributes for users (posixAccount, shadowAccount)
    and groups (posixGroup).
    
    Compatible with standard LDAP POSIX implementation.
    """
    
    @staticmethod
    def info() -> PluginInfo:
        """Return plugin metadata."""
        return PluginInfo(
            name="posix",
            version="1.0.0",
            description="POSIX account management (Unix accounts)",
            author="Heracles Team",
            object_types=["user", "group", "mixed-group"],
            object_classes=[
                "posixAccount", 
                "shadowAccount", 
                "posixGroup", 
                "groupOfNames",
                "hostObject",  # For system trust
            ],
            dependencies=[],  # No dependencies for POSIX
            # Note: systems plugin dependency is optional (for host validation)
            optional_dependencies=["systems"],
            required_config=[],  # Using config_schema instead
            priority=10,  # Show early in tabs
            minimum_api_version="0.8.0",
        )
    
    @staticmethod
    def config_schema() -> List[ConfigSection]:
        """
        Define POSIX plugin configuration schema.
        
        Sections:
        - UID/GID Allocation: Ranges for automatic ID assignment
        - Defaults: Default values for new accounts
        - Home Directory: Home directory configuration
        """
        return [
            ConfigSection(
                id="uid_gid",
                label="UID/GID Allocation",
                description="Configure ranges for automatic UID and GID assignment",
                icon="hash",
                order=10,
                fields=[
                    ConfigField(
                        key="uid_min",
                        label="Minimum UID",
                        field_type=ConfigFieldType.INTEGER,
                        default_value=10000,
                        description="Minimum UID value for new POSIX accounts",
                        validation=ConfigFieldValidation(
                            required=True,
                            min_value=1000,
                            max_value=60000,
                        ),
                    ),
                    ConfigField(
                        key="uid_max",
                        label="Maximum UID",
                        field_type=ConfigFieldType.INTEGER,
                        default_value=60000,
                        description="Maximum UID value for new POSIX accounts",
                        validation=ConfigFieldValidation(
                            required=True,
                            min_value=1000,
                            max_value=65534,
                        ),
                    ),
                    ConfigField(
                        key="gid_min",
                        label="Minimum GID",
                        field_type=ConfigFieldType.INTEGER,
                        default_value=10000,
                        description="Minimum GID value for new POSIX groups",
                        validation=ConfigFieldValidation(
                            required=True,
                            min_value=1000,
                            max_value=60000,
                        ),
                    ),
                    ConfigField(
                        key="gid_max",
                        label="Maximum GID",
                        field_type=ConfigFieldType.INTEGER,
                        default_value=60000,
                        description="Maximum GID value for new POSIX groups",
                        validation=ConfigFieldValidation(
                            required=True,
                            min_value=1000,
                            max_value=65534,
                        ),
                    ),
                ],
            ),
            ConfigSection(
                id="defaults",
                label="Default Values",
                description="Default values for new POSIX accounts",
                icon="settings",
                order=20,
                fields=[
                    ConfigField(
                        key="default_shell",
                        label="Default Shell",
                        field_type=ConfigFieldType.SELECT,
                        default_value="/bin/bash",
                        description="Default login shell for new accounts",
                        options=[
                            ConfigFieldOption("/bin/bash", "Bash"),
                            ConfigFieldOption("/bin/sh", "Bourne Shell"),
                            ConfigFieldOption("/bin/zsh", "Zsh"),
                            ConfigFieldOption("/usr/bin/fish", "Fish"),
                            ConfigFieldOption("/bin/false", "No Login"),
                            ConfigFieldOption("/usr/sbin/nologin", "No Login (with message)"),
                        ],
                    ),
                    ConfigField(
                        key="default_gid",
                        label="Default Primary GID",
                        field_type=ConfigFieldType.INTEGER,
                        default_value=None,
                        description="Default primary group GID (leave empty to auto-select)",
                        validation=ConfigFieldValidation(
                            required=False,
                            min_value=100,
                            max_value=65534,
                        ),
                    ),
                ],
            ),
            ConfigSection(
                id="home_directory",
                label="Home Directory",
                description="Home directory settings for new accounts",
                icon="folder",
                order=30,
                fields=[
                    ConfigField(
                        key="default_home_base",
                        label="Home Directory Base",
                        field_type=ConfigFieldType.PATH,
                        default_value="/home",
                        description="Base path for home directories",
                        validation=ConfigFieldValidation(
                            required=True,
                            pattern=r"^/[a-zA-Z0-9/_-]+$",
                        ),
                    ),
                    ConfigField(
                        key="home_directory_template",
                        label="Home Directory Template",
                        field_type=ConfigFieldType.STRING,
                        default_value="{home_base}/{uid}",
                        description="Template for home directory path. Variables: {home_base}, {uid}, {cn}",
                        validation=ConfigFieldValidation(
                            required=True,
                            min_length=5,
                            max_length=256,
                        ),
                    ),
                    ConfigField(
                        key="create_home_directory",
                        label="Create Home Directory",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=False,
                        description="Automatically create home directory (requires server-side script)",
                    ),
                ],
            ),
            ConfigSection(
                id="shadow",
                label="Shadow Password",
                description="Shadow password policy defaults",
                icon="lock",
                order=40,
                fields=[
                    ConfigField(
                        key="shadow_min",
                        label="Minimum Age (days)",
                        field_type=ConfigFieldType.INTEGER,
                        default_value=0,
                        description="Minimum days before password can be changed",
                        validation=ConfigFieldValidation(
                            required=False,
                            min_value=0,
                            max_value=365,
                        ),
                    ),
                    ConfigField(
                        key="shadow_max",
                        label="Maximum Age (days)",
                        field_type=ConfigFieldType.INTEGER,
                        default_value=99999,
                        description="Maximum days before password must be changed (99999 = never)",
                        validation=ConfigFieldValidation(
                            required=False,
                            min_value=0,
                            max_value=99999,
                        ),
                    ),
                    ConfigField(
                        key="shadow_warning",
                        label="Warning Period (days)",
                        field_type=ConfigFieldType.INTEGER,
                        default_value=7,
                        description="Days before expiration to warn user",
                        validation=ConfigFieldValidation(
                            required=False,
                            min_value=0,
                            max_value=90,
                        ),
                    ),
                    ConfigField(
                        key="shadow_inactive",
                        label="Inactive Period (days)",
                        field_type=ConfigFieldType.INTEGER,
                        default_value=-1,
                        description="Days after expiration before account is disabled (-1 = never)",
                        validation=ConfigFieldValidation(
                            required=False,
                            min_value=-1,
                            max_value=365,
                        ),
                    ),
                ],
            ),
        ]
    
    @staticmethod
    def default_config() -> Dict[str, Any]:
        """Return default configuration values."""
        return {
            # UID/GID Allocation
            "uid_min": 10000,
            "uid_max": 60000,
            "gid_min": 10000,
            "gid_max": 60000,
            # Defaults
            "default_shell": "/bin/bash",
            "default_gid": None,
            # Home Directory
            "default_home_base": "/home",
            "home_directory_template": "{home_base}/{uid}",
            "create_home_directory": False,
            # Shadow
            "shadow_min": 0,
            "shadow_max": 99999,
            "shadow_warning": 7,
            "shadow_inactive": -1,
        }
    
    def validate_config_business_rules(self, config: Dict[str, Any]) -> List[str]:
        """Custom business rule validation for POSIX config."""
        errors = []
        
        # UID range validation
        uid_min = config.get("uid_min", 10000)
        uid_max = config.get("uid_max", 60000)
        if uid_min >= uid_max:
            errors.append("Minimum UID must be less than Maximum UID")
        
        if uid_max - uid_min < 100:
            errors.append("UID range should be at least 100 (for practical use)")
        
        # GID range validation
        gid_min = config.get("gid_min", 10000)
        gid_max = config.get("gid_max", 60000)
        if gid_min >= gid_max:
            errors.append("Minimum GID must be less than Maximum GID")
        
        if gid_max - gid_min < 100:
            errors.append("GID range should be at least 100 (for practical use)")
        
        # Home directory template validation
        template = config.get("home_directory_template", "")
        if template and "{uid}" not in template and "{cn}" not in template:
            errors.append("Home directory template must contain {uid} or {cn}")
        
        return errors
    
    def on_config_change(
        self,
        old_config: Dict[str, Any],
        new_config: Dict[str, Any],
        changed_keys: List[str],
    ) -> None:
        """Handle configuration changes at runtime."""
        self.logger.info(
            f"POSIX plugin configuration updated: {changed_keys}"
        )
        
        # Log specific changes
        if "uid_min" in changed_keys or "uid_max" in changed_keys:
            self.logger.info(
                f"UID range changed: {new_config.get('uid_min')}-{new_config.get('uid_max')}"
            )
        
        if "gid_min" in changed_keys or "gid_max" in changed_keys:
            self.logger.info(
                f"GID range changed: {new_config.get('gid_min')}-{new_config.get('gid_max')}"
            )
    
    @staticmethod
    def tabs() -> List[TabDefinition]:
        """Define tabs provided by this plugin."""
        return [
            TabDefinition(
                id="posix",
                label="Unix",
                icon="terminal",
                object_type="user",
                activation_filter="(objectClass=posixAccount)",
                schema_file="schema_user.json",
                service_class=PosixService,
                create_schema=PosixAccountCreate,
                read_schema=PosixAccountRead,
                update_schema=PosixAccountUpdate,
                required=False,
            ),
            TabDefinition(
                id="posix-group",
                label="POSIX",
                icon="users",
                object_type="group",
                activation_filter="(objectClass=posixGroup)",
                schema_file="schema_group.json",
                service_class=PosixGroupService,
                create_schema=PosixGroupCreate,
                read_schema=PosixGroupRead,
                update_schema=PosixGroupUpdate,
                required=False,
            ),
            # MixedGroup: combination of groupOfNames + posixGroup
            TabDefinition(
                id="mixed-group",
                label="Mixed Group",
                icon="layers",
                object_type="mixed-group",
                activation_filter="(&(objectClass=groupOfNames)(objectClass=posixGroup))",
                schema_file="schema_mixed_group.json",
                service_class=MixedGroupService,
                create_schema=MixedGroupCreate,
                read_schema=MixedGroupRead,
                update_schema=MixedGroupUpdate,
                required=False,
            ),
        ]
    
    def on_activate(self) -> None:
        """Called when plugin is activated."""
        uid_min = self._config.get("uid_min", 10000)
        uid_max = self._config.get("uid_max", 60000)
        self.logger.info(
            f"POSIX plugin activated (UID range: {uid_min}-{uid_max})"
        )
    
    def on_deactivate(self) -> None:
        """Called when plugin is deactivated."""
        self.logger.info("POSIX plugin deactivated")

    @staticmethod
    def routes() -> List[Any]:
        """Return API routers for POSIX endpoints."""
        return [router]
