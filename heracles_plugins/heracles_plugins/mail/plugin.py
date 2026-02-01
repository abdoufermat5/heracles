"""
Mail Plugin Definition
======================

Main plugin class that registers mail account management functionality.
"""

from typing import Any, List

from heracles_api.plugins.base import Plugin, PluginInfo, TabDefinition

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

    def on_activate(self) -> None:
        """Called when plugin is activated."""
        self.logger.info("Mail plugin activated")

    def on_deactivate(self) -> None:
        """Called when plugin is deactivated."""
        self.logger.info("Mail plugin deactivated")

    @staticmethod
    def routes() -> List[Any]:
        """Return API routers for mail endpoints."""
        return [router]
