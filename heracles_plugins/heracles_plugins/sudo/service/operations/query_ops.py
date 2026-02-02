"""
Sudo Query Operations Mixin
===========================

User-centric and host-centric queries for sudo roles.
"""

from datetime import datetime, timezone
from typing import List, Optional

import structlog

from heracles_api.services.ldap_service import LdapOperationError

from ..base import MANAGED_ATTRIBUTES
from ...schemas import SudoRoleCreate, SudoRoleRead

logger = structlog.get_logger(__name__)


class QueryOperationsMixin:
    """Mixin providing sudo query operations."""

    async def get_defaults(self) -> Optional[SudoRoleRead]:
        """Get the sudo defaults entry."""
        return await self.get_role("defaults")

    async def create_defaults(self, options: List[str] = None) -> SudoRoleRead:
        """Create the sudo defaults entry if it doesn't exist."""
        existing = await self.get_defaults()
        if existing:
            return existing
        
        data = SudoRoleCreate(
            cn="defaults",
            description="Default sudo options",
            sudoOption=options or [],
        )
        return await self.create_role(data)

    async def get_roles_for_user(self, uid: str, groups: List[str] = None) -> List[SudoRoleRead]:
        """Get all sudo roles that apply to a specific user."""
        
        # Build filter for user, their groups, and ALL
        filters = [f"(sudoUser={self._ldap._escape_filter(uid)})"]
        filters.append("(sudoUser=ALL)")
        
        if groups:
            for group in groups:
                filters.append(f"(sudoUser=%{self._ldap._escape_filter(group)})")
        
        search_filter = f"(&(objectClass=sudoRole)(|{''.join(filters)}))"
        
        try:
            sudoers_dn = await self._get_sudoers_container()
            entries = await self._ldap.search(
                search_base=sudoers_dn,
                search_filter=search_filter,
                attributes=MANAGED_ATTRIBUTES,
            )
            
            roles = [self._entry_to_read(entry) for entry in entries]
            
            # Filter out invalid (time-constrained) roles
            now = datetime.now(timezone.utc)
            valid_roles = [r for r in roles if self._is_role_valid(r, now)]
            
            # Sort by order
            valid_roles.sort(key=lambda r: (r.sudo_order or 0, r.cn))
            
            return valid_roles
            
        except LdapOperationError as e:
            logger.error("sudo_get_user_roles_failed", uid=uid, error=str(e))
            return []

    async def get_roles_for_host(self, hostname: str) -> List[SudoRoleRead]:
        """Get all sudo roles that apply to a specific host."""
        
        search_filter = f"(&(objectClass=sudoRole)(|(sudoHost={self._ldap._escape_filter(hostname)})(sudoHost=ALL)))"
        
        try:
            sudoers_dn = await self._get_sudoers_container()
            entries = await self._ldap.search(
                search_base=sudoers_dn,
                search_filter=search_filter,
                attributes=MANAGED_ATTRIBUTES,
            )
            
            roles = [self._entry_to_read(entry) for entry in entries]
            roles.sort(key=lambda r: (r.sudo_order or 0, r.cn))
            
            return roles
            
        except LdapOperationError as e:
            logger.error("sudo_get_host_roles_failed", hostname=hostname, error=str(e))
            return []
