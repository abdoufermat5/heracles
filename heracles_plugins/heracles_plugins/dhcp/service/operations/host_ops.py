"""
DHCP Host Operations
====================

CRUD operations for dhcpHost objects.
"""

from typing import Any, Dict, List, Optional

import structlog

from heracles_api.services.ldap_service import LdapNotFoundError

from ...schemas import (
    DhcpObjectType,
    HostCreate,
    HostUpdate,
    HostRead,
    HostListItem,
    HostListResponse,
)
from ..constants import (
    TYPE_OBJECT_CLASSES,
    COMMON_ATTRIBUTES,
    HOST_ATTRIBUTES,
)
from ..utils import get_first_value, get_list_value, extract_fixed_address
from ..base import DhcpServiceBase, DhcpValidationError

logger = structlog.get_logger(__name__)


class HostOperationsMixin(DhcpServiceBase):
    """Mixin for DHCP Host CRUD operations."""
    
    async def list_hosts(
        self,
        parent_dn: str,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> HostListResponse:
        """List hosts under a parent."""
        filters = ["(objectClass=dhcpHost)"]
        
        if search:
            filters.append(f"(|(cn=*{search}*)(dhcpHWAddress=*{search}*)(dhcpComments=*{search}*))")
        
        ldap_filter = f"(&{''.join(filters)})"
        
        entries = await self._ldap.search(
            search_base=parent_dn,
            search_filter=ldap_filter,
            attributes=COMMON_ATTRIBUTES + HOST_ATTRIBUTES,
            scope="subtree",
        )
        
        items = []
        for entry in entries:
            statements = get_list_value(entry, "dhcpStatements")
            fixed_addr = extract_fixed_address(statements)
            
            items.append(HostListItem(
                dn=entry.dn,
                cn=get_first_value(entry, "cn", ""),
                dhcpHWAddress=get_first_value(entry, "dhcpHWAddress"),
                fixedAddress=fixed_addr,
                dhcpComments=get_first_value(entry, "dhcpComments"),
            ))
        
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        
        return HostListResponse(
            items=items[start:end],
            total=total,
            page=page,
            page_size=page_size,
        )
    
    async def get_host(self, dn: str) -> HostRead:
        """Get a host by DN."""
        entry = await self._ldap.get_by_dn(
            dn,
            attributes=COMMON_ATTRIBUTES + HOST_ATTRIBUTES,
        )
        
        if entry is None:
            raise LdapNotFoundError(f"Host not found: {dn}")
        
        statements = get_list_value(entry, "dhcpStatements")
        fixed_addr = extract_fixed_address(statements)
        
        return HostRead(
            dn=entry.dn or dn,
            cn=get_first_value(entry, "cn", ""),
            dhcpHWAddress=get_first_value(entry, "dhcpHWAddress"),
            fixedAddress=fixed_addr,
            dhcpStatements=statements,
            dhcpOption=get_list_value(entry, "dhcpOption"),
            dhcpComments=get_first_value(entry, "dhcpComments"),
            parentDn=self._get_parent_dn(dn),
        )
    
    async def create_host(self, parent_dn: str, data: HostCreate) -> HostRead:
        """Create a new host reservation."""
        dn = self._get_object_dn(data.cn, parent_dn)
        
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing:
            raise DhcpValidationError(f"Host already exists: {data.cn}")
        
        # Validate system reference if systems plugin is available
        if data.system_dn and self._systems_service:
            system = await self._systems_service.get_system_by_dn(data.system_dn)
            if system is None:
                raise DhcpValidationError(f"Referenced system not found: {data.system_dn}")
        
        attributes: Dict[str, List[Any]] = {
            "cn": [data.cn],
        }
        
        if data.dhcp_hw_address:
            attributes["dhcpHWAddress"] = [data.dhcp_hw_address]
        if data.dhcp_statements:
            attributes["dhcpStatements"] = data.dhcp_statements
        if data.dhcp_options:
            attributes["dhcpOption"] = data.dhcp_options
        if data.comments:
            attributes["dhcpComments"] = [data.comments]
        
        await self._ldap.add(
            dn=dn,
            object_classes=TYPE_OBJECT_CLASSES[DhcpObjectType.HOST],
            attributes=attributes,
        )
        
        logger.info("dhcp_host_created", cn=data.cn, dn=dn)
        
        return await self.get_host(dn)
    
    async def update_host(self, dn: str, data: HostUpdate) -> HostRead:
        """Update a host."""
        existing = await self._ldap.get_by_dn(dn, attributes=["cn", "dhcpStatements"])
        if existing is None:
            raise LdapNotFoundError(f"Host not found: {dn}")
        
        modifications: Dict[str, List[Any]] = {}
        
        if data.dhcp_hw_address is not None:
            modifications["dhcpHWAddress"] = [data.dhcp_hw_address] if data.dhcp_hw_address else []
        
        # Handle fixed address update
        if data.fixed_address is not None:
            current_statements = existing.get("dhcpStatements", [])
            # Remove old fixed-address
            new_statements = [s for s in current_statements if not s.startswith("fixed-address ")]
            # Add new one if provided
            if data.fixed_address:
                new_statements.append(f"fixed-address {data.fixed_address}")
            modifications["dhcpStatements"] = new_statements
        elif data.dhcp_statements is not None:
            modifications["dhcpStatements"] = data.dhcp_statements
        
        if data.dhcp_options is not None:
            modifications["dhcpOption"] = data.dhcp_options
        if data.comments is not None:
            modifications["dhcpComments"] = [data.comments] if data.comments else []
        
        if modifications:
            await self._ldap.modify(dn, modifications)
            logger.info("dhcp_host_updated", dn=dn)
        
        return await self.get_host(dn)
    
    async def delete_host(self, dn: str) -> None:
        """Delete a host."""
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing is None:
            raise LdapNotFoundError(f"Host not found: {dn}")
        
        await self._ldap.delete(dn)
        logger.info("dhcp_host_deleted", dn=dn)
    
    async def get_host_by_mac(self, mac_address: str) -> Optional[HostRead]:
        """Find a DHCP host by MAC address."""
        # Normalize MAC format
        from ...schemas import validate_mac_address
        try:
            normalized_mac = validate_mac_address(mac_address)
        except ValueError:
            return None
        
        entries = await self._ldap.search(
            search_base=self._dhcp_dn,
            search_filter=f"(&(objectClass=dhcpHost)(dhcpHWAddress={normalized_mac}))",
            attributes=COMMON_ATTRIBUTES + HOST_ATTRIBUTES,
            scope="subtree",
        )
        
        if not entries:
            return None
        
        entry = entries[0]
        statements = entry.get("dhcpStatements", [])
        fixed_addr = extract_fixed_address(statements)
        
        return HostRead(
            dn=entry.dn,
            cn=get_first_value(entry, "cn", ""),
            dhcpHWAddress=entry.get("dhcpHWAddress", [None])[0],
            fixedAddress=fixed_addr,
            dhcpStatements=statements,
            dhcpOption=entry.get("dhcpOption", []),
            dhcpComments=entry.get("dhcpComments", [None])[0],
            parentDn=self._get_parent_dn(entry.dn),
        )
    
    async def get_hosts_by_ip(self, ip_address: str) -> List[HostRead]:
        """Find DHCP hosts by fixed IP address."""
        entries = await self._ldap.search(
            search_base=self._dhcp_dn,
            search_filter=f"(&(objectClass=dhcpHost)(dhcpStatements=fixed-address {ip_address}*))",
            attributes=COMMON_ATTRIBUTES + HOST_ATTRIBUTES,
            scope="subtree",
        )
        
        hosts = []
        for entry in entries:
            statements = entry.get("dhcpStatements", [])
            fixed_addr = extract_fixed_address(statements)
            
            hosts.append(HostRead(
                dn=entry.dn,
                cn=get_first_value(entry, "cn", ""),
                dhcpHWAddress=entry.get("dhcpHWAddress", [None])[0],
                fixedAddress=fixed_addr,
                dhcpStatements=statements,
                dhcpOption=entry.get("dhcpOption", []),
                dhcpComments=entry.get("dhcpComments", [None])[0],
                parentDn=self._get_parent_dn(entry.dn),
            ))
        
        return hosts
