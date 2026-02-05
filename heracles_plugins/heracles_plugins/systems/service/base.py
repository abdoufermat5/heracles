"""
Systems Service Base
====================

Shared constants, exceptions, and base class for system operations.
"""

from typing import Any, Dict

import structlog

from heracles_api.plugins.base import TabService
from heracles_api.services.ldap_service import LdapService


logger = structlog.get_logger(__name__)


class SystemValidationError(Exception):
    """Raised when system validation fails."""
    pass


class SystemServiceBase(TabService):
    """
    Base class for SystemService providing common initialization.
    
    Handles configuration and DN management.
    """

    def __init__(self, ldap_service: LdapService, config: Dict[str, Any]):
        super().__init__(ldap_service, config)
        
        # Configuration
        self._systems_rdn = config.get("systems_rdn", "ou=systems")
        self._base_dn = config.get("base_dn", ldap_service.base_dn)
        self._systems_dn = f"{self._systems_rdn},{self._base_dn}"
    
    def get_systems_dn(self) -> str:
        """Get the base DN for systems container."""
        return self._systems_dn
