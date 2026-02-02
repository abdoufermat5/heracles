"""
OU Operations
=============

Organizational Unit management for systems hierarchy.
"""

from typing import Any, TYPE_CHECKING

import structlog

from heracles_api.services.ldap_service import LdapOperationError

if TYPE_CHECKING:
    from ..base import SystemServiceBase

from ...schemas import SystemType


logger = structlog.get_logger(__name__)


class OUOperationsMixin:
    """Mixin providing OU management methods."""
    
    # Type hints for mixin
    _ldap: Any
    _systems_dn: str
    _get_type_ou: Any
    
    async def _ensure_systems_ou(self: "SystemServiceBase") -> None:
        """Ensure the systems OU exists."""
        try:
            exists = await self._ldap.get_by_dn(
                self._systems_dn, 
                attributes=["ou"]
            )
            if exists is None:
                await self._ldap.add(
                    dn=self._systems_dn,
                    object_classes=["organizationalUnit"],
                    attributes={"ou": ["systems"]},
                )
                logger.info("systems_ou_created", dn=self._systems_dn)
        except LdapOperationError as e:
            logger.warning("systems_ou_check_failed", error=str(e))
    
    async def _ensure_type_ou(self: "SystemServiceBase", system_type: SystemType) -> None:
        """Ensure the OU for a specific system type exists."""
        await self._ensure_systems_ou()
        
        ou_dn = self._get_type_ou(system_type)
        ou_name = SystemType.get_rdn(system_type).replace("ou=", "")
        
        try:
            exists = await self._ldap.get_by_dn(ou_dn, attributes=["ou"])
            if exists is None:
                await self._ldap.add(
                    dn=ou_dn,
                    object_classes=["organizationalUnit"],
                    attributes={"ou": [ou_name]},
                )
                logger.info("system_type_ou_created", dn=ou_dn, type=system_type.value)
        except LdapOperationError as e:
            logger.warning("system_type_ou_check_failed", type=system_type.value, error=str(e))
