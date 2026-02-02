"""
DHCP Class and SubClass Operations
==================================

CRUD operations for dhcpClass and dhcpSubClass objects.
"""

from typing import Any, Dict, List, Optional

import structlog

from heracles_api.services.ldap_service import LdapNotFoundError

from ...schemas import (
    DhcpObjectType,
    DhcpClassCreate,
    DhcpClassUpdate,
    DhcpClassRead,
    DhcpClassListItem,
    DhcpClassListResponse,
    SubClassCreate,
    SubClassUpdate,
    SubClassRead,
)
from ..constants import (
    TYPE_OBJECT_CLASSES,
    COMMON_ATTRIBUTES,
    CLASS_ATTRIBUTES,
    SUBCLASS_ATTRIBUTES,
)
from ..utils import get_first_value
from ..base import DhcpServiceBase, DhcpValidationError

logger = structlog.get_logger(__name__)


class ClassOperationsMixin(DhcpServiceBase):
    """Mixin for DHCP Class and SubClass CRUD operations."""
    
    # ========================================================================
    # Class Operations
    # ========================================================================
    
    async def list_classes(
        self,
        parent_dn: str,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> DhcpClassListResponse:
        """List classes under a parent."""
        filters = ["(objectClass=dhcpClass)"]
        
        if search:
            filters.append(f"(|(cn=*{search}*)(dhcpComments=*{search}*))")
        
        ldap_filter = f"(&{''.join(filters)})"
        
        entries = await self._ldap.search(
            search_base=parent_dn,
            search_filter=ldap_filter,
            attributes=COMMON_ATTRIBUTES + CLASS_ATTRIBUTES,
            scope="subtree",
        )
        
        items = [
            DhcpClassListItem(
                dn=entry.dn,
                cn=get_first_value(entry, "cn", ""),
                dhcpComments=entry.get("dhcpComments", [None])[0],
            )
            for entry in entries
        ]
        
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        
        return DhcpClassListResponse(
            items=items[start:end],
            total=total,
            page=page,
            page_size=page_size,
        )
    
    async def get_class(self, dn: str) -> DhcpClassRead:
        """Get a class by DN."""
        entry = await self._ldap.get_by_dn(
            dn,
            attributes=COMMON_ATTRIBUTES + CLASS_ATTRIBUTES,
        )
        
        if entry is None:
            raise LdapNotFoundError(f"Class not found: {dn}")
        
        return DhcpClassRead(
            dn=entry.dn or dn,
            cn=get_first_value(entry, "cn", ""),
            dhcpStatements=entry.get("dhcpStatements", []),
            dhcpOption=entry.get("dhcpOption", []),
            dhcpComments=entry.get("dhcpComments", [None])[0],
            parentDn=self._get_parent_dn(dn),
        )
    
    async def create_class(self, parent_dn: str, data: DhcpClassCreate) -> DhcpClassRead:
        """Create a new class."""
        dn = self._get_object_dn(data.cn, parent_dn)
        
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing:
            raise DhcpValidationError(f"Class already exists: {data.cn}")
        
        attributes: Dict[str, List[Any]] = {
            "cn": [data.cn],
        }
        
        if data.dhcp_statements:
            attributes["dhcpStatements"] = data.dhcp_statements
        if data.dhcp_options:
            attributes["dhcpOption"] = data.dhcp_options
        if data.comments:
            attributes["dhcpComments"] = [data.comments]
        
        await self._ldap.add(
            dn=dn,
            object_classes=TYPE_OBJECT_CLASSES[DhcpObjectType.CLASS],
            attributes=attributes,
        )
        
        logger.info("dhcp_class_created", cn=data.cn, dn=dn)
        
        return await self.get_class(dn)
    
    async def update_class(self, dn: str, data: DhcpClassUpdate) -> DhcpClassRead:
        """Update a class."""
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing is None:
            raise LdapNotFoundError(f"Class not found: {dn}")
        
        modifications: Dict[str, List[Any]] = {}
        
        if data.dhcp_statements is not None:
            modifications["dhcpStatements"] = data.dhcp_statements
        if data.dhcp_options is not None:
            modifications["dhcpOption"] = data.dhcp_options
        if data.comments is not None:
            modifications["dhcpComments"] = [data.comments] if data.comments else []
        
        if modifications:
            await self._ldap.modify(dn, modifications)
            logger.info("dhcp_class_updated", dn=dn)
        
        return await self.get_class(dn)
    
    async def delete_class(self, dn: str, recursive: bool = False) -> None:
        """Delete a class."""
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing is None:
            raise LdapNotFoundError(f"Class not found: {dn}")
        
        if recursive:
            await self._delete_children_recursive(dn)
        
        await self._ldap.delete(dn)
        logger.info("dhcp_class_deleted", dn=dn)
    
    # ========================================================================
    # SubClass Operations
    # ========================================================================
    
    async def get_subclass(self, dn: str) -> SubClassRead:
        """Get a subclass by DN."""
        entry = await self._ldap.get_by_dn(
            dn,
            attributes=COMMON_ATTRIBUTES + SUBCLASS_ATTRIBUTES,
        )
        
        if entry is None:
            raise LdapNotFoundError(f"SubClass not found: {dn}")
        
        return SubClassRead(
            dn=entry.dn or dn,
            cn=get_first_value(entry, "cn", ""),
            dhcpClassData=entry.get("dhcpClassData", [None])[0],
            dhcpStatements=entry.get("dhcpStatements", []),
            dhcpOption=entry.get("dhcpOption", []),
            dhcpComments=entry.get("dhcpComments", [None])[0],
            parentDn=self._get_parent_dn(dn),
        )
    
    async def create_subclass(self, parent_dn: str, data: SubClassCreate) -> SubClassRead:
        """Create a new subclass under a class."""
        dn = self._get_object_dn(data.cn, parent_dn)
        
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing:
            raise DhcpValidationError(f"SubClass already exists: {data.cn}")
        
        attributes: Dict[str, List[Any]] = {
            "cn": [data.cn],
        }
        
        if data.dhcp_class_data:
            attributes["dhcpClassData"] = [data.dhcp_class_data]
        if data.dhcp_statements:
            attributes["dhcpStatements"] = data.dhcp_statements
        if data.dhcp_options:
            attributes["dhcpOption"] = data.dhcp_options
        if data.comments:
            attributes["dhcpComments"] = [data.comments]
        
        await self._ldap.add(
            dn=dn,
            object_classes=TYPE_OBJECT_CLASSES[DhcpObjectType.SUBCLASS],
            attributes=attributes,
        )
        
        logger.info("dhcp_subclass_created", cn=data.cn, dn=dn)
        
        return await self.get_subclass(dn)
    
    async def update_subclass(self, dn: str, data: SubClassUpdate) -> SubClassRead:
        """Update a subclass."""
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing is None:
            raise LdapNotFoundError(f"SubClass not found: {dn}")
        
        modifications: Dict[str, List[Any]] = {}
        
        if data.dhcp_class_data is not None:
            modifications["dhcpClassData"] = [data.dhcp_class_data] if data.dhcp_class_data else []
        if data.dhcp_statements is not None:
            modifications["dhcpStatements"] = data.dhcp_statements
        if data.dhcp_options is not None:
            modifications["dhcpOption"] = data.dhcp_options
        if data.comments is not None:
            modifications["dhcpComments"] = [data.comments] if data.comments else []
        
        if modifications:
            await self._ldap.modify(dn, modifications)
            logger.info("dhcp_subclass_updated", dn=dn)
        
        return await self.get_subclass(dn)
    
    async def delete_subclass(self, dn: str) -> None:
        """Delete a subclass."""
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing is None:
            raise LdapNotFoundError(f"SubClass not found: {dn}")
        
        await self._ldap.delete(dn)
        logger.info("dhcp_subclass_deleted", dn=dn)
