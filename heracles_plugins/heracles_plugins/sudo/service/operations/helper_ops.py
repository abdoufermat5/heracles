"""
Sudo Helper Operations Mixin
============================

Helper methods for LDAP entry conversion and attribute handling.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

import structlog

from heracles_api.services.ldap_service import LdapEntry

from ..base import (
    parse_generalized_time,
    datetime_to_generalized,
    is_time_valid,
)
from ...schemas import SudoRoleCreate, SudoRoleRead

logger = structlog.get_logger(__name__)


class HelperOperationsMixin:
    """Mixin providing sudo helper operations."""

    async def _ensure_sudoers_ou(self) -> None:
        """Ensure the sudoers OU exists."""
        sudoers_dn = await self._get_sudoers_container()
        sudoers_rdn = await self._get_sudoers_rdn()
        # Extract the ou value from the rdn (e.g., "ou=sudoers5" -> "sudoers5")
        ou_value = sudoers_rdn.split("=", 1)[1] if "=" in sudoers_rdn else sudoers_rdn
        
        try:
            entry = await self._ldap.get_by_dn(sudoers_dn)
            if entry is None:
                await self._ldap.add(
                    dn=sudoers_dn,
                    object_classes=["organizationalUnit"],
                    attributes={"ou": ou_value},
                )
                logger.info("sudoers_ou_created", dn=sudoers_dn)
        except Exception:
            # Try to create it
            try:
                await self._ldap.add(
                    dn=sudoers_dn,
                    object_classes=["organizationalUnit"],
                    attributes={"ou": ou_value},
                )
                logger.info("sudoers_ou_created", dn=sudoers_dn)
            except Exception as e:
                logger.debug("sudoers_ou_exists_or_error", error=str(e))

    def _build_attributes(self, data: SudoRoleCreate) -> Dict[str, Any]:
        """Build LDAP attributes from create schema."""
        attrs = {"cn": data.cn}
        
        if data.description:
            attrs["description"] = data.description
        
        if data.sudo_user:
            attrs["sudoUser"] = data.sudo_user
        
        if data.sudo_host:
            attrs["sudoHost"] = data.sudo_host
        
        if data.sudo_command:
            attrs["sudoCommand"] = data.sudo_command
        
        if data.sudo_run_as_user:
            attrs["sudoRunAsUser"] = data.sudo_run_as_user
        
        if data.sudo_run_as_group:
            attrs["sudoRunAsGroup"] = data.sudo_run_as_group
        
        if data.sudo_option:
            attrs["sudoOption"] = data.sudo_option
        
        if data.sudo_order is not None:
            attrs["sudoOrder"] = str(data.sudo_order)
        
        if data.sudo_not_before:
            attrs["sudoNotBefore"] = datetime_to_generalized(data.sudo_not_before)
        
        if data.sudo_not_after:
            attrs["sudoNotAfter"] = datetime_to_generalized(data.sudo_not_after)
        
        return attrs

    def _entry_to_read(self, entry: LdapEntry) -> SudoRoleRead:
        """Convert LDAP entry to read schema."""
        cn = self._get_first(entry, "cn", "")
        
        # Parse time constraints
        not_before = parse_generalized_time(self._get_first(entry, "sudoNotBefore"))
        not_after = parse_generalized_time(self._get_first(entry, "sudoNotAfter"))
        
        # Check if currently valid
        is_valid = is_time_valid(not_before, not_after)
        
        return SudoRoleRead(
            dn=entry.dn,
            cn=cn,
            description=self._get_first(entry, "description"),
            sudoUser=self._get_list(entry, "sudoUser"),
            sudoHost=self._get_list(entry, "sudoHost") or ["ALL"],
            sudoCommand=self._get_list(entry, "sudoCommand"),
            sudoRunAsUser=self._get_list(entry, "sudoRunAsUser") or ["ALL"],
            sudoRunAsGroup=self._get_list(entry, "sudoRunAsGroup"),
            sudoOption=self._get_list(entry, "sudoOption"),
            sudoOrder=self._get_int(entry, "sudoOrder", 0),
            sudoNotBefore=not_before,
            sudoNotAfter=not_after,
            isDefault=cn.lower() == "defaults",
            isValid=is_valid,
        )

    def _get_first(self, entry: LdapEntry, attr: str, default: Any = None) -> Any:
        """Get first value of an attribute."""
        val = entry.get(attr)
        if val is None:
            return default
        if isinstance(val, list):
            return val[0] if val else default
        return val

    def _get_list(self, entry: LdapEntry, attr: str) -> List[str]:
        """Get attribute as list."""
        val = entry.get(attr)
        if val is None:
            return []
        if isinstance(val, str):
            return [val]
        return list(val)

    def _get_int(self, entry: LdapEntry, attr: str, default: int = 0) -> int:
        """Get attribute as integer."""
        val = self._get_first(entry, attr)
        if val is None:
            return default
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    def _is_role_valid(self, role: SudoRoleRead, now: datetime = None) -> bool:
        """Check if a role is currently valid based on time constraints."""
        if now is None:
            now = datetime.now(timezone.utc)
        
        if role.sudo_not_before and now < role.sudo_not_before:
            return False
        if role.sudo_not_after and now > role.sudo_not_after:
            return False
        
        return True
