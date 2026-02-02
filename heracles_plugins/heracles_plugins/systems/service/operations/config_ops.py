"""
Config Operations
=================

Configuration and DN management operations.
"""

from typing import Any, Dict, Optional, TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from ..base import SystemServiceBase

from ...schemas import SystemType


logger = structlog.get_logger(__name__)


class ConfigOperationsMixin:
    """Mixin providing configuration and DN management methods."""
    
    # Type hints for mixin (actual attributes come from SystemServiceBase)
    _systems_rdn: str
    _base_dn: str
    _systems_dn: str
    _config: Dict[str, Any]
    
    async def _get_validation_config(self: "SystemServiceBase") -> Dict[str, Any]:
        """
        Get systems validation config with hot-reload support.
        
        Reads from database config with fallback to init-time config.
        """
        try:
            from heracles_api.services.config import get_plugin_config_value
            
            validate_ip = await get_plugin_config_value(
                "systems",
                "validate_ip_addresses",
                self._config.get("validate_ip_addresses", True)
            )
            validate_mac = await get_plugin_config_value(
                "systems",
                "validate_mac_addresses",
                self._config.get("validate_mac_addresses", True)
            )
            require_unique_hostname = await get_plugin_config_value(
                "systems",
                "require_unique_hostname",
                self._config.get("require_unique_hostname", True)
            )
            require_unique_ip = await get_plugin_config_value(
                "systems",
                "require_unique_ip",
                self._config.get("require_unique_ip", False)
            )
            require_unique_mac = await get_plugin_config_value(
                "systems",
                "require_unique_mac",
                self._config.get("require_unique_mac", True)
            )
            
            return {
                "validate_ip_addresses": validate_ip,
                "validate_mac_addresses": validate_mac,
                "require_unique_hostname": require_unique_hostname,
                "require_unique_ip": require_unique_ip,
                "require_unique_mac": require_unique_mac,
            }
            
        except Exception as e:
            logger.warning("systems_config_load_error", error=str(e))
            return {
                "validate_ip_addresses": self._config.get("validate_ip_addresses", True),
                "validate_mac_addresses": self._config.get("validate_mac_addresses", True),
                "require_unique_hostname": self._config.get("require_unique_hostname", True),
                "require_unique_ip": self._config.get("require_unique_ip", False),
                "require_unique_mac": self._config.get("require_unique_mac", True),
            }

    def _get_systems_container(self: "SystemServiceBase", base_dn: Optional[str] = None) -> str:
        """Get the systems container DN for the given context.
        
        If base_dn is provided (department context), returns ou=systems,{base_dn}.
        Otherwise returns the default ou=systems,{root_base_dn}.
        """
        if base_dn:
            return f"{self._systems_rdn},{base_dn}"
        return self._systems_dn
    
    def _get_type_ou(self: "SystemServiceBase", system_type: SystemType, base_dn: Optional[str] = None) -> str:
        """Get the OU DN for a system type within the given context."""
        rdn = SystemType.get_rdn(system_type)
        container = self._get_systems_container(base_dn)
        return f"{rdn},{container}"
    
    def _get_system_dn(self: "SystemServiceBase", cn: str, system_type: SystemType, base_dn: Optional[str] = None) -> str:
        """Get the DN for a system within the given context."""
        ou_dn = self._get_type_ou(system_type, base_dn)
        return f"cn={cn},{ou_dn}"
