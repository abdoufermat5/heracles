"""
POSIX Plugin Definition
=======================

Main plugin class that registers POSIX functionality.
"""

from typing import Any, List

from heracles_api.plugins.base import Plugin, PluginInfo, TabDefinition

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
            required_config=[],
            priority=10,  # Show early in tabs
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
