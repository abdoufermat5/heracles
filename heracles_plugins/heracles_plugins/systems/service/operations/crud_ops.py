"""
CRUD Operations
===============

Create, Read, Update, Delete operations for systems.
"""

from typing import Any, Optional, TYPE_CHECKING

import structlog

from heracles_api.services.ldap_service import LdapOperationError, LdapNotFoundError

if TYPE_CHECKING:
    from ..base import SystemServiceBase

from ...schemas import (
    SystemType,
    SystemCreate,
    SystemRead,
    SystemUpdate,
    SystemListResponse,
)
from ..constants import TYPE_OBJECT_CLASSES, get_all_attributes
from ..utils import detect_system_type
from ..base import SystemValidationError


logger = structlog.get_logger(__name__)


class CRUDOperationsMixin:
    """Mixin providing CRUD operations for systems."""
    
    # Type hints for mixin
    _ldap: Any
    _get_systems_container: Any
    _get_type_ou: Any
    _get_system_dn: Any
    _ensure_type_ou: Any
    validate_system: Any
    get_system: Any
    _entry_to_list_item: Any
    _entry_to_read: Any
    _build_create_attributes: Any
    _build_update_changes: Any
    
    async def list_systems(
        self: "SystemServiceBase",
        system_type: Optional[SystemType] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        base_dn: Optional[str] = None,
    ) -> SystemListResponse:
        """
        List systems with optional filtering.
        
        Args:
            system_type: Filter by system type (None = all types)
            search: Search in cn, description, ipHostNumber
            page: Page number (1-indexed)
            page_size: Items per page
            
        Returns:
            SystemListResponse with paginated results
        """
        # Build search filter
        filters = []
        
        if system_type:
            obj_class = SystemType.get_object_class(system_type)
            filters.append(f"(objectClass={obj_class})")
        else:
            # Match any of our system types
            type_filters = [
                f"(objectClass={SystemType.get_object_class(t)})"
                for t in SystemType
            ]
            filters.append(f"(|{''.join(type_filters)})")
        
        if search:
            escaped_search = self._ldap._escape_filter(search)
            search_filter = f"(|(cn=*{escaped_search}*)(description=*{escaped_search}*)(ipHostNumber=*{escaped_search}*))"
            filters.append(search_filter)
        
        combined_filter = f"(&{''.join(filters)})" if len(filters) > 1 else filters[0]
        
        try:
            # Get the systems container for the given context
            # Search within specific type OU if type provided
            if system_type:
                search_base = self._get_type_ou(system_type, base_dn)
            else:
                search_base = self._get_systems_container(base_dn)
            
            entries = await self._ldap.search(
                search_base=search_base,
                search_filter=combined_filter,
                attributes=get_all_attributes(),
            )
            
            # Convert to list items
            systems = [self._entry_to_list_item(entry) for entry in entries]
            
            # Sort by cn
            systems.sort(key=lambda s: s.cn)
            
            # Pagination
            total = len(systems)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_systems = systems[start_idx:end_idx]
            
            return SystemListResponse(
                systems=paginated_systems,
                total=total,
                page=page,
                page_size=page_size,
                has_more=end_idx < total,
            )
            
        except LdapOperationError as e:
            logger.error("systems_list_failed", error=str(e))
            raise
    
    async def get_system(
        self: "SystemServiceBase", 
        cn: str, 
        system_type: SystemType,
        base_dn: Optional[str] = None
    ) -> Optional[SystemRead]:
        """
        Get a single system by CN and type.
        
        If base_dn is provided, looks within that context's systems container.
        Otherwise uses the default systems container.
        """
        dn = self._get_system_dn(cn, system_type, base_dn)
        
        try:
            entry = await self._ldap.get_by_dn(
                dn, 
                attributes=get_all_attributes()
            )
            if entry is None:
                return None
            return self._entry_to_read(entry, system_type)
        except LdapOperationError:
            return None
    
    async def get_system_by_dn(self: "SystemServiceBase", dn: str) -> Optional[SystemRead]:
        """Get a system by its DN (auto-detect type)."""
        try:
            entry = await self._ldap.get_by_dn(
                dn, 
                attributes=get_all_attributes()
            )
            if entry is None:
                return None
            
            # Detect type from objectClass
            system_type = detect_system_type(entry)
            if system_type is None:
                return None
            
            return self._entry_to_read(entry, system_type)
        except LdapOperationError:
            return None
    
    async def create_system(
        self: "SystemServiceBase", 
        data: SystemCreate,
        base_dn: Optional[str] = None
    ) -> SystemRead:
        """
        Create a new system.
        
        If base_dn is provided, creates in that department's systems container.
        Otherwise creates it in the default systems container.
        """
        
        # Check if system already exists
        existing = await self.get_system(data.cn, data.system_type, base_dn=base_dn)
        if existing:
            raise SystemValidationError(
                f"System '{data.cn}' of type '{data.system_type.value}' already exists"
            )
        
        # Validate against config-based rules (uniqueness checks)
        validation_errors = await self.validate_system(data, base_dn=base_dn)
        if validation_errors:
            raise SystemValidationError("; ".join(validation_errors))
        
        # Get the DN for the new system
        dn = self._get_system_dn(data.cn, data.system_type, base_dn)
        
        # Ensure OU exists (only for root context)
        if not base_dn:
            await self._ensure_type_ou(data.system_type)
        
        # Get object classes for this type
        object_classes = TYPE_OBJECT_CLASSES[data.system_type].copy()
        
        # Build attributes
        attributes = self._build_create_attributes(data)
        
        try:
            await self._ldap.add(
                dn=dn,
                object_classes=object_classes,
                attributes=attributes,
            )
            
            logger.info(
                "system_created", 
                cn=data.cn, 
                type=data.system_type.value,
                dn=dn,
                context="custom" if base_dn else "default"
            )
            
            # Read back and return
            # Pass base_dn to finding it again
            return await self.get_system(data.cn, data.system_type, base_dn=base_dn)
            
        except LdapOperationError as e:
            logger.error(
                "system_create_failed", 
                cn=data.cn, 
                type=data.system_type.value,
                error=str(e)
            )
            raise SystemValidationError(f"Failed to create system: {e}")
    
    async def update_system(
        self: "SystemServiceBase", 
        cn: str, 
        system_type: SystemType, 
        data: SystemUpdate,
        base_dn: Optional[str] = None
    ) -> SystemRead:
        """Update an existing system."""
        
        # Check exists and get current DN
        existing = await self.get_system(cn, system_type, base_dn=base_dn)
        if not existing:
            raise LdapNotFoundError(f"System '{cn}' of type '{system_type.value}' not found")
            
        # Determine actual DN
        if base_dn:
            # Search to get DN
            object_class = SystemType.get_object_class(system_type)
            search_filter = f"(&(cn={cn})(objectClass={object_class}))"
            entries = await self._ldap.search(base_dn, search_filter, attributes=["cn"])
            if not entries:
                raise LdapNotFoundError(f"System '{cn}' not found in {base_dn}")
            dn = entries[0].dn
        else:
            dn = self._get_system_dn(cn, system_type)
        
        # Build changes
        changes = self._build_update_changes(data, system_type)
        
        if changes:
            try:
                await self._ldap.modify(dn, changes)
                logger.info(
                    "system_updated", 
                    cn=cn, 
                    type=system_type.value,
                    changes=len(changes)
                )
            except LdapOperationError as e:
                logger.error(
                    "system_update_failed", 
                    cn=cn, 
                    type=system_type.value,
                    error=str(e)
                )
                raise SystemValidationError(f"Failed to update system: {e}")
        
        return await self.get_system(cn, system_type, base_dn=base_dn)
    
    async def delete_system(
        self: "SystemServiceBase", 
        cn: str, 
        system_type: SystemType,
        base_dn: Optional[str] = None
    ) -> None:
        """Delete a system."""
        
        # Check exists and get DN
        existing = await self.get_system(cn, system_type, base_dn=base_dn)
        if not existing:
            raise LdapNotFoundError(f"System '{cn}' of type '{system_type.value}' not found")

        if base_dn:
            # Search to get DN
            object_class = SystemType.get_object_class(system_type)
            search_filter = f"(&(cn={cn})(objectClass={object_class}))"
            entries = await self._ldap.search(base_dn, search_filter, attributes=["cn"])
            if not entries:
                raise LdapNotFoundError(f"System '{cn}' not found in {base_dn}")
            dn = entries[0].dn
        else:
            dn = self._get_system_dn(cn, system_type)
        
        try:
            await self._ldap.delete(dn)
            logger.info(
                "system_deleted", 
                cn=cn, 
                type=system_type.value,
                dn=dn
            )
        except LdapOperationError as e:
            logger.error(
                "system_delete_failed", 
                cn=cn, 
                type=system_type.value,
                error=str(e)
            )
            raise SystemValidationError(f"Failed to delete system: {e}")
