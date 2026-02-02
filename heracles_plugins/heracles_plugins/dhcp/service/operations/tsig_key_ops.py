"""
DHCP TSIG Key Operations
========================

CRUD operations for dhcpTSigKey objects.
"""

from typing import Any, Dict, List, Optional

import structlog

from heracles_api.services.ldap_service import LdapNotFoundError

from ...schemas import (
    DhcpObjectType,
    TsigKeyAlgorithm,
    TsigKeyCreate,
    TsigKeyUpdate,
    TsigKeyRead,
    TsigKeyListItem,
    TsigKeyListResponse,
)
from ..constants import (
    TYPE_OBJECT_CLASSES,
    COMMON_ATTRIBUTES,
)
from ..utils import get_first_value
from ..base import DhcpServiceBase, DhcpValidationError

logger = structlog.get_logger(__name__)


class TsigKeyOperationsMixin(DhcpServiceBase):
    """Mixin for DHCP TSIG Key CRUD operations."""
    
    async def list_tsig_keys(
        self,
        parent_dn: str,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> TsigKeyListResponse:
        """List TSIG keys under a parent."""
        filters = ["(objectClass=dhcpTSigKey)"]
        
        if search:
            filters.append(f"(|(cn=*{search}*)(dhcpComments=*{search}*))")
        
        ldap_filter = f"(&{''.join(filters)})"
        
        entries = await self._ldap.search(
            search_base=parent_dn,
            search_filter=ldap_filter,
            attributes=COMMON_ATTRIBUTES + ["dhcpKeyAlgorithm"],  # Don't fetch secret
            scope="subtree",
        )
        
        items = [
            TsigKeyListItem(
                dn=entry.dn,
                cn=get_first_value(entry, "cn", ""),
                dhcpKeyAlgorithm=TsigKeyAlgorithm(entry.get("dhcpKeyAlgorithm", ["hmac-md5"])[0]),
                dhcpComments=entry.get("dhcpComments", [None])[0],
            )
            for entry in entries
        ]
        
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        
        return TsigKeyListResponse(
            items=items[start:end],
            total=total,
            page=page,
            page_size=page_size,
        )
    
    async def get_tsig_key(self, dn: str) -> TsigKeyRead:
        """Get a TSIG key by DN (secret not returned)."""
        entry = await self._ldap.get_by_dn(
            dn,
            attributes=COMMON_ATTRIBUTES + ["dhcpKeyAlgorithm"],
        )
        
        if entry is None:
            raise LdapNotFoundError(f"TSIG key not found: {dn}")
        
        return TsigKeyRead(
            dn=entry.dn or dn,
            cn=get_first_value(entry, "cn", ""),
            dhcpKeyAlgorithm=TsigKeyAlgorithm(entry.get("dhcpKeyAlgorithm", ["hmac-md5"])[0]),
            dhcpStatements=entry.get("dhcpStatements", []),
            dhcpOption=entry.get("dhcpOption", []),
            dhcpComments=entry.get("dhcpComments", [None])[0],
            parentDn=self._get_parent_dn(dn),
        )
    
    async def create_tsig_key(self, parent_dn: str, data: TsigKeyCreate) -> TsigKeyRead:
        """Create a new TSIG key."""
        dn = self._get_object_dn(data.cn, parent_dn)
        
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing:
            raise DhcpValidationError(f"TSIG key already exists: {data.cn}")
        
        attributes: Dict[str, List[Any]] = {
            "cn": [data.cn],
            "dhcpKeyAlgorithm": [data.dhcp_key_algorithm.value],
            "dhcpKeySecret": [data.dhcp_key_secret.encode()],
        }
        
        if data.dhcp_statements:
            attributes["dhcpStatements"] = data.dhcp_statements
        if data.dhcp_options:
            attributes["dhcpOption"] = data.dhcp_options
        if data.comments:
            attributes["dhcpComments"] = [data.comments]
        
        await self._ldap.add(
            dn=dn,
            object_classes=TYPE_OBJECT_CLASSES[DhcpObjectType.TSIG_KEY],
            attributes=attributes,
        )
        
        logger.info("dhcp_tsig_key_created", cn=data.cn, dn=dn)
        
        return await self.get_tsig_key(dn)
    
    async def update_tsig_key(self, dn: str, data: TsigKeyUpdate) -> TsigKeyRead:
        """Update a TSIG key."""
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing is None:
            raise LdapNotFoundError(f"TSIG key not found: {dn}")
        
        modifications: Dict[str, List[Any]] = {}
        
        if data.dhcp_key_algorithm is not None:
            modifications["dhcpKeyAlgorithm"] = [data.dhcp_key_algorithm.value]
        if data.dhcp_key_secret is not None:
            modifications["dhcpKeySecret"] = [data.dhcp_key_secret.encode()]
        if data.dhcp_statements is not None:
            modifications["dhcpStatements"] = data.dhcp_statements
        if data.dhcp_options is not None:
            modifications["dhcpOption"] = data.dhcp_options
        if data.comments is not None:
            modifications["dhcpComments"] = [data.comments] if data.comments else []
        
        if modifications:
            await self._ldap.modify(dn, modifications)
            logger.info("dhcp_tsig_key_updated", dn=dn)
        
        return await self.get_tsig_key(dn)
    
    async def delete_tsig_key(self, dn: str) -> None:
        """Delete a TSIG key."""
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing is None:
            raise LdapNotFoundError(f"TSIG key not found: {dn}")
        
        await self._ldap.delete(dn)
        logger.info("dhcp_tsig_key_deleted", dn=dn)
