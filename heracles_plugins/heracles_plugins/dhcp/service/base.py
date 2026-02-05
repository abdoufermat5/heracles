"""
DHCP Service Base
=================

Base class and common functionality for DHCP operations.
"""

from typing import Any, Dict, List, Optional

import structlog

from heracles_api.services.ldap_service import (
    LdapService,
    LdapOperationError,
)

logger = structlog.get_logger(__name__)


class DhcpValidationError(Exception):
    """Raised when DHCP validation fails."""
    pass


class DhcpServiceBase:
    """
    Base class for DHCP service operations.
    
    Provides common functionality like DN building and OU management.
    """

    def __init__(self, ldap_service: LdapService, config: Dict[str, Any]):
        self._ldap = ldap_service
        self._config = config
        
        # Configuration
        self._dhcp_rdn = config.get("dhcp_rdn", "ou=dhcp")
        self._base_dn = config.get("base_dn", ldap_service.base_dn)
        self._dhcp_dn = f"{self._dhcp_rdn},{self._base_dn}"
        
        # Systems plugin integration (optional)
        self._systems_service = None

    def get_dhcp_dn(self) -> str:
        """Get the DHCP container DN (e.g. ou=dhcp,dc=heracles,dc=local)."""
        return self._dhcp_dn

    def reload_config(self, config: Dict[str, Any]) -> None:
        """
        Reload configuration values.
        
        Called when configuration changes to update internal state.
        """
        old_dhcp_rdn = self._dhcp_rdn
        self._dhcp_rdn = config.get("dhcp_rdn", "ou=dhcp")
        self._base_dn = config.get("base_dn", self._ldap.base_dn)
        self._dhcp_dn = f"{self._dhcp_rdn},{self._base_dn}"
        
        if old_dhcp_rdn != self._dhcp_rdn:
            logger.info(
                "dhcp_rdn_reloaded",
                old_rdn=old_dhcp_rdn,
                new_rdn=self._dhcp_rdn,
            )
    
    def set_systems_service(self, systems_service: Any) -> None:
        """Set the systems service for host validation integration."""
        self._systems_service = systems_service
    
    def _get_dhcp_container(self, base_dn: Optional[str] = None) -> str:
        """Get the DHCP container DN for the given context.
        
        If base_dn is provided (department context), returns ou=dhcp,{base_dn}.
        Otherwise returns the default ou=dhcp,{root_base_dn}.
        """
        if base_dn:
            return f"{self._dhcp_rdn},{base_dn}"
        return self._dhcp_dn
    
    def _get_service_dn(self, service_cn: str, base_dn: Optional[str] = None) -> str:
        """Get the DN for a DHCP service."""
        if base_dn:
            return f"cn={service_cn},{self._dhcp_rdn},{base_dn}"
        return f"cn={service_cn},{self._dhcp_dn}"
    
    def _get_object_dn(self, cn: str, parent_dn: str) -> str:
        """Get the DN for a DHCP object under a parent."""
        return f"cn={cn},{parent_dn}"
    
    def _get_parent_dn(self, dn: str) -> str:
        """Extract parent DN from an object DN."""
        parts = dn.split(",", 1)
        if len(parts) > 1:
            return parts[1]
        return self._dhcp_dn

    async def _ensure_dhcp_ou(self, base_dn: Optional[str] = None) -> None:
        """Ensure the DHCP OU exists."""
        if base_dn:
            dn = f"{self._dhcp_rdn},{base_dn}"
        else:
            dn = self._dhcp_dn
            
        try:
            exists = await self._ldap.get_by_dn(
               dn, 
                attributes=["ou"]
            )
            if exists is None:
                await self._ldap.add(
                    dn=dn,
                    object_classes=["organizationalUnit"],
                    attributes={"ou": ["dhcp"]},
                )
                logger.info("dhcp_ou_created", dn=dn)
        except LdapOperationError as e:
            logger.warning("dhcp_ou_check_failed", error=str(e))
    
    async def _delete_children_recursive(self, parent_dn: str) -> None:
        """Recursively delete all children of a DN."""
        # Find all direct children
        entries = await self._ldap.search(
            search_base=parent_dn,
            search_filter="(objectClass=*)",
            attributes=["dn"],
            scope="onelevel",
        )
        
        # Delete each child recursively
        for entry in entries:
            child_dn = entry.dn
            if child_dn and child_dn != parent_dn:
                await self._delete_children_recursive(child_dn)
                await self._ldap.delete(child_dn)
