"""
DHCP Pool Operations
====================

CRUD operations for dhcpPool objects.
"""

from typing import Any, Dict, List, Optional

import structlog

from heracles_api.services.ldap_service import LdapNotFoundError

from ...schemas import (
    DhcpObjectType,
    PoolCreate,
    PoolUpdate,
    PoolRead,
    PoolListItem,
    PoolListResponse,
)
from ..constants import (
    TYPE_OBJECT_CLASSES,
    COMMON_ATTRIBUTES,
    POOL_ATTRIBUTES,
)
from ..utils import get_first_value
from ..base import DhcpServiceBase, DhcpValidationError

logger = structlog.get_logger(__name__)


class PoolOperationsMixin(DhcpServiceBase):
    """Mixin for DHCP Pool CRUD operations."""
    
    async def list_pools(
        self,
        parent_dn: str,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> PoolListResponse:
        """List pools under a parent (subnet or shared network)."""
        filters = ["(objectClass=dhcpPool)"]
        
        if search:
            filters.append(f"(|(cn=*{search}*)(dhcpComments=*{search}*))")
        
        ldap_filter = f"(&{''.join(filters)})"
        
        entries = await self._ldap.search(
            search_base=parent_dn,
            search_filter=ldap_filter,
            attributes=COMMON_ATTRIBUTES + POOL_ATTRIBUTES,
            scope="onelevel",
        )
        
        items = [
            PoolListItem(
                dn=entry.dn,
                cn=get_first_value(entry, "cn", ""),
                dhcpRange=entry.get("dhcpRange", []),
                dhcpComments=entry.get("dhcpComments", [None])[0],
            )
            for entry in entries
        ]
        
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        
        return PoolListResponse(
            items=items[start:end],
            total=total,
            page=page,
            page_size=page_size,
        )
    
    async def get_pool(self, dn: str) -> PoolRead:
        """Get a pool by DN."""
        entry = await self._ldap.get_by_dn(
            dn,
            attributes=COMMON_ATTRIBUTES + POOL_ATTRIBUTES,
        )
        
        if entry is None:
            raise LdapNotFoundError(f"Pool not found: {dn}")
        
        return PoolRead(
            dn=entry.dn or dn,
            cn=get_first_value(entry, "cn", ""),
            dhcpRange=entry.get("dhcpRange", []),
            dhcpPermitList=entry.get("dhcpPermitList", []),
            dhcpStatements=entry.get("dhcpStatements", []),
            dhcpOption=entry.get("dhcpOption", []),
            dhcpComments=entry.get("dhcpComments", [None])[0],
            parentDn=self._get_parent_dn(dn),
        )
    
    async def create_pool(self, parent_dn: str, data: PoolCreate) -> PoolRead:
        """Create a new pool under a subnet or shared network."""
        dn = self._get_object_dn(data.cn, parent_dn)
        
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing:
            raise DhcpValidationError(f"Pool already exists: {data.cn}")
        
        attributes: Dict[str, List[Any]] = {
            "cn": [data.cn],
            "dhcpRange": data.dhcp_range,
        }
        
        if data.dhcp_permit_list:
            attributes["dhcpPermitList"] = data.dhcp_permit_list
        if data.dhcp_statements:
            attributes["dhcpStatements"] = data.dhcp_statements
        if data.dhcp_options:
            attributes["dhcpOption"] = data.dhcp_options
        if data.comments:
            attributes["dhcpComments"] = [data.comments]
        
        await self._ldap.add(
            dn=dn,
            object_classes=TYPE_OBJECT_CLASSES[DhcpObjectType.POOL],
            attributes=attributes,
        )
        
        logger.info("dhcp_pool_created", cn=data.cn, dn=dn)
        
        return await self.get_pool(dn)
    
    async def update_pool(self, dn: str, data: PoolUpdate) -> PoolRead:
        """Update a pool."""
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing is None:
            raise LdapNotFoundError(f"Pool not found: {dn}")
        
        modifications: Dict[str, List[Any]] = {}
        
        if data.dhcp_range is not None:
            modifications["dhcpRange"] = data.dhcp_range
        if data.dhcp_permit_list is not None:
            modifications["dhcpPermitList"] = data.dhcp_permit_list
        if data.dhcp_statements is not None:
            modifications["dhcpStatements"] = data.dhcp_statements
        if data.dhcp_options is not None:
            modifications["dhcpOption"] = data.dhcp_options
        if data.comments is not None:
            modifications["dhcpComments"] = [data.comments] if data.comments else []
        
        if modifications:
            await self._ldap.modify(dn, modifications)
            logger.info("dhcp_pool_updated", dn=dn)
        
        return await self.get_pool(dn)
    
    async def delete_pool(self, dn: str) -> None:
        """Delete a pool."""
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing is None:
            raise LdapNotFoundError(f"Pool not found: {dn}")
        
        await self._ldap.delete(dn)
        logger.info("dhcp_pool_deleted", dn=dn)
