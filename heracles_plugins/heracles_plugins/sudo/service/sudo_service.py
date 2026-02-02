"""
Sudo Service
============

Business logic for sudo role management.
Handles LDAP operations for sudoRole entries.
"""

from typing import Any, Dict, Optional

import structlog

from heracles_api.plugins.base import TabService
from heracles_api.services.ldap_service import LdapService, LdapOperationError

from ..schemas import SudoRoleCreate, SudoRoleRead, SudoRoleUpdate
from .base import MANAGED_ATTRIBUTES
from .operations import (
    ConfigOperationsMixin,
    ValidationOperationsMixin,
    HelperOperationsMixin,
    CrudOperationsMixin,
    QueryOperationsMixin,
)

logger = structlog.get_logger(__name__)


class SudoService(
    ConfigOperationsMixin,
    ValidationOperationsMixin,
    HelperOperationsMixin,
    CrudOperationsMixin,
    QueryOperationsMixin,
    TabService,
):
    """
    Service for managing sudo roles.
    
    Handles:
    - sudoRole objectClass
    - CRUD operations for sudo rules
    - Time-based validity checking
    """

    def __init__(self, ldap_service: LdapService, config: Dict[str, Any]):
        super().__init__(ldap_service, config)
        
        # Configuration (cached for fallback)
        self._sudoers_rdn = config.get("sudoers_rdn", "ou=sudoers")
        self._base_dn = config.get("base_dn", ldap_service.base_dn)
        self._sudoers_dn = f"{self._sudoers_rdn},{self._base_dn}"

    # ========================================================================
    # TabService Interface (for user tab, if needed)
    # ========================================================================

    async def is_active(self, dn: str) -> bool:
        """Not used for sudo - it's a standalone object type."""
        return False

    async def read(self, dn: str) -> Optional[SudoRoleRead]:
        """Read sudo role by DN."""
        try:
            entry = await self._ldap.get_by_dn(dn, attributes=MANAGED_ATTRIBUTES)
            if entry is None:
                return None
            return self._entry_to_read(entry)
        except LdapOperationError:
            return None

    async def activate(self, dn: str, data: SudoRoleCreate) -> SudoRoleRead:
        """Not applicable for sudo roles."""
        raise NotImplementedError("Use create_role() instead")

    async def deactivate(self, dn: str) -> bool:
        """Not applicable for sudo roles."""
        raise NotImplementedError("Use delete_role() instead")

    async def update(self, dn: str, data: SudoRoleUpdate) -> SudoRoleRead:
        """Update sudo role by DN."""
        # Extract CN from DN
        cn = dn.split(",")[0].split("=")[1]
        return await self.update_role(cn, data)
