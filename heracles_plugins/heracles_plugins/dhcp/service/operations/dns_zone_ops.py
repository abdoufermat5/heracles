"""
DHCP DNS Zone Operations
========================

CRUD operations for dhcpDnsZone objects.
"""

from typing import Any, Dict, List, Optional

import structlog

from heracles_api.services.ldap_service import LdapNotFoundError

from ...schemas import (
    DhcpObjectType,
    DnsZoneCreate,
    DnsZoneUpdate,
    DnsZoneRead,
    DnsZoneListItem,
    DnsZoneListResponse,
)
from ..constants import (
    TYPE_OBJECT_CLASSES,
    COMMON_ATTRIBUTES,
    DNS_ZONE_ATTRIBUTES,
)
from ..utils import get_first_value
from ..base import DhcpServiceBase, DhcpValidationError

logger = structlog.get_logger(__name__)


class DnsZoneOperationsMixin(DhcpServiceBase):
    """Mixin for DHCP DNS Zone CRUD operations."""
    
    async def list_dns_zones(
        self,
        parent_dn: str,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> DnsZoneListResponse:
        """List DNS zones under a parent."""
        filters = ["(objectClass=dhcpDnsZone)"]
        
        if search:
            filters.append(f"(|(cn=*{search}*)(dhcpComments=*{search}*))")
        
        ldap_filter = f"(&{''.join(filters)})"
        
        entries = await self._ldap.search(
            search_base=parent_dn,
            search_filter=ldap_filter,
            attributes=COMMON_ATTRIBUTES + DNS_ZONE_ATTRIBUTES,
            scope="subtree",
        )
        
        items = [
            DnsZoneListItem(
                dn=entry.dn,
                cn=get_first_value(entry, "cn", ""),
                dhcpDnsZoneServer=entry.get("dhcpDnsZoneServer", [""])[0],
                dhcpComments=entry.get("dhcpComments", [None])[0],
            )
            for entry in entries
        ]
        
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        
        return DnsZoneListResponse(
            items=items[start:end],
            total=total,
            page=page,
            page_size=page_size,
        )
    
    async def get_dns_zone(self, dn: str) -> DnsZoneRead:
        """Get a DNS zone by DN."""
        entry = await self._ldap.get_by_dn(
            dn,
            attributes=COMMON_ATTRIBUTES + DNS_ZONE_ATTRIBUTES,
        )
        
        if entry is None:
            raise LdapNotFoundError(f"DNS zone not found: {dn}")
        
        return DnsZoneRead(
            dn=entry.dn or dn,
            cn=get_first_value(entry, "cn", ""),
            dhcpDnsZoneServer=entry.get("dhcpDnsZoneServer", [""])[0],
            dhcpKeyDN=entry.get("dhcpKeyDN", [None])[0],
            dhcpStatements=entry.get("dhcpStatements", []),
            dhcpOption=entry.get("dhcpOption", []),
            dhcpComments=entry.get("dhcpComments", [None])[0],
            parentDn=self._get_parent_dn(dn),
        )
    
    async def create_dns_zone(self, parent_dn: str, data: DnsZoneCreate) -> DnsZoneRead:
        """Create a new DNS zone."""
        dn = self._get_object_dn(data.cn, parent_dn)
        
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing:
            raise DhcpValidationError(f"DNS zone already exists: {data.cn}")
        
        attributes: Dict[str, List[Any]] = {
            "cn": [data.cn],
            "dhcpDnsZoneServer": [data.dhcp_dns_zone_server],
        }
        
        if data.dhcp_key_dn:
            attributes["dhcpKeyDN"] = [data.dhcp_key_dn]
        if data.dhcp_statements:
            attributes["dhcpStatements"] = data.dhcp_statements
        if data.dhcp_options:
            attributes["dhcpOption"] = data.dhcp_options
        if data.comments:
            attributes["dhcpComments"] = [data.comments]
        
        await self._ldap.add(
            dn=dn,
            object_classes=TYPE_OBJECT_CLASSES[DhcpObjectType.DNS_ZONE],
            attributes=attributes,
        )
        
        logger.info("dhcp_dns_zone_created", cn=data.cn, dn=dn)
        
        return await self.get_dns_zone(dn)
    
    async def update_dns_zone(self, dn: str, data: DnsZoneUpdate) -> DnsZoneRead:
        """Update a DNS zone."""
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing is None:
            raise LdapNotFoundError(f"DNS zone not found: {dn}")
        
        modifications: Dict[str, List[Any]] = {}
        
        if data.dhcp_dns_zone_server is not None:
            modifications["dhcpDnsZoneServer"] = [data.dhcp_dns_zone_server]
        if data.dhcp_key_dn is not None:
            modifications["dhcpKeyDN"] = [data.dhcp_key_dn] if data.dhcp_key_dn else []
        if data.dhcp_statements is not None:
            modifications["dhcpStatements"] = data.dhcp_statements
        if data.dhcp_options is not None:
            modifications["dhcpOption"] = data.dhcp_options
        if data.comments is not None:
            modifications["dhcpComments"] = [data.comments] if data.comments else []
        
        if modifications:
            await self._ldap.modify(dn, modifications)
            logger.info("dhcp_dns_zone_updated", dn=dn)
        
        return await self.get_dns_zone(dn)
    
    async def delete_dns_zone(self, dn: str) -> None:
        """Delete a DNS zone."""
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing is None:
            raise LdapNotFoundError(f"DNS zone not found: {dn}")
        
        await self._ldap.delete(dn)
        logger.info("dhcp_dns_zone_deleted", dn=dn)
