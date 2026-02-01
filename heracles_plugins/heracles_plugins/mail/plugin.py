"""
Mail Plugin Definition
======================

Main plugin class that registers mail account management functionality.
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
    MailAccountCreate,
    MailAccountRead,
    MailAccountUpdate,
    MailGroupCreate,
    MailGroupRead,
    MailGroupUpdate,
)
from .services.mail_user_service import MailUserService
from .services.mail_group_service import MailGroupService
from .routes import router


class MailPlugin(Plugin):
    """
    Mail account management plugin.

    Provides mail account management via the hrcMailAccount and hrcGroupMail
    objectClasses.

    Features:
    - User mail accounts with quota, forwarding, and vacation
    - Group mailing lists with local-only restrictions
    
    Configuration:
        - default_mail_domain: Default domain for mail addresses
        - default_quota: Default mailbox quota in bytes
        - allow_forwarding: Allow mail forwarding
        - allow_vacation: Allow vacation/auto-reply messages
        - quota_unit: Display unit for quotas (KB, MB, GB)
    """

    @staticmethod
    def info() -> PluginInfo:
        """Return plugin metadata."""
        return PluginInfo(
            name="mail",
            version="1.0.0",
            description="Mail account management (hrcMailAccount, hrcGroupMail)",
            author="Heracles Team",
            object_types=["user", "group"],
            object_classes=["hrcMailAccount", "hrcGroupMail"],
            dependencies=[],
            optional_dependencies=["posix"],
            required_config=[],
            priority=35,  # After POSIX (10), SSH (25), Sudo (30)
        )

    @staticmethod
    def tabs() -> List[TabDefinition]:
        """Define tabs provided by this plugin."""
        return [
            TabDefinition(
                id="mail",
                label="Mail",
                icon="mail",
                object_type="user",
                activation_filter="(objectClass=hrcMailAccount)",
                schema_file="schema_mail.json",
                service_class=MailUserService,
                create_schema=MailAccountCreate,
                read_schema=MailAccountRead,
                update_schema=MailAccountUpdate,
                required=False,
            ),
            TabDefinition(
                id="mail-group",
                label="Mailing List",
                icon="mails",
                object_type="group",
                activation_filter="(objectClass=hrcGroupMail)",
                schema_file="schema_mail_group.json",
                service_class=MailGroupService,
                create_schema=MailGroupCreate,
                read_schema=MailGroupRead,
                update_schema=MailGroupUpdate,
                required=False,
            ),
        ]
    
    @staticmethod
    def config_schema() -> List[ConfigSection]:
        """
        Define configuration schema for Mail plugin.
        
        Returns:
            List of configuration sections with fields.
        """
        return [
            ConfigSection(
                id="general",
                label="General Settings",
                description="Basic mail plugin configuration",
                fields=[
                    ConfigField(
                        key="default_mail_domain",
                        label="Default Mail Domain",
                        description="Default domain for mail addresses (e.g., example.com)",
                        field_type=ConfigFieldType.STRING,
                        default_value="heracles.local",
                        required=True,
                        validation=ConfigFieldValidation(
                            pattern=r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$",
                        ),
                    ),
                    ConfigField(
                        key="mail_attribute",
                        label="Primary Mail Attribute",
                        description="LDAP attribute for primary mail address",
                        field_type=ConfigFieldType.SELECT,
                        default_value="mail",
                        options=[
                            ConfigFieldOption(value="mail", label="mail"),
                            ConfigFieldOption(value="mailPrimaryAddress", label="mailPrimaryAddress"),
                        ],
                    ),
                    ConfigField(
                        key="auto_generate_mail",
                        label="Auto-Generate Mail Address",
                        description="Automatically generate mail address from user attributes",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=True,
                    ),
                    ConfigField(
                        key="mail_address_template",
                        label="Mail Address Template",
                        description="Template for auto-generated addresses ({uid}, {givenName}, {sn})",
                        field_type=ConfigFieldType.STRING,
                        default_value="{uid}@{domain}",
                    ),
                ],
            ),
            ConfigSection(
                id="quota",
                label="Quota Settings",
                description="Mailbox quota configuration",
                fields=[
                    ConfigField(
                        key="default_quota",
                        label="Default Quota (MB)",
                        description="Default mailbox quota in megabytes (0 = unlimited)",
                        field_type=ConfigFieldType.INTEGER,
                        default_value=1024,
                        validation=ConfigFieldValidation(
                            min_value=0,
                            max_value=1048576,  # 1 TB max
                        ),
                    ),
                    ConfigField(
                        key="quota_unit",
                        label="Quota Display Unit",
                        description="Unit for displaying quotas in the UI",
                        field_type=ConfigFieldType.SELECT,
                        default_value="MB",
                        options=[
                            ConfigFieldOption(value="KB", label="Kilobytes (KB)"),
                            ConfigFieldOption(value="MB", label="Megabytes (MB)"),
                            ConfigFieldOption(value="GB", label="Gigabytes (GB)"),
                        ],
                    ),
                    ConfigField(
                        key="enforce_quota",
                        label="Enforce Quota",
                        description="Require quota for all mail accounts",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=False,
                    ),
                    ConfigField(
                        key="max_quota",
                        label="Maximum Quota (MB)",
                        description="Maximum allowed quota (0 = no limit)",
                        field_type=ConfigFieldType.INTEGER,
                        default_value=0,
                        validation=ConfigFieldValidation(
                            min_value=0,
                            max_value=1048576,
                        ),
                    ),
                ],
            ),
            ConfigSection(
                id="features",
                label="Features",
                description="Enable or disable mail features",
                fields=[
                    ConfigField(
                        key="allow_forwarding",
                        label="Allow Forwarding",
                        description="Allow users to forward mail to external addresses",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=True,
                    ),
                    ConfigField(
                        key="allow_vacation",
                        label="Allow Vacation Messages",
                        description="Allow users to set vacation/auto-reply messages",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=True,
                    ),
                    ConfigField(
                        key="allow_aliases",
                        label="Allow Mail Aliases",
                        description="Allow multiple mail aliases per user",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=True,
                    ),
                    ConfigField(
                        key="max_aliases",
                        label="Maximum Aliases",
                        description="Maximum mail aliases per user (0 = unlimited)",
                        field_type=ConfigFieldType.INTEGER,
                        default_value=10,
                        validation=ConfigFieldValidation(
                            min_value=0,
                            max_value=100,
                        ),
                    ),
                ],
            ),
            ConfigSection(
                id="mailing_lists",
                label="Mailing Lists",
                description="Group mailing list settings",
                fields=[
                    ConfigField(
                        key="default_list_type",
                        label="Default List Type",
                        description="Default type for new mailing lists",
                        field_type=ConfigFieldType.SELECT,
                        default_value="open",
                        options=[
                            ConfigFieldOption(value="open", label="Open (Anyone can post)"),
                            ConfigFieldOption(value="moderated", label="Moderated"),
                            ConfigFieldOption(value="members", label="Members Only"),
                            ConfigFieldOption(value="announce", label="Announcement Only"),
                        ],
                    ),
                    ConfigField(
                        key="allow_external_members",
                        label="Allow External Members",
                        description="Allow adding external email addresses to lists",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=False,
                    ),
                    ConfigField(
                        key="group_mail_suffix",
                        label="Group Mail Suffix",
                        description="Suffix for auto-generated group addresses (e.g., -list)",
                        field_type=ConfigFieldType.STRING,
                        default_value="",
                    ),
                ],
            ),
            ConfigSection(
                id="validation",
                label="Validation",
                description="Input validation settings",
                fields=[
                    ConfigField(
                        key="validate_mail_format",
                        label="Validate Mail Format",
                        description="Validate email address format",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=True,
                    ),
                    ConfigField(
                        key="validate_domain",
                        label="Validate Domain",
                        description="Only allow mail addresses in configured domains",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=False,
                    ),
                    ConfigField(
                        key="allowed_domains",
                        label="Allowed Domains",
                        description="List of allowed mail domains (comma-separated)",
                        field_type=ConfigFieldType.STRING,
                        default_value="",
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
            "default_mail_domain": "",
            "mail_attribute": "mail",
            "auto_generate_mail": True,
            "mail_address_template": "{uid}@{domain}",
            # Quota
            "default_quota": 1024,
            "quota_unit": "MB",
            "enforce_quota": False,
            "max_quota": 0,
            # Features
            "allow_forwarding": True,
            "allow_vacation": True,
            "allow_aliases": True,
            "max_aliases": 10,
            # Mailing lists
            "default_list_type": "open",
            "allow_external_members": False,
            "group_mail_suffix": "",
            # Validation
            "validate_mail_format": True,
            "validate_domain": False,
            "allowed_domains": "",
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
        # Validate quota settings
        default_quota = config.get("default_quota", 1024)
        max_quota = config.get("max_quota", 0)
        
        if max_quota > 0 and default_quota > max_quota:
            return "Default quota cannot exceed maximum quota"
        
        # Validate mail template
        template = config.get("mail_address_template", "")
        if config.get("auto_generate_mail") and not template:
            return "Mail address template is required when auto-generation is enabled"
        
        # Validate template placeholders
        if template:
            valid_placeholders = ["{uid}", "{givenName}", "{sn}", "{cn}", "{domain}"]
            import re
            placeholders = re.findall(r"\{[^}]+\}", template)
            for placeholder in placeholders:
                if placeholder not in valid_placeholders:
                    return f"Invalid placeholder in mail template: {placeholder}"
        
        # Validate domain validation settings
        if config.get("validate_domain") and not config.get("allowed_domains"):
            return "Allowed domains must be specified when domain validation is enabled"
        
        return None
    
    @staticmethod
    def on_config_change(old_config: Dict[str, Any], new_config: Dict[str, Any]) -> None:
        """
        Handle configuration changes.
        
        Args:
            old_config: Previous configuration.
            new_config: New configuration.
        """
        # Log significant changes
        if old_config.get("default_mail_domain") != new_config.get("default_mail_domain"):
            # Domain change affects new accounts
            pass
        
        if old_config.get("default_quota") != new_config.get("default_quota"):
            # Quota change affects new accounts only
            pass

    def on_activate(self) -> None:
        """Called when plugin is activated."""
        domain = self.get_config_value("default_mail_domain", "")
        self.logger.info(f"Mail plugin activated (default domain: {domain or 'not set'})")

    def on_deactivate(self) -> None:
        """Called when plugin is deactivated."""
        self.logger.info("Mail plugin deactivated")

    @staticmethod
    def routes() -> List[Any]:
        """Return API routers for mail endpoints."""
        return [router]
