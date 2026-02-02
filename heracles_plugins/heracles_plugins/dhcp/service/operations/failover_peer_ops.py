"""
DHCP Failover Peer Operations
=============================

CRUD operations for dhcpFailOverPeer objects.
"""

from typing import Any, Dict, List, Optional

import structlog

from heracles_api.services.ldap_service import LdapNotFoundError

from ...schemas import (
    DhcpObjectType,
    FailoverPeerCreate,
    FailoverPeerUpdate,
    FailoverPeerRead,
    FailoverPeerListItem,
    FailoverPeerListResponse,
)
from ..constants import (
    TYPE_OBJECT_CLASSES,
    COMMON_ATTRIBUTES,
    FAILOVER_PEER_ATTRIBUTES,
)
from ..utils import get_first_value
from ..base import DhcpServiceBase, DhcpValidationError

logger = structlog.get_logger(__name__)


class FailoverPeerOperationsMixin(DhcpServiceBase):
    """Mixin for DHCP Failover Peer CRUD operations."""
    
    async def list_failover_peers(
        self,
        parent_dn: str,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> FailoverPeerListResponse:
        """List failover peers under a parent."""
        filters = ["(objectClass=dhcpFailOverPeer)"]
        
        if search:
            filters.append(f"(|(cn=*{search}*)(dhcpComments=*{search}*))")
        
        ldap_filter = f"(&{''.join(filters)})"
        
        entries = await self._ldap.search(
            search_base=parent_dn,
            search_filter=ldap_filter,
            attributes=COMMON_ATTRIBUTES + FAILOVER_PEER_ATTRIBUTES,
            scope="subtree",
        )
        
        items = [
            FailoverPeerListItem(
                dn=entry.dn,
                cn=get_first_value(entry, "cn", ""),
                dhcpFailOverPrimaryServer=entry.get("dhcpFailOverPrimaryServer", [""])[0],
                dhcpFailOverSecondaryServer=entry.get("dhcpFailOverSecondaryServer", [""])[0],
                dhcpComments=entry.get("dhcpComments", [None])[0],
            )
            for entry in entries
        ]
        
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        
        return FailoverPeerListResponse(
            items=items[start:end],
            total=total,
            page=page,
            page_size=page_size,
        )
    
    async def get_failover_peer(self, dn: str) -> FailoverPeerRead:
        """Get a failover peer by DN."""
        entry = await self._ldap.get_by_dn(
            dn,
            attributes=COMMON_ATTRIBUTES + FAILOVER_PEER_ATTRIBUTES,
        )
        
        if entry is None:
            raise LdapNotFoundError(f"Failover peer not found: {dn}")
        
        return FailoverPeerRead(
            dn=entry.dn or dn,
            cn=get_first_value(entry, "cn", ""),
            dhcpFailOverPrimaryServer=entry.get("dhcpFailOverPrimaryServer", [""])[0],
            dhcpFailOverSecondaryServer=entry.get("dhcpFailOverSecondaryServer", [""])[0],
            dhcpFailOverPrimaryPort=int(entry.get("dhcpFailOverPrimaryPort", [647])[0]),
            dhcpFailOverSecondaryPort=int(entry.get("dhcpFailOverSecondaryPort", [647])[0]),
            dhcpFailOverResponseDelay=int(entry.get("dhcpFailOverResponseDelay", [0])[0]) or None,
            dhcpFailOverUnackedUpdates=int(entry.get("dhcpFailOverUnackedUpdates", [0])[0]) or None,
            dhcpMaxClientLeadTime=int(entry.get("dhcpMaxClientLeadTime", [0])[0]) or None,
            dhcpFailOverSplit=int(entry.get("dhcpFailOverSplit", [0])[0]) or None,
            dhcpFailOverLoadBalanceTime=int(entry.get("dhcpFailOverLoadBalanceTime", [0])[0]) or None,
            dhcpStatements=entry.get("dhcpStatements", []),
            dhcpOption=entry.get("dhcpOption", []),
            dhcpComments=entry.get("dhcpComments", [None])[0],
            parentDn=self._get_parent_dn(dn),
        )
    
    async def create_failover_peer(
        self,
        parent_dn: str,
        data: FailoverPeerCreate,
    ) -> FailoverPeerRead:
        """Create a new failover peer."""
        dn = self._get_object_dn(data.cn, parent_dn)
        
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing:
            raise DhcpValidationError(f"Failover peer already exists: {data.cn}")
        
        attributes: Dict[str, List[Any]] = {
            "cn": [data.cn],
            "dhcpFailOverPrimaryServer": [data.dhcp_failover_primary_server],
            "dhcpFailOverSecondaryServer": [data.dhcp_failover_secondary_server],
            "dhcpFailOverPrimaryPort": [str(data.dhcp_failover_primary_port)],
            "dhcpFailOverSecondaryPort": [str(data.dhcp_failover_secondary_port)],
        }
        
        if data.dhcp_failover_response_delay:
            attributes["dhcpFailOverResponseDelay"] = [str(data.dhcp_failover_response_delay)]
        if data.dhcp_failover_unacked_updates:
            attributes["dhcpFailOverUnackedUpdates"] = [str(data.dhcp_failover_unacked_updates)]
        if data.dhcp_max_client_lead_time:
            attributes["dhcpMaxClientLeadTime"] = [str(data.dhcp_max_client_lead_time)]
        if data.dhcp_failover_split is not None:
            attributes["dhcpFailOverSplit"] = [str(data.dhcp_failover_split)]
        if data.dhcp_failover_load_balance_time:
            attributes["dhcpFailOverLoadBalanceTime"] = [str(data.dhcp_failover_load_balance_time)]
        if data.dhcp_statements:
            attributes["dhcpStatements"] = data.dhcp_statements
        if data.dhcp_options:
            attributes["dhcpOption"] = data.dhcp_options
        if data.comments:
            attributes["dhcpComments"] = [data.comments]
        
        await self._ldap.add(
            dn=dn,
            object_classes=TYPE_OBJECT_CLASSES[DhcpObjectType.FAILOVER_PEER],
            attributes=attributes,
        )
        
        logger.info("dhcp_failover_peer_created", cn=data.cn, dn=dn)
        
        return await self.get_failover_peer(dn)
    
    async def update_failover_peer(self, dn: str, data: FailoverPeerUpdate) -> FailoverPeerRead:
        """Update a failover peer."""
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing is None:
            raise LdapNotFoundError(f"Failover peer not found: {dn}")
        
        modifications: Dict[str, List[Any]] = {}
        
        if data.dhcp_failover_primary_server is not None:
            modifications["dhcpFailOverPrimaryServer"] = [data.dhcp_failover_primary_server]
        if data.dhcp_failover_secondary_server is not None:
            modifications["dhcpFailOverSecondaryServer"] = [data.dhcp_failover_secondary_server]
        if data.dhcp_failover_primary_port is not None:
            modifications["dhcpFailOverPrimaryPort"] = [str(data.dhcp_failover_primary_port)]
        if data.dhcp_failover_secondary_port is not None:
            modifications["dhcpFailOverSecondaryPort"] = [str(data.dhcp_failover_secondary_port)]
        if data.dhcp_failover_response_delay is not None:
            modifications["dhcpFailOverResponseDelay"] = [str(data.dhcp_failover_response_delay)]
        if data.dhcp_failover_unacked_updates is not None:
            modifications["dhcpFailOverUnackedUpdates"] = [str(data.dhcp_failover_unacked_updates)]
        if data.dhcp_max_client_lead_time is not None:
            modifications["dhcpMaxClientLeadTime"] = [str(data.dhcp_max_client_lead_time)]
        if data.dhcp_failover_split is not None:
            modifications["dhcpFailOverSplit"] = [str(data.dhcp_failover_split)]
        if data.dhcp_failover_load_balance_time is not None:
            modifications["dhcpFailOverLoadBalanceTime"] = [str(data.dhcp_failover_load_balance_time)]
        if data.dhcp_statements is not None:
            modifications["dhcpStatements"] = data.dhcp_statements
        if data.dhcp_options is not None:
            modifications["dhcpOption"] = data.dhcp_options
        if data.comments is not None:
            modifications["dhcpComments"] = [data.comments] if data.comments else []
        
        if modifications:
            await self._ldap.modify(dn, modifications)
            logger.info("dhcp_failover_peer_updated", dn=dn)
        
        return await self.get_failover_peer(dn)
    
    async def delete_failover_peer(self, dn: str) -> None:
        """Delete a failover peer."""
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing is None:
            raise LdapNotFoundError(f"Failover peer not found: {dn}")
        
        await self._ldap.delete(dn)
        logger.info("dhcp_failover_peer_deleted", dn=dn)
