"""
Sudo CRUD Operations Mixin
==========================

Create, Read, Update, Delete operations for sudo roles.
"""

from datetime import datetime, timezone
from typing import Optional

import structlog

from heracles_api.services.ldap_service import LdapOperationError, LdapNotFoundError

from ..base import (
    OBJECT_CLASSES,
    MANAGED_ATTRIBUTES,
    SudoValidationError,
    datetime_to_generalized,
)
from ...schemas import (
    SudoRoleCreate,
    SudoRoleRead,
    SudoRoleUpdate,
    SudoRoleListResponse,
)

logger = structlog.get_logger(__name__)


class CrudOperationsMixin:
    """Mixin providing sudo CRUD operations."""

    async def list_roles(
        self,
        search: Optional[str] = None,
        base_dn: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> SudoRoleListResponse:
        """List all sudo roles with optional filtering."""
        
        # Get the sudoers container for the given context
        search_base = await self._get_sudoers_container(base_dn)
        if search:
            escaped_search = self._ldap._escape_filter(search)
            search_filter = f"(&(objectClass=sudoRole)(|(cn=*{escaped_search}*)(description=*{escaped_search}*)(sudoUser=*{escaped_search}*)))"
        else:
            search_filter = "(objectClass=sudoRole)"
        
        try:
            entries = await self._ldap.search(
                search_base=search_base,
                search_filter=search_filter,
                attributes=MANAGED_ATTRIBUTES,
            )
            
            # Convert to schema objects
            roles = [self._entry_to_read(entry) for entry in entries]
            
            # Sort by order, then by cn
            roles.sort(key=lambda r: (r.sudo_order or 0, r.cn))
            
            # Pagination
            total = len(roles)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_roles = roles[start_idx:end_idx]
            
            return SudoRoleListResponse(
                roles=paginated_roles,
                total=total,
                page=page,
                page_size=page_size,
                has_more=end_idx < total,
            )
            
        except LdapOperationError as e:
            logger.error("sudo_list_failed", error=str(e))
            raise

    async def get_role(
        self, 
        cn: str,
        base_dn: Optional[str] = None
    ) -> Optional[SudoRoleRead]:
        """Get a single sudo role by CN."""
        dn = await self._get_role_dn(cn, base_dn)
        
        try:
            entry = await self._ldap.get_by_dn(dn, attributes=MANAGED_ATTRIBUTES)
            if entry is None:
                return None
            return self._entry_to_read(entry)
        except LdapOperationError:
            return None

    async def create_role(
        self, 
        data: SudoRoleCreate,
        base_dn: Optional[str] = None
    ) -> SudoRoleRead:
        """Create a new sudo role."""
        
        # Check if role already exists
        existing = await self.get_role(data.cn, base_dn=base_dn)
        if existing:
            raise SudoValidationError(f"Sudo role '{data.cn}' already exists")
        
        # Validate against config-based rules
        validation_errors = await self.validate_sudo_role(data)
        if validation_errors:
            raise SudoValidationError("; ".join(validation_errors))
        
        # Get the DN for the new role
        dn = await self._get_role_dn(data.cn, base_dn)
        
        # Ensure sudoers OU exists (only for root context)
        if not base_dn:
            await self._ensure_sudoers_ou()
        
        # Build attributes
        attributes = self._build_attributes(data)
        
        try:
            await self._ldap.add(
                dn=dn,
                object_classes=OBJECT_CLASSES,
                attributes=attributes,
            )
            
            logger.info("sudo_role_created", cn=data.cn, dn=dn)
            
            # Read back and return
            return await self.get_role(data.cn, base_dn=base_dn)
            
        except LdapOperationError as e:
            logger.error("sudo_role_create_failed", cn=data.cn, error=str(e))
            raise SudoValidationError(f"Failed to create sudo role: {e}")

    async def update_role(
        self, 
        cn: str, 
        data: SudoRoleUpdate,
        base_dn: Optional[str] = None
    ) -> SudoRoleRead:
        """Update an existing sudo role."""
        
        # Check if it's the defaults entry
        if cn.lower() == "defaults":
            # Only allow updating options for defaults
            if any([
                data.sudo_user is not None,
                data.sudo_host is not None,
                data.sudo_command is not None,
                data.sudo_run_as_user is not None,
                data.sudo_run_as_group is not None,
            ]):
                raise SudoValidationError(
                    "Cannot modify users/hosts/commands on the defaults entry"
                )
        
        # Check exists and get DN
        existing = await self.get_role(cn, base_dn=base_dn)
        if not existing:
            raise LdapNotFoundError(f"Sudo role '{cn}' not found")
            
        if base_dn:
             # Search to get DN
             search_filter = f"(&(cn={cn})(objectClass=sudoRole))"
             entries = await self._ldap.search(base_dn, search_filter, attributes=["cn"])
             if not entries:
                 raise LdapNotFoundError(f"Sudo role '{cn}' not found in {base_dn}")
             dn = entries[0].dn
        else:
            sudoers_dn = await self._get_sudoers_container()
            dn = f"cn={cn},{sudoers_dn}"
        
        # Build changes
        changes = {}
        
        if data.description is not None:
            if data.description:
                changes["description"] = ("replace", [data.description])
            else:
                changes["description"] = ("delete", [])
        
        if data.sudo_user is not None:
            if data.sudo_user:
                changes["sudoUser"] = ("replace", data.sudo_user)
            else:
                changes["sudoUser"] = ("delete", [])
        
        if data.sudo_host is not None:
            if data.sudo_host:
                changes["sudoHost"] = ("replace", data.sudo_host)
            else:
                changes["sudoHost"] = ("delete", [])
        
        if data.sudo_command is not None:
            if data.sudo_command:
                changes["sudoCommand"] = ("replace", data.sudo_command)
            else:
                changes["sudoCommand"] = ("delete", [])
        
        if data.sudo_run_as_user is not None:
            if data.sudo_run_as_user:
                changes["sudoRunAsUser"] = ("replace", data.sudo_run_as_user)
            else:
                changes["sudoRunAsUser"] = ("delete", [])
        
        if data.sudo_run_as_group is not None:
            if data.sudo_run_as_group:
                changes["sudoRunAsGroup"] = ("replace", data.sudo_run_as_group)
            else:
                changes["sudoRunAsGroup"] = ("delete", [])
        
        if data.sudo_option is not None:
            if data.sudo_option:
                changes["sudoOption"] = ("replace", data.sudo_option)
            else:
                changes["sudoOption"] = ("delete", [])
        
        if data.sudo_order is not None:
            changes["sudoOrder"] = ("replace", [str(data.sudo_order)])
        
        if data.sudo_not_before is not None:
            changes["sudoNotBefore"] = ("replace", [datetime_to_generalized(data.sudo_not_before)])
        elif data.sudo_not_before == "":
            changes["sudoNotBefore"] = ("delete", [])
        
        if data.sudo_not_after is not None:
            changes["sudoNotAfter"] = ("replace", [datetime_to_generalized(data.sudo_not_after)])
        elif data.sudo_not_after == "":
            changes["sudoNotAfter"] = ("delete", [])
        
        if changes:
            try:
                await self._ldap.modify(dn, changes)
                logger.info("sudo_role_updated", cn=cn)
            except LdapOperationError as e:
                logger.error("sudo_role_update_failed", cn=cn, error=str(e))
                raise SudoValidationError(f"Failed to update sudo role: {e}")
        
        return await self.get_role(cn, base_dn=base_dn)

    async def delete_role(
        self, 
        cn: str,
        base_dn: Optional[str] = None
    ) -> bool:
        """Delete a sudo role."""
        
        # Don't allow deleting defaults
        if cn.lower() == "defaults":
            raise SudoValidationError("Cannot delete the defaults entry")
        
        # Check exists and get DN
        existing = await self.get_role(cn, base_dn=base_dn)
        if not existing:
            raise LdapNotFoundError(f"Sudo role '{cn}' not found")

        if base_dn:
             # Search to get DN
             search_filter = f"(&(cn={cn})(objectClass=sudoRole))"
             entries = await self._ldap.search(base_dn, search_filter, attributes=["cn"])
             if not entries:
                 raise LdapNotFoundError(f"Sudo role '{cn}' not found in {base_dn}")
             dn = entries[0].dn
        else:
            sudoers_dn = await self._get_sudoers_container()
            dn = f"cn={cn},{sudoers_dn}"
        
        try:
            await self._ldap.delete(dn)
            logger.info("sudo_role_deleted", cn=cn)
            return True
        except LdapOperationError as e:
            logger.error("sudo_role_delete_failed", cn=cn, error=str(e))
            raise SudoValidationError(f"Failed to delete sudo role: {e}")
