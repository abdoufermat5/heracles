"""
Systems Plugin Definition
=========================

Main plugin class that registers systems management functionality.
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
    
    Configuration:
        - systems_rdn: Base RDN for systems entries
        - default_system_type: Default type for new systems
        - validate_ip_addresses: Enable IP address validation
        - validate_mac_addresses: Enable MAC address validation
        - require_unique_hostname: Enforce unique hostnames
        - require_unique_ip: Enforce unique IP addresses
        - require_unique_mac: Enforce unique MAC addresses
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
        systems_rdn = self.get_config_value("systems_rdn", "ou=systems")
        self.logger.info(f"Systems plugin activated (systems RDN: {systems_rdn})")
    
    def on_deactivate(self) -> None:
        """Called when plugin is deactivated."""
        self.logger.info("Systems plugin deactivated")
    
    @staticmethod
    def config_schema() -> List[ConfigSection]:
        """
        Define configuration schema for Systems plugin.
        
        Returns:
            List of configuration sections with fields.
        """
        return [
            ConfigSection(
                id="general",
                label="General Settings",
                description="Basic systems plugin configuration",
                fields=[
                    ConfigField(
                        key="systems_rdn",
                        label="Systems RDN",
                        description="Base RDN for system entries in LDAP",
                        field_type=ConfigFieldType.STRING,
                        default_value="ou=systems",
                        required=True,
                        requires_restart=True,
                        validation=ConfigFieldValidation(
                            pattern=r"^[a-z]+=.+$",
                        ),
                    ),
                    ConfigField(
                        key="default_system_type",
                        label="Default System Type",
                        description="Default type when creating new systems",
                        field_type=ConfigFieldType.SELECT,
                        default_value="server",
                        options=[
                            ConfigFieldOption(value="server", label="Server"),
                            ConfigFieldOption(value="workstation", label="Workstation"),
                            ConfigFieldOption(value="terminal", label="Terminal"),
                            ConfigFieldOption(value="printer", label="Printer"),
                            ConfigFieldOption(value="component", label="Component"),
                            ConfigFieldOption(value="phone", label="Phone"),
                            ConfigFieldOption(value="mobile", label="Mobile Phone"),
                        ],
                    ),
                    ConfigField(
                        key="organize_by_type",
                        label="Organize By Type",
                        description="Create sub-OUs for each system type",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=True,
                    ),
                ],
            ),
            ConfigSection(
                id="validation",
                label="Validation",
                description="Input validation settings",
                fields=[
                    ConfigField(
                        key="validate_ip_addresses",
                        label="Validate IP Addresses",
                        description="Validate IP address format (IPv4/IPv6)",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=True,
                    ),
                    ConfigField(
                        key="validate_mac_addresses",
                        label="Validate MAC Addresses",
                        description="Validate MAC address format",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=True,
                    ),
                    ConfigField(
                        key="validate_hostnames",
                        label="Validate Hostnames",
                        description="Validate hostname format (RFC 1123)",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=True,
                    ),
                ],
            ),
            ConfigSection(
                id="uniqueness",
                label="Uniqueness Constraints",
                description="Enforce unique values across systems",
                fields=[
                    ConfigField(
                        key="require_unique_hostname",
                        label="Unique Hostnames",
                        description="Require unique hostnames across all systems",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=True,
                    ),
                    ConfigField(
                        key="require_unique_ip",
                        label="Unique IP Addresses",
                        description="Require unique IP addresses across all systems",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=False,
                    ),
                    ConfigField(
                        key="require_unique_mac",
                        label="Unique MAC Addresses",
                        description="Require unique MAC addresses across all systems",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=True,
                    ),
                ],
            ),
            ConfigSection(
                id="defaults",
                label="Default Values",
                description="Default values for new systems",
                fields=[
                    ConfigField(
                        key="default_location",
                        label="Default Location",
                        description="Default physical location for new systems",
                        field_type=ConfigFieldType.STRING,
                        default_value="",
                    ),
                    ConfigField(
                        key="default_description_template",
                        label="Description Template",
                        description="Default description template ({type}, {hostname} available)",
                        field_type=ConfigFieldType.STRING,
                        default_value="{type}: {hostname}",
                    ),
                ],
            ),
            ConfigSection(
                id="network",
                label="Network Settings",
                description="Network-related configuration",
                fields=[
                    ConfigField(
                        key="mac_address_format",
                        label="MAC Address Format",
                        description="Display format for MAC addresses",
                        field_type=ConfigFieldType.SELECT,
                        default_value="colon",
                        options=[
                            ConfigFieldOption(value="colon", label="Colon-separated (AA:BB:CC:DD:EE:FF)"),
                            ConfigFieldOption(value="hyphen", label="Hyphen-separated (AA-BB-CC-DD-EE-FF)"),
                            ConfigFieldOption(value="dot", label="Dot-separated (AABB.CCDD.EEFF)"),
                            ConfigFieldOption(value="plain", label="No separator (AABBCCDDEEFF)"),
                        ],
                    ),
                    ConfigField(
                        key="allow_ipv6",
                        label="Allow IPv6",
                        description="Allow IPv6 addresses for systems",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=True,
                    ),
                    ConfigField(
                        key="allow_multiple_ips",
                        label="Allow Multiple IPs",
                        description="Allow multiple IP addresses per system",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=True,
                    ),
                    ConfigField(
                        key="allow_multiple_macs",
                        label="Allow Multiple MACs",
                        description="Allow multiple MAC addresses per system",
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
            "systems_rdn": "ou=systems",
            "default_system_type": "server",
            "organize_by_type": True,
            # Validation
            "validate_ip_addresses": True,
            "validate_mac_addresses": True,
            "validate_hostnames": True,
            # Uniqueness
            "require_unique_hostname": True,
            "require_unique_ip": False,
            "require_unique_mac": True,
            # Defaults
            "default_location": "",
            "default_description_template": "{type}: {hostname}",
            # Network
            "mac_address_format": "colon",
            "allow_ipv6": True,
            "allow_multiple_ips": True,
            "allow_multiple_macs": True,
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
        # Validate description template
        template = config.get("default_description_template", "")
        if template and "{" in template:
            # Check for valid placeholders
            valid_placeholders = ["{type}", "{hostname}", "{cn}"]
            # Extract placeholders from template
            import re
            placeholders = re.findall(r"\{[^}]+\}", template)
            for placeholder in placeholders:
                if placeholder not in valid_placeholders:
                    return f"Invalid placeholder in description template: {placeholder}"
        
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
        self.logger.info(f"Systems plugin configuration updated: {changed_keys}")
        
        # Log significant changes
        if "systems_rdn" in changed_keys:
            self.logger.warning(
                f"Systems RDN changed: {new_config.get('systems_rdn')} - may require restart"
            )
        
        if "organize_by_type" in changed_keys:
            self.logger.info(
                f"Organization structure changed: organize_by_type = {new_config.get('organize_by_type')}"
            )

    @staticmethod
    def routes() -> List[Any]:
        """Return API routers for systems endpoints."""
        return [router]
