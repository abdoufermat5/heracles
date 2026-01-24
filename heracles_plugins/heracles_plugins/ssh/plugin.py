"""
SSH Plugin Definition
=====================

Main plugin class that registers SSH key management functionality.
"""

from typing import Any, List

from heracles_api.plugins.base import Plugin, PluginInfo, TabDefinition

from .schemas import (
    SSHKeyCreate,
    SSHKeyRead,
    UserSSHStatus,
)
from .service import SSHService
from .routes import router


class SSHPlugin(Plugin):
    """
    SSH key management plugin.
    
    Provides SSH public key management via the ldapPublicKey objectClass.
    
    Compatible with OpenSSH LDAP integration (AuthorizedKeysCommand).
    """
    
    @staticmethod
    def info() -> PluginInfo:
        """Return plugin metadata."""
        return PluginInfo(
            name="ssh",
            version="1.0.0",
            description="SSH public key management (ldapPublicKey)",
            author="Heracles Team",
            object_types=["user"],
            object_classes=["ldapPublicKey"],
            dependencies=[],  # No hard dependencies
            optional_dependencies=["posix"],  # Works better with POSIX users
            required_config=[],
            priority=25,  # After POSIX
        )
    
    @staticmethod
    def tabs() -> List[TabDefinition]:
        """Define tabs provided by this plugin."""
        return [
            TabDefinition(
                id="ssh",
                label="SSH Keys",
                icon="key",
                object_type="user",
                activation_filter="(objectClass=inetOrgPerson)",
                schema_file="schema_ssh.json",
                service_class=SSHService,
                create_schema=SSHKeyCreate,
                read_schema=SSHKeyRead,
                update_schema=None,  # Keys are add/remove only
                required=False,  # Optional tab for users
            ),
        ]
    
    def on_activate(self) -> None:
        """Called when plugin is activated."""
        self.logger.info("SSH plugin activated")
    
    def on_deactivate(self) -> None:
        """Called when plugin is deactivated."""
        self.logger.info("SSH plugin deactivated")

    @staticmethod
    def routes() -> List[Any]:
        """Return API routers for SSH endpoints."""
        return [router]
