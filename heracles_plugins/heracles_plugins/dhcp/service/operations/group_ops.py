"""
DHCP Group Operations
=====================

CRUD operations for dhcpGroup objects.
"""

from typing import Any, Dict, List, Optional

import structlog

from heracles_api.services.ldap_service import LdapNotFoundError

from ...schemas import (
    DhcpObjectType,
    GroupCreate,
    GroupUpdate,
    GroupRead,
    GroupListItem,
    GroupListResponse,
)
from ..constants import (
    TYPE_OBJECT_CLASSES,
    COMMON_ATTRIBUTES,
    GROUP_ATTRIBUTES,
)
from ..utils import get_first_value
from ..base import DhcpServiceBase, DhcpValidationError

logger = structlog.get_logger(__name__)


class GroupOperationsMixin(DhcpServiceBase):
    """Mixin for DHCP Group CRUD operations."""
    
    async def list_groups(
        self,
        parent_dn: str,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> GroupListResponse:
        """List groups under a parent."""
        filters = ["(objectClass=dhcpGroup)"]
        
        if search:
            filters.append(f"(|(cn=*{search}*)(dhcpComments=*{search}*))")
        
        ldap_filter = f"(&{''.join(filters)})"
        
        entries = await self._ldap.search(
            search_base=parent_dn,
            search_filter=ldap_filter,
            attributes=COMMON_ATTRIBUTES + GROUP_ATTRIBUTES,
            scope="subtree",
        )
        
        items = [
            GroupListItem(
                dn=entry.dn,
                cn=get_first_value(entry, "cn", ""),
                dhcpComments=entry.get("dhcpComments", [None])[0],
            )
            for entry in entries
        ]
        
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        
        return GroupListResponse(
            items=items[start:end],
            total=total,
            page=page,
            page_size=page_size,
        )
    
    async def get_group(self, dn: str) -> GroupRead:
        """Get a group by DN."""
        entry = await self._ldap.get_by_dn(
            dn,
            attributes=COMMON_ATTRIBUTES + GROUP_ATTRIBUTES,
        )
        
        if entry is None:
            raise LdapNotFoundError(f"Group not found: {dn}")
        
        return GroupRead(
            dn=entry.dn or dn,
            cn=get_first_value(entry, "cn", ""),
            dhcpStatements=entry.get("dhcpStatements", []),
            dhcpOption=entry.get("dhcpOption", []),
            dhcpComments=entry.get("dhcpComments", [None])[0],
            parentDn=self._get_parent_dn(dn),
        )
    
    async def create_group(self, parent_dn: str, data: GroupCreate) -> GroupRead:
        """Create a new group."""
        dn = self._get_object_dn(data.cn, parent_dn)
        
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing:
            raise DhcpValidationError(f"Group already exists: {data.cn}")
        
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
            object_classes=TYPE_OBJECT_CLASSES[DhcpObjectType.GROUP],
            attributes=attributes,
        )
        
        logger.info("dhcp_group_created", cn=data.cn, dn=dn)
        
        return await self.get_group(dn)
    
    async def update_group(self, dn: str, data: GroupUpdate) -> GroupRead:
        """Update a group."""
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing is None:
            raise LdapNotFoundError(f"Group not found: {dn}")
        
        modifications: Dict[str, List[Any]] = {}
        
        if data.dhcp_statements is not None:
            modifications["dhcpStatements"] = data.dhcp_statements
        if data.dhcp_options is not None:
            modifications["dhcpOption"] = data.dhcp_options
        if data.comments is not None:
            modifications["dhcpComments"] = [data.comments] if data.comments else []
        
        if modifications:
            await self._ldap.modify(dn, modifications)
            logger.info("dhcp_group_updated", dn=dn)
        
        return await self.get_group(dn)
    
    async def delete_group(self, dn: str, recursive: bool = False) -> None:
        """Delete a group."""
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing is None:
            raise LdapNotFoundError(f"Group not found: {dn}")
        
        if recursive:
            await self._delete_children_recursive(dn)
        
        await self._ldap.delete(dn)
        logger.info("dhcp_group_deleted", dn=dn)
