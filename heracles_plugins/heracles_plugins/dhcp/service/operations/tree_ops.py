"""
DHCP Tree Operations
====================

Operations for building DHCP configuration tree views.
"""

from typing import Any, Dict, Optional

import structlog

from ...schemas import (
    DhcpObjectType,
    DhcpTreeNode,
    DhcpTreeResponse,
)
from ..utils import get_first_value
from ..base import DhcpServiceBase

logger = structlog.get_logger(__name__)


class TreeOperationsMixin(DhcpServiceBase):
    """Mixin for DHCP tree operations."""
    
    async def get_service_tree(self, service_cn: str) -> DhcpTreeResponse:
        """Get the full DHCP configuration tree for a service."""
        # Import here to avoid circular dependency - get_service is from ServiceOperationsMixin
        service = await self.get_service(service_cn)  # type: ignore
        service_dn = self._get_service_dn(service_cn)
        
        # Build tree recursively
        root_node = await self._build_tree_node(service_dn, service.cn, DhcpObjectType.SERVICE)
        
        return DhcpTreeResponse(service=root_node)
    
    async def _build_tree_node(
        self,
        dn: str,
        cn: str,
        obj_type: DhcpObjectType,
    ) -> DhcpTreeNode:
        """Recursively build a tree node with its children."""
        # Get entry details
        entry = await self._ldap.get_by_dn(dn, attributes=["dhcpComments"])
        comments = get_first_value(entry, "dhcpComments") if entry else None
        
        # Get allowed child types
        allowed_children = DhcpObjectType.get_allowed_children(obj_type)
        
        children = []
        for child_type in allowed_children:
            # Search for children of this type
            obj_class = DhcpObjectType.get_object_class(child_type)
            child_entries = await self._ldap.search(
                search_base=dn,
                search_filter=f"(objectClass={obj_class})",
                attributes=["cn", "objectClass", "dhcpComments"],
                scope="onelevel",
            )
            
            for child_entry in child_entries:
                child_dn = child_entry.dn
                child_cn = get_first_value(child_entry, "cn", "")
                
                # Recursively build child nodes
                child_node = await self._build_tree_node(child_dn, child_cn, child_type)
                children.append(child_node)
        
        return DhcpTreeNode(
            dn=dn,
            cn=cn,
            objectType=obj_type,
            dhcpComments=comments,
            children=children,
        )
