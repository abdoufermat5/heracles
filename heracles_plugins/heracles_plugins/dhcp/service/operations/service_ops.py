"""
DHCP Service Operations
=======================

CRUD operations for dhcpService objects.
"""

from typing import Any, Dict, List, Optional

import structlog

from heracles_api.services.ldap_service import LdapNotFoundError

from ...schemas import (
    DhcpObjectType,
    DhcpServiceCreate,
    DhcpServiceUpdate,
    DhcpServiceRead,
    DhcpServiceListItem,
    DhcpServiceListResponse,
)
from ..constants import (
    TYPE_OBJECT_CLASSES,
    COMMON_ATTRIBUTES,
    SERVICE_ATTRIBUTES,
)
from ..utils import get_first_value, get_list_value
from ..base import DhcpServiceBase, DhcpValidationError

logger = structlog.get_logger(__name__)


class ServiceOperationsMixin(DhcpServiceBase):
    """Mixin for DHCP Service CRUD operations."""
    
    async def list_services(
        self,
        search: Optional[str] = None,
        base_dn: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> DhcpServiceListResponse:
        """List all DHCP services."""
        if not base_dn:
             await self._ensure_dhcp_ou()
        else:
             await self._ensure_dhcp_ou(base_dn=base_dn)
        
        # Determine search base
        if base_dn:
            search_base = f"{self._dhcp_rdn},{base_dn}"
        else:
            search_base = self._dhcp_dn
        
        # Build search filter
        filters = ["(objectClass=dhcpService)"]
        
        if search:
            search_filter = f"(|(cn=*{search}*)(dhcpComments=*{search}*))"
            filters.append(search_filter)
        
        ldap_filter = f"(&{''.join(filters)})"
        
        # Search
        entries = await self._ldap.search(
            search_base=search_base,
            search_filter=ldap_filter,
            attributes=COMMON_ATTRIBUTES + SERVICE_ATTRIBUTES,
            scope="onelevel",
        )
        
        # Convert to list items
        items = []
        for entry in entries:
            items.append(DhcpServiceListItem(
                dn=entry.dn,
                cn=get_first_value(entry, "cn", ""),
                comments=get_first_value(entry, "dhcpComments"),
            ))
        
        # Pagination
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_items = items[start:end]
        
        return DhcpServiceListResponse(
            items=paginated_items,
            total=total,
            page=page,
            page_size=page_size,
        )
    
    async def get_service(
        self, 
        cn: str,
        base_dn: Optional[str] = None
    ) -> DhcpServiceRead:
        """Get a DHCP service by name."""
        dn = self._get_service_dn(cn, base_dn=base_dn)
        
        entry = await self._ldap.get_by_dn(
            dn,
            attributes=COMMON_ATTRIBUTES + SERVICE_ATTRIBUTES,
        )
        
        if entry is None:
            raise LdapNotFoundError(f"DHCP service not found: {cn}")
        
        return DhcpServiceRead(
            dn=entry.dn or dn,
            cn=get_first_value(entry, "cn", cn),
            dhcpPrimaryDN=get_first_value(entry, "dhcpPrimaryDN"),
            dhcpSecondaryDN=get_first_value(entry, "dhcpSecondaryDN"),
            dhcpStatements=get_list_value(entry, "dhcpStatements"),
            dhcpOption=get_list_value(entry, "dhcpOption"),
            dhcpComments=get_first_value(entry, "dhcpComments"),
        )
    
    async def create_service(
        self, 
        data: DhcpServiceCreate,
        base_dn: Optional[str] = None
    ) -> DhcpServiceRead:
        """Create a new DHCP service."""
        await self._ensure_dhcp_ou(base_dn=base_dn)
        
        dn = self._get_service_dn(data.cn, base_dn=base_dn)
        
        # Check if exists
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing:
            raise DhcpValidationError(f"DHCP service already exists: {data.cn}")
        
        # Build attributes
        attributes: Dict[str, List[Any]] = {
            "cn": [data.cn],
        }
        
        if data.dhcp_primary_dn:
            attributes["dhcpPrimaryDN"] = [data.dhcp_primary_dn]
        if data.dhcp_secondary_dn:
            attributes["dhcpSecondaryDN"] = [data.dhcp_secondary_dn]
        if data.dhcp_statements:
            attributes["dhcpStatements"] = data.dhcp_statements
        if data.dhcp_options:
            attributes["dhcpOption"] = data.dhcp_options
        if data.comments:
            attributes["dhcpComments"] = [data.comments]
        
        # Create entry
        await self._ldap.add(
            dn=dn,
            object_classes=TYPE_OBJECT_CLASSES[DhcpObjectType.SERVICE],
            attributes=attributes,
        )
        
        logger.info("dhcp_service_created", cn=data.cn, dn=dn)
        
        return await self.get_service(data.cn, base_dn=base_dn)
    
    async def update_service(
        self, 
        cn: str, 
        data: DhcpServiceUpdate,
        base_dn: Optional[str] = None
    ) -> DhcpServiceRead:
        """Update a DHCP service."""
        dn = self._get_service_dn(cn, base_dn=base_dn)
        
        # Check exists
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing is None:
            raise LdapNotFoundError(f"DHCP service not found: {cn}")
        
        # Build modifications
        modifications: Dict[str, List[Any]] = {}
        
        if data.dhcp_primary_dn is not None:
            modifications["dhcpPrimaryDN"] = [data.dhcp_primary_dn] if data.dhcp_primary_dn else []
        if data.dhcp_secondary_dn is not None:
            modifications["dhcpSecondaryDN"] = [data.dhcp_secondary_dn] if data.dhcp_secondary_dn else []
        if data.dhcp_statements is not None:
            modifications["dhcpStatements"] = data.dhcp_statements
        if data.dhcp_options is not None:
            modifications["dhcpOption"] = data.dhcp_options
        if data.comments is not None:
            modifications["dhcpComments"] = [data.comments] if data.comments else []
        
        if modifications:
            await self._ldap.modify(dn, modifications)
            logger.info("dhcp_service_updated", cn=cn, dn=dn)
        
        return await self.get_service(cn, base_dn=base_dn)
    
    async def delete_service(
        self, 
        cn: str, 
        recursive: bool = False,
        base_dn: Optional[str] = None
    ) -> None:
        """Delete a DHCP service."""
        dn = self._get_service_dn(cn, base_dn=base_dn)
        
        # Check exists
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing is None:
            raise LdapNotFoundError(f"DHCP service not found: {cn}")
        
        if recursive:
            # Delete all children first
            await self._delete_children_recursive(dn)
        
        await self._ldap.delete(dn)
        logger.info("dhcp_service_deleted", cn=cn, dn=dn)
