"""
Sudo Config Operations Mixin
============================

Configuration and validation config management.
"""

from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


class ConfigOperationsMixin:
    """Mixin providing sudo configuration operations."""

    async def _get_sudoers_rdn(self) -> str:
        """
        Get sudoers_rdn with hot-reload support.
        
        Reads from database config with fallback to init-time config.
        """
        try:
            from heracles_api.services.config import get_plugin_config_value
            return await get_plugin_config_value(
                "sudo",
                "sudoers_rdn",
                self._sudoers_rdn
            )
        except Exception as e:
            logger.warning("sudo_config_load_error", error=str(e), key="sudoers_rdn")
            return self._sudoers_rdn

    async def _get_sudoers_dn(self, base_dn: Optional[str] = None) -> str:
        """
        Get the sudoers container DN with hot-reload support.
        
        Args:
            base_dn: Optional base DN to use instead of default
            
        Returns:
            Full DN of sudoers container
        """
        sudoers_rdn = await self._get_sudoers_rdn()
        effective_base = base_dn or self._base_dn
        return f"{sudoers_rdn},{effective_base}"

    async def _get_sudoers_container(self, base_dn: Optional[str] = None) -> str:
        """Get the sudoers container DN for the given context.
        
        If base_dn is provided (department context), returns {sudoers_rdn},{base_dn}.
        Otherwise returns the default {sudoers_rdn},{root_base_dn}.
        
        Uses hot-reload support to get current config value.
        """
        sudoers_rdn = await self._get_sudoers_rdn()
        if base_dn:
            return f"{sudoers_rdn},{base_dn}"
        return f"{sudoers_rdn},{self._base_dn}"

    async def _get_role_dn(self, cn: str, base_dn: Optional[str] = None) -> str:
        """Get the DN for a sudo role."""
        container = await self._get_sudoers_container(base_dn)
        return f"cn={cn},{container}"
