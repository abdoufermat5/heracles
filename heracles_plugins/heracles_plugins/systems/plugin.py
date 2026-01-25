"""
Systems Plugin Definition
=========================

Main plugin class that registers systems management functionality.
"""

from typing import Any, List

from heracles_api.plugins.base import Plugin, PluginInfo, TabDefinition

from .schemas import (
    SystemType,
    SystemCreate,
    SystemRead,
    SystemUpdate,
)
from .service import SystemService
from .routes import router


class SystemsPlugin(Plugin):
    """
    Systems management plugin.
    
    Provides management of servers, workstations, terminals, printers,
    components, and phones in the LDAP directory.
    
    System Types:
        - server: Physical or virtual servers (hrcServer)
        - workstation: User workstations (hrcWorkstation)
        - terminal: Thin clients/terminals (hrcTerminal)
        - printer: Network printers (hrcPrinter)
        - component: Network devices, switches, etc. (device)
        - phone: IP phones (hrcPhone)
        - mobile: Mobile phones (hrcMobilePhone)
    
    All types support IP/MAC addressing via ipHost and ieee802Device
    auxiliary classes.
    """
    
    @staticmethod
    def info() -> PluginInfo:
        """Return plugin metadata."""
        return PluginInfo(
            name="systems",
            version="1.0.0",
            description="System management (servers, workstations, terminals, printers, components, phones)",
            author="Heracles Team",
            object_types=[
                "system-server",
                "system-workstation", 
                "system-terminal",
                "system-printer",
                "system-component",
                "system-phone",
                "system-mobile",
            ],
            object_classes=[
                "hrcServer",
                "hrcWorkstation",
                "hrcTerminal",
                "hrcPrinter",
                "device",
                "hrcPhone",
                "hrcMobilePhone",
                "ipHost",
                "ieee802Device",
            ],
            dependencies=[],  # No dependencies
            optional_dependencies=[],
            required_config=[],
            priority=15,  # Before POSIX (which depends on it for host validation)
        )
    
    @staticmethod
    def tabs() -> List[TabDefinition]:
        """
        Define tabs provided by this plugin.
        
        Systems is a management plugin - it manages standalone objects,
        not tabs on users/groups. Each system type is its own object type.
        
        The "systems" tab is the main service provider for cross-type operations.
        """
        return [
            # Main systems service (for cross-type operations like host validation)
            TabDefinition(
                id="systems",
                label="Systems",
                icon="server",
                object_type="system",
                activation_filter="(|(objectClass=hrcServer)(objectClass=hrcWorkstation)(objectClass=hrcTerminal)(objectClass=hrcPrinter)(objectClass=device)(objectClass=hrcPhone)(objectClass=hrcMobilePhone))",
                schema_file="schema_server.json",
                service_class=SystemService,
                create_schema=SystemCreate,
                read_schema=SystemRead,
                update_schema=SystemUpdate,
                required=True,
            ),
            # Server
            TabDefinition(
                id="system-server",
                label="Server",
                icon="server",
                object_type="system-server",
                activation_filter="(objectClass=hrcServer)",
                schema_file="schema_server.json",
                service_class=SystemService,
                create_schema=SystemCreate,
                read_schema=SystemRead,
                update_schema=SystemUpdate,
                required=True,
            ),
            # Workstation
            TabDefinition(
                id="system-workstation",
                label="Workstation",
                icon="monitor",
                object_type="system-workstation",
                activation_filter="(objectClass=hrcWorkstation)",
                schema_file="schema_workstation.json",
                service_class=SystemService,
                create_schema=SystemCreate,
                read_schema=SystemRead,
                update_schema=SystemUpdate,
                required=True,
            ),
            # Terminal
            TabDefinition(
                id="system-terminal",
                label="Terminal",
                icon="terminal",
                object_type="system-terminal",
                activation_filter="(objectClass=hrcTerminal)",
                schema_file="schema_terminal.json",
                service_class=SystemService,
                create_schema=SystemCreate,
                read_schema=SystemRead,
                update_schema=SystemUpdate,
                required=True,
            ),
            # Printer
            TabDefinition(
                id="system-printer",
                label="Printer",
                icon="printer",
                object_type="system-printer",
                activation_filter="(objectClass=hrcPrinter)",
                schema_file="schema_printer.json",
                service_class=SystemService,
                create_schema=SystemCreate,
                read_schema=SystemRead,
                update_schema=SystemUpdate,
                required=True,
            ),
            # Component
            TabDefinition(
                id="system-component",
                label="Component",
                icon="cpu",
                object_type="system-component",
                activation_filter="(objectClass=device)",
                schema_file="schema_component.json",
                service_class=SystemService,
                create_schema=SystemCreate,
                read_schema=SystemRead,
                update_schema=SystemUpdate,
                required=True,
            ),
            # Phone
            TabDefinition(
                id="system-phone",
                label="Phone",
                icon="phone",
                object_type="system-phone",
                activation_filter="(objectClass=hrcPhone)",
                schema_file="schema_phone.json",
                service_class=SystemService,
                create_schema=SystemCreate,
                read_schema=SystemRead,
                update_schema=SystemUpdate,
                required=True,
            ),
            # Mobile Phone
            TabDefinition(
                id="system-mobile",
                label="Mobile Phone",
                icon="smartphone",
                object_type="system-mobile",
                activation_filter="(objectClass=hrcMobilePhone)",
                schema_file="schema_mobile.json",
                service_class=SystemService,
                create_schema=SystemCreate,
                read_schema=SystemRead,
                update_schema=SystemUpdate,
                required=True,
            ),
        ]
    
    def on_activate(self) -> None:
        """Called when plugin is activated."""
        systems_rdn = self._config.get("systems_rdn", "ou=systems")
        self.logger.info(f"Systems plugin activated (systems RDN: {systems_rdn})")
    
    def on_deactivate(self) -> None:
        """Called when plugin is deactivated."""
        self.logger.info("Systems plugin deactivated")

    @staticmethod
    def routes() -> List[Any]:
        """Return API routers for systems endpoints."""
        return [router]
