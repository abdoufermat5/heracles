"""
DHCP Shared Network Operations
==============================

CRUD operations for dhcpSharedNetwork objects.
"""

from typing import Any, Dict, List, Optional

import structlog

from heracles_api.services.ldap_service import LdapNotFoundError

from ...schemas import (
    DhcpObjectType,
    SharedNetworkCreate,
    SharedNetworkUpdate,
    SharedNetworkRead,
    SharedNetworkListItem,
    SharedNetworkListResponse,
)
from ..constants import (
    TYPE_OBJECT_CLASSES,
    COMMON_ATTRIBUTES,
    SHARED_NETWORK_ATTRIBUTES,
)
from ..utils import get_first_value
from ..base import DhcpServiceBase, DhcpValidationError

logger = structlog.get_logger(__name__)


class SharedNetworkOperationsMixin(DhcpServiceBase):
    """Mixin for DHCP Shared Network CRUD operations."""
    
    async def list_shared_networks(
        self,
        service_cn: str,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> SharedNetworkListResponse:
        """List shared networks under a service."""
        base_dn = self._get_service_dn(service_cn)
        
        filters = ["(objectClass=dhcpSharedNetwork)"]
        
        if search:
            filters.append(f"(|(cn=*{search}*)(dhcpComments=*{search}*))")
        
        ldap_filter = f"(&{''.join(filters)})"
        
        entries = await self._ldap.search(
            search_base=base_dn,
            search_filter=ldap_filter,
            attributes=COMMON_ATTRIBUTES + SHARED_NETWORK_ATTRIBUTES,
            scope="onelevel",
        )
        
        items = [
            SharedNetworkListItem(
                dn=entry.dn,
                cn=get_first_value(entry, "cn", ""),
                dhcpComments=entry.get("dhcpComments", [None])[0],
            )
            for entry in entries
        ]
        
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        
        return SharedNetworkListResponse(
            items=items[start:end],
            total=total,
            page=page,
            page_size=page_size,
        )
    
    async def get_shared_network(self, dn: str) -> SharedNetworkRead:
        """Get a shared network by DN."""
        entry = await self._ldap.get_by_dn(
            dn,
            attributes=COMMON_ATTRIBUTES + SHARED_NETWORK_ATTRIBUTES,
        )
        
        if entry is None:
            raise LdapNotFoundError(f"Shared network not found: {dn}")
        
        return SharedNetworkRead(
            dn=entry.dn or dn,
            cn=get_first_value(entry, "cn", ""),
            dhcpStatements=entry.get("dhcpStatements", []),
            dhcpOption=entry.get("dhcpOption", []),
            dhcpComments=entry.get("dhcpComments", [None])[0],
            parentDn=self._get_parent_dn(dn),
        )
    
    async def create_shared_network(
        self,
        service_cn: str,
        data: SharedNetworkCreate,
    ) -> SharedNetworkRead:
        """Create a new shared network under a service."""
        parent_dn = self._get_service_dn(service_cn)
        dn = self._get_object_dn(data.cn, parent_dn)
        
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing:
            raise DhcpValidationError(f"Shared network already exists: {data.cn}")
        
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
            object_classes=TYPE_OBJECT_CLASSES[DhcpObjectType.SHARED_NETWORK],
            attributes=attributes,
        )
        
        logger.info("dhcp_shared_network_created", cn=data.cn, dn=dn)
        
        return await self.get_shared_network(dn)
    
    async def update_shared_network(self, dn: str, data: SharedNetworkUpdate) -> SharedNetworkRead:
        """Update a shared network."""
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing is None:
            raise LdapNotFoundError(f"Shared network not found: {dn}")
        
        modifications: Dict[str, List[Any]] = {}
        
        if data.dhcp_statements is not None:
            modifications["dhcpStatements"] = data.dhcp_statements
        if data.dhcp_options is not None:
            modifications["dhcpOption"] = data.dhcp_options
        if data.comments is not None:
            modifications["dhcpComments"] = [data.comments] if data.comments else []
        
        if modifications:
            await self._ldap.modify(dn, modifications)
            logger.info("dhcp_shared_network_updated", dn=dn)
        
        return await self.get_shared_network(dn)
    
    async def delete_shared_network(self, dn: str, recursive: bool = False) -> None:
        """Delete a shared network."""
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing is None:
            raise LdapNotFoundError(f"Shared network not found: {dn}")
        
        if recursive:
            await self._delete_children_recursive(dn)
        
        await self._ldap.delete(dn)
        logger.info("dhcp_shared_network_deleted", dn=dn)
