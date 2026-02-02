"""
DHCP Subnet Operations
======================

CRUD operations for dhcpSubnet objects.
"""

from typing import Any, Dict, List, Optional

import structlog

from heracles_api.services.ldap_service import LdapNotFoundError

from ...schemas import (
    DhcpObjectType,
    SubnetCreate,
    SubnetUpdate,
    SubnetRead,
    SubnetListItem,
    SubnetListResponse,
)
from ..constants import (
    TYPE_OBJECT_CLASSES,
    COMMON_ATTRIBUTES,
    SUBNET_ATTRIBUTES,
)
from ..utils import get_first_value, get_list_value
from ..base import DhcpServiceBase, DhcpValidationError

logger = structlog.get_logger(__name__)


class SubnetOperationsMixin(DhcpServiceBase):
    """Mixin for DHCP Subnet CRUD operations."""
    
    async def list_subnets(
        self,
        service_cn: str,
        parent_dn: Optional[str] = None,
        search: Optional[str] = None,
        base_dn: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> SubnetListResponse:
        """List subnets under a service or parent."""
        search_base = parent_dn or self._get_service_dn(service_cn, base_dn=base_dn)
        
        filters = ["(objectClass=dhcpSubnet)"]
        
        if search:
            search_filter = f"(|(cn=*{search}*)(dhcpComments=*{search}*))"
            filters.append(search_filter)
        
        ldap_filter = f"(&{''.join(filters)})"
        
        entries = await self._ldap.search(
            search_base=search_base,
            search_filter=ldap_filter,
            attributes=COMMON_ATTRIBUTES + SUBNET_ATTRIBUTES,
            scope="subtree",
        )
        
        items = []
        for entry in entries:
            netmask_val = get_first_value(entry, "dhcpNetMask", 0)
            items.append(SubnetListItem(
                dn=entry.dn,
                cn=get_first_value(entry, "cn", ""),
                dhcpNetMask=int(netmask_val) if netmask_val else 0,
                dhcpRange=get_list_value(entry, "dhcpRange"),
                dhcpComments=get_first_value(entry, "dhcpComments"),
            ))
        
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        
        return SubnetListResponse(
            items=items[start:end],
            total=total,
            page=page,
            page_size=page_size,
        )
    
    async def get_subnet(self, dn: str) -> SubnetRead:
        """Get a subnet by DN."""
        entry = await self._ldap.get_by_dn(
            dn,
            attributes=COMMON_ATTRIBUTES + SUBNET_ATTRIBUTES,
        )
        
        if entry is None:
            raise LdapNotFoundError(f"Subnet not found: {dn}")
        
        netmask_val = get_first_value(entry, "dhcpNetMask", 0)
        return SubnetRead(
            dn=entry.dn or dn,
            cn=get_first_value(entry, "cn", ""),
            dhcpNetMask=int(netmask_val) if netmask_val else 0,
            dhcpRange=get_list_value(entry, "dhcpRange"),
            dhcpStatements=get_list_value(entry, "dhcpStatements"),
            dhcpOption=get_list_value(entry, "dhcpOption"),
            dhcpComments=get_first_value(entry, "dhcpComments"),
            parentDn=self._get_parent_dn(dn),
        )
    
    async def create_subnet(
        self,
        parent_dn: str,
        data: SubnetCreate,
    ) -> SubnetRead:
        """Create a new subnet under a parent (service or shared network)."""
        dn = self._get_object_dn(data.cn, parent_dn)
        
        # Check if exists
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing:
            raise DhcpValidationError(f"Subnet already exists: {data.cn}")
        
        # Build attributes
        attributes: Dict[str, List[Any]] = {
            "cn": [data.cn],
            "dhcpNetMask": [str(data.dhcp_netmask)],
        }
        
        if data.dhcp_range:
            attributes["dhcpRange"] = data.dhcp_range
        if data.dhcp_statements:
            attributes["dhcpStatements"] = data.dhcp_statements
        if data.dhcp_options:
            attributes["dhcpOption"] = data.dhcp_options
        if data.comments:
            attributes["dhcpComments"] = [data.comments]
        
        await self._ldap.add(
            dn=dn,
            object_classes=TYPE_OBJECT_CLASSES[DhcpObjectType.SUBNET],
            attributes=attributes,
        )
        
        logger.info("dhcp_subnet_created", cn=data.cn, dn=dn)
        
        return await self.get_subnet(dn)
    
    async def update_subnet(self, dn: str, data: SubnetUpdate) -> SubnetRead:
        """Update a subnet."""
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing is None:
            raise LdapNotFoundError(f"Subnet not found: {dn}")
        
        modifications: Dict[str, List[Any]] = {}
        
        if data.dhcp_netmask is not None:
            modifications["dhcpNetMask"] = [str(data.dhcp_netmask)]
        if data.dhcp_range is not None:
            modifications["dhcpRange"] = data.dhcp_range
        if data.dhcp_statements is not None:
            modifications["dhcpStatements"] = data.dhcp_statements
        if data.dhcp_options is not None:
            modifications["dhcpOption"] = data.dhcp_options
        if data.comments is not None:
            modifications["dhcpComments"] = [data.comments] if data.comments else []
        
        if modifications:
            await self._ldap.modify(dn, modifications)
            logger.info("dhcp_subnet_updated", dn=dn)
        
        return await self.get_subnet(dn)
    
    async def delete_subnet(self, dn: str, recursive: bool = False) -> None:
        """Delete a subnet."""
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing is None:
            raise LdapNotFoundError(f"Subnet not found: {dn}")
        
        if recursive:
            await self._delete_children_recursive(dn)
        
        await self._ldap.delete(dn)
        logger.info("dhcp_subnet_deleted", dn=dn)
