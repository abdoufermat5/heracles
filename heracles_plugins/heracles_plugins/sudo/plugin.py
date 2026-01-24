"""
Sudo Plugin Definition
======================

Main plugin class that registers sudo functionality.
"""

from typing import Any, List

from heracles_api.plugins.base import Plugin, PluginInfo, TabDefinition

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
    
    def on_activate(self) -> None:
        """Called when plugin is activated."""
        sudoers_rdn = self._config.get("sudoers_rdn", "ou=sudoers")
        self.logger.info(f"Sudo plugin activated (sudoers RDN: {sudoers_rdn})")
    
    def on_deactivate(self) -> None:
        """Called when plugin is deactivated."""
        self.logger.info("Sudo plugin deactivated")

    @staticmethod
    def routes() -> List[Any]:
        """Return API routers for sudo endpoints."""
        return [router]
