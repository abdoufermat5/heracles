"""
DHCP Service
============

Business logic for DHCP configuration management.
Handles LDAP operations for all DHCP object types.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import re

import structlog

from heracles_api.plugins.base import TabService
from heracles_api.services.ldap_service import (
    LdapService,
    LdapEntry,
    LdapOperationError,
    LdapNotFoundError,
)

from .schemas import (
    DhcpObjectType,
    TsigKeyAlgorithm,
    # Service
    DhcpServiceCreate,
    DhcpServiceUpdate,
    DhcpServiceRead,
    DhcpServiceListItem,
    DhcpServiceListResponse,
    # Subnet
    SubnetCreate,
    SubnetUpdate,
    SubnetRead,
    SubnetListItem,
    SubnetListResponse,
    # Pool
    PoolCreate,
    PoolUpdate,
    PoolRead,
    PoolListItem,
    PoolListResponse,
    # Host
    HostCreate,
    HostUpdate,
    HostRead,
    HostListItem,
    HostListResponse,
    # Shared Network
    SharedNetworkCreate,
    SharedNetworkUpdate,
    SharedNetworkRead,
    SharedNetworkListItem,
    SharedNetworkListResponse,
    # Group
    GroupCreate,
    GroupUpdate,
    GroupRead,
    GroupListItem,
    GroupListResponse,
    # Class
    DhcpClassCreate,
    DhcpClassUpdate,
    DhcpClassRead,
    DhcpClassListItem,
    DhcpClassListResponse,
    # SubClass
    SubClassCreate,
    SubClassUpdate,
    SubClassRead,
    # TSIG Key
    TsigKeyCreate,
    TsigKeyUpdate,
    TsigKeyRead,
    TsigKeyListItem,
    TsigKeyListResponse,
    # DNS Zone
    DnsZoneCreate,
    DnsZoneUpdate,
    DnsZoneRead,
    DnsZoneListItem,
    DnsZoneListResponse,
    # Failover Peer
    FailoverPeerCreate,
    FailoverPeerUpdate,
    FailoverPeerRead,
    FailoverPeerListItem,
    FailoverPeerListResponse,
    # Tree
    DhcpTreeNode,
    DhcpTreeResponse,
)

logger = structlog.get_logger(__name__)


class DhcpValidationError(Exception):
    """Raised when DHCP validation fails."""
    pass


class DhcpService(TabService):
    """
    Service for managing DHCP configuration in LDAP.
    
    Handles all DHCP object types:
    - Service (dhcpService) - root configuration
    - SharedNetwork (dhcpSharedNetwork)
    - Subnet (dhcpSubnet)
    - Pool (dhcpPool)
    - Host (dhcpHost)
    - Group (dhcpGroup)
    - Class (dhcpClass)
    - SubClass (dhcpSubClass)
    - TsigKey (dhcpTSigKey)
    - DnsZone (dhcpDnsZone)
    - FailoverPeer (dhcpFailOverPeer)
    """
    
    # Map object types to their LDAP objectClasses
    TYPE_OBJECT_CLASSES = {
        DhcpObjectType.SERVICE: ["dhcpService"],
        DhcpObjectType.SHARED_NETWORK: ["dhcpSharedNetwork"],
        DhcpObjectType.SUBNET: ["dhcpSubnet"],
        DhcpObjectType.POOL: ["dhcpPool"],
        DhcpObjectType.HOST: ["dhcpHost"],
        DhcpObjectType.GROUP: ["dhcpGroup"],
        DhcpObjectType.CLASS: ["dhcpClass"],
        DhcpObjectType.SUBCLASS: ["dhcpSubClass"],
        DhcpObjectType.TSIG_KEY: ["dhcpTSigKey"],
        DhcpObjectType.DNS_ZONE: ["dhcpDnsZone"],
        DhcpObjectType.FAILOVER_PEER: ["dhcpFailOverPeer"],
    }
    
    # Common attributes for all DHCP types
    COMMON_ATTRIBUTES = [
        "cn",
        "objectClass",
        "dhcpStatements",
        "dhcpOption",
        "dhcpComments",
    ]
    
    # Service-specific attributes
    SERVICE_ATTRIBUTES = [
        "dhcpPrimaryDN",
        "dhcpSecondaryDN",
        "dhcpServerDN",
        "dhcpSharedNetworkDN",
        "dhcpSubnetDN",
        "dhcpGroupDN",
        "dhcpHostDN",
        "dhcpClassesDN",
        "dhcpZoneDN",
        "dhcpKeyDN",
        "dhcpFailOverPeerDN",
    ]
    
    # Subnet-specific attributes
    SUBNET_ATTRIBUTES = [
        "dhcpNetMask",
        "dhcpRange",
        "dhcpPoolDN",
        "dhcpGroupDN",
        "dhcpHostDN",
        "dhcpClassesDN",
        "dhcpLeasesDN",
        "dhcpZoneDN",
        "dhcpKeyDN",
        "dhcpFailOverPeerDN",
    ]
    
    # Pool-specific attributes
    POOL_ATTRIBUTES = [
        "dhcpRange",
        "dhcpPermitList",
        "dhcpClassesDN",
        "dhcpLeasesDN",
        "dhcpZoneDN",
        "dhcpKeyDN",
    ]
    
    # Host-specific attributes
    HOST_ATTRIBUTES = [
        "dhcpHWAddress",
        "dhcpLeaseDN",
    ]
    
    # Shared network-specific attributes
    SHARED_NETWORK_ATTRIBUTES = [
        "dhcpSubnetDN",
        "dhcpPoolDN",
        "dhcpZoneDN",
    ]
    
    # Group-specific attributes
    GROUP_ATTRIBUTES = [
        "dhcpHostDN",
    ]
    
    # Class-specific attributes
    CLASS_ATTRIBUTES = [
        "dhcpSubClassesDN",
    ]
    
    # SubClass-specific attributes
    SUBCLASS_ATTRIBUTES = [
        "dhcpClassData",
    ]
    
    # TSIG Key-specific attributes
    TSIG_KEY_ATTRIBUTES = [
        "dhcpKeyAlgorithm",
        "dhcpKeySecret",
    ]
    
    # DNS Zone-specific attributes
    DNS_ZONE_ATTRIBUTES = [
        "dhcpDnsZoneServer",
        "dhcpKeyDN",
    ]
    
    # Failover Peer-specific attributes
    FAILOVER_PEER_ATTRIBUTES = [
        "dhcpFailOverPrimaryServer",
        "dhcpFailOverSecondaryServer",
        "dhcpFailOverPrimaryPort",
        "dhcpFailOverSecondaryPort",
        "dhcpFailOverResponseDelay",
        "dhcpFailOverUnackedUpdates",
        "dhcpMaxClientLeadTime",
        "dhcpFailOverSplit",
        "dhcpHashBucketAssignment",
        "dhcpFailOverLoadBalanceTime",
    ]
    
    def __init__(self, ldap_service: LdapService, config: Dict[str, Any]):
        super().__init__(ldap_service, config)
        
        # Configuration
        self._dhcp_rdn = config.get("dhcp_rdn", "ou=dhcp")
        self._base_dn = config.get("base_dn", ldap_service.base_dn)
        self._dhcp_dn = f"{self._dhcp_rdn},{self._base_dn}"
        
        # Systems plugin integration (optional)
        self._systems_service = None
    
    def set_systems_service(self, systems_service: Any) -> None:
        """Set the systems service for host validation integration."""
        self._systems_service = systems_service
    
    @staticmethod
    def _get_first_value(entry: LdapEntry, attr: str, default: Any = None) -> Any:
        """
        Safely get the first value of an attribute.
        
        Handles both single values and lists returned by LdapEntry.
        """
        value = entry.get(attr)
        if value is None:
            return default
        if isinstance(value, list):
            return value[0] if value else default
        return value
    
    @staticmethod
    def _get_list_value(entry: LdapEntry, attr: str) -> List[str]:
        """
        Safely get an attribute as a list.
        
        Handles both single values and lists returned by LdapEntry.
        """
        value = entry.get(attr)
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]
    
    def _get_all_attributes(self) -> List[str]:
        """Get all managed attributes."""
        attrs = set(self.COMMON_ATTRIBUTES)
        attrs.update(self.SERVICE_ATTRIBUTES)
        attrs.update(self.SUBNET_ATTRIBUTES)
        attrs.update(self.POOL_ATTRIBUTES)
        attrs.update(self.HOST_ATTRIBUTES)
        attrs.update(self.SHARED_NETWORK_ATTRIBUTES)
        attrs.update(self.GROUP_ATTRIBUTES)
        attrs.update(self.CLASS_ATTRIBUTES)
        attrs.update(self.SUBCLASS_ATTRIBUTES)
        attrs.update(self.TSIG_KEY_ATTRIBUTES)
        attrs.update(self.DNS_ZONE_ATTRIBUTES)
        attrs.update(self.FAILOVER_PEER_ATTRIBUTES)
        return list(attrs)
    
    def _get_dhcp_container(self, base_dn: Optional[str] = None) -> str:
        """Get the DHCP container DN for the given context.
        
        If base_dn is provided (department context), returns ou=dhcp,{base_dn}.
        Otherwise returns the default ou=dhcp,{root_base_dn}.
        """
        if base_dn:
            return f"{self._dhcp_rdn},{base_dn}"
        return self._dhcp_dn
    
    def _get_service_dn(self, service_cn: str, base_dn: Optional[str] = None) -> str:
        """Get the DN for a DHCP service."""
        if base_dn:
            return f"cn={service_cn},{self._dhcp_rdn},{base_dn}"
        return f"cn={service_cn},{self._dhcp_dn}"
    
    def _get_object_dn(self, cn: str, parent_dn: str) -> str:
        """Get the DN for a DHCP object under a parent."""
        return f"cn={cn},{parent_dn}"
    
    def _get_parent_dn(self, dn: str) -> str:
        """Extract parent DN from an object DN."""
        parts = dn.split(",", 1)
        if len(parts) > 1:
            return parts[1]
        return self._dhcp_dn
    
    def _extract_fixed_address(self, statements: List[str]) -> Optional[str]:
        """Extract fixed-address from dhcpStatements."""
        for stmt in statements:
            if stmt.startswith("fixed-address "):
                return stmt.split(" ", 1)[1].strip().rstrip(";")
        return None
    
    def _detect_object_type(self, entry: LdapEntry) -> Optional[DhcpObjectType]:
        """Detect object type from LDAP entry objectClasses."""
        object_classes = entry.get("objectClass", [])
        for oc in object_classes:
            obj_type = DhcpObjectType.from_object_class(oc)
            if obj_type:
                return obj_type
        return None
    
    # ========================================================================
    # OU Management
    # ========================================================================
    
    async def _ensure_dhcp_ou(self, base_dn: Optional[str] = None) -> None:
        """Ensure the DHCP OU exists."""
        if base_dn:
            dn = f"{self._dhcp_rdn},{base_dn}"
        else:
            dn = self._dhcp_dn
            
        try:
            exists = await self._ldap.get_by_dn(
               dn, 
                attributes=["ou"]
            )
            if exists is None:
                await self._ldap.add(
                    dn=dn,
                    object_classes=["organizationalUnit"],
                    attributes={"ou": ["dhcp"]}, # Assuming dhcp_rdn is ou=dhcp
                )
                logger.info("dhcp_ou_created", dn=dn)
        except LdapOperationError as e:
            logger.warning("dhcp_ou_check_failed", error=str(e))
    
    # ========================================================================
    # Service CRUD Operations
    # ========================================================================
    
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
            attributes=self.COMMON_ATTRIBUTES + self.SERVICE_ATTRIBUTES,
            scope="onelevel",
        )
        
        # Convert to list items
        items = []
        for entry in entries:
            items.append(DhcpServiceListItem(
                dn=entry.dn,
                cn=self._get_first_value(entry, "cn", ""),
                comments=self._get_first_value(entry, "dhcpComments"),
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
            attributes=self.COMMON_ATTRIBUTES + self.SERVICE_ATTRIBUTES,
        )
        
        if entry is None:
            raise LdapNotFoundError(f"DHCP service not found: {cn}")
        
        return DhcpServiceRead(
            dn=entry.dn or dn,
            cn=self._get_first_value(entry, "cn", cn),
            dhcpPrimaryDN=self._get_first_value(entry, "dhcpPrimaryDN"),
            dhcpSecondaryDN=self._get_first_value(entry, "dhcpSecondaryDN"),
            dhcpStatements=self._get_list_value(entry, "dhcpStatements"),
            dhcpOption=self._get_list_value(entry, "dhcpOption"),
            dhcpComments=self._get_first_value(entry, "dhcpComments"),
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
            object_classes=self.TYPE_OBJECT_CLASSES[DhcpObjectType.SERVICE],
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
    
    async def _delete_children_recursive(self, parent_dn: str) -> None:
        """Recursively delete all children of a DN."""
        # Find all direct children
        entries = await self._ldap.search(
            search_base=parent_dn,
            search_filter="(objectClass=*)",
            attributes=["dn"],
            scope="onelevel",
        )
        
        # Delete each child recursively
        for entry in entries:
            child_dn = entry.dn
            if child_dn and child_dn != parent_dn:
                await self._delete_children_recursive(child_dn)
                await self._ldap.delete(child_dn)
    
    # ========================================================================
    # Subnet CRUD Operations
    # ========================================================================
    
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
            attributes=self.COMMON_ATTRIBUTES + self.SUBNET_ATTRIBUTES,
            scope="subtree",
        )
        
        items = []
        for entry in entries:
            netmask_val = self._get_first_value(entry, "dhcpNetMask", 0)
            items.append(SubnetListItem(
                dn=entry.dn,
                cn=self._get_first_value(entry, "cn", ""),
                dhcpNetMask=int(netmask_val) if netmask_val else 0,
                dhcpRange=self._get_list_value(entry, "dhcpRange"),
                dhcpComments=self._get_first_value(entry, "dhcpComments"),
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
            attributes=self.COMMON_ATTRIBUTES + self.SUBNET_ATTRIBUTES,
        )
        
        if entry is None:
            raise LdapNotFoundError(f"Subnet not found: {dn}")
        
        netmask_val = self._get_first_value(entry, "dhcpNetMask", 0)
        return SubnetRead(
            dn=entry.dn or dn,
            cn=self._get_first_value(entry, "cn", ""),
            dhcpNetMask=int(netmask_val) if netmask_val else 0,
            dhcpRange=self._get_list_value(entry, "dhcpRange"),
            dhcpStatements=self._get_list_value(entry, "dhcpStatements"),
            dhcpOption=self._get_list_value(entry, "dhcpOption"),
            dhcpComments=self._get_first_value(entry, "dhcpComments"),
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
            object_classes=self.TYPE_OBJECT_CLASSES[DhcpObjectType.SUBNET],
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
    
    # ========================================================================
    # Pool CRUD Operations
    # ========================================================================
    
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
            attributes=self.COMMON_ATTRIBUTES + self.POOL_ATTRIBUTES,
            scope="onelevel",
        )
        
        items = [
            PoolListItem(
                dn=entry.dn,
                cn=self._get_first_value(entry, "cn", ""),
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
            attributes=self.COMMON_ATTRIBUTES + self.POOL_ATTRIBUTES,
        )
        
        if entry is None:
            raise LdapNotFoundError(f"Pool not found: {dn}")
        
        return PoolRead(
            dn=entry.dn or dn,
            cn=self._get_first_value(entry, "cn", ""),
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
            object_classes=self.TYPE_OBJECT_CLASSES[DhcpObjectType.POOL],
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
    
    # ========================================================================
    # Host CRUD Operations
    # ========================================================================
    
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
            attributes=self.COMMON_ATTRIBUTES + self.HOST_ATTRIBUTES,
            scope="subtree",
        )
        
        items = []
        for entry in entries:
            statements = self._get_list_value(entry, "dhcpStatements")
            fixed_addr = self._extract_fixed_address(statements)
            
            items.append(HostListItem(
                dn=entry.dn,
                cn=self._get_first_value(entry, "cn", ""),
                dhcpHWAddress=self._get_first_value(entry, "dhcpHWAddress"),
                fixedAddress=fixed_addr,
                dhcpComments=self._get_first_value(entry, "dhcpComments"),
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
            attributes=self.COMMON_ATTRIBUTES + self.HOST_ATTRIBUTES,
        )
        
        if entry is None:
            raise LdapNotFoundError(f"Host not found: {dn}")
        
        statements = self._get_list_value(entry, "dhcpStatements")
        fixed_addr = self._extract_fixed_address(statements)
        
        return HostRead(
            dn=entry.dn or dn,
            cn=self._get_first_value(entry, "cn", ""),
            dhcpHWAddress=self._get_first_value(entry, "dhcpHWAddress"),
            fixedAddress=fixed_addr,
            dhcpStatements=statements,
            dhcpOption=self._get_list_value(entry, "dhcpOption"),
            dhcpComments=self._get_first_value(entry, "dhcpComments"),
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
            object_classes=self.TYPE_OBJECT_CLASSES[DhcpObjectType.HOST],
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
    
    # ========================================================================
    # Shared Network CRUD Operations
    # ========================================================================
    
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
            attributes=self.COMMON_ATTRIBUTES + self.SHARED_NETWORK_ATTRIBUTES,
            scope="onelevel",
        )
        
        items = [
            SharedNetworkListItem(
                dn=entry.dn,
                cn=self._get_first_value(entry, "cn", ""),
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
            attributes=self.COMMON_ATTRIBUTES + self.SHARED_NETWORK_ATTRIBUTES,
        )
        
        if entry is None:
            raise LdapNotFoundError(f"Shared network not found: {dn}")
        
        return SharedNetworkRead(
            dn=entry.dn or dn,
            cn=self._get_first_value(entry, "cn", ""),
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
            object_classes=self.TYPE_OBJECT_CLASSES[DhcpObjectType.SHARED_NETWORK],
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
    
    # ========================================================================
    # Group CRUD Operations
    # ========================================================================
    
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
            attributes=self.COMMON_ATTRIBUTES + self.GROUP_ATTRIBUTES,
            scope="subtree",
        )
        
        items = [
            GroupListItem(
                dn=entry.dn,
                cn=self._get_first_value(entry, "cn", ""),
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
            attributes=self.COMMON_ATTRIBUTES + self.GROUP_ATTRIBUTES,
        )
        
        if entry is None:
            raise LdapNotFoundError(f"Group not found: {dn}")
        
        return GroupRead(
            dn=entry.dn or dn,
            cn=self._get_first_value(entry, "cn", ""),
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
            object_classes=self.TYPE_OBJECT_CLASSES[DhcpObjectType.GROUP],
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
    
    # ========================================================================
    # Class CRUD Operations
    # ========================================================================
    
    async def list_classes(
        self,
        parent_dn: str,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> DhcpClassListResponse:
        """List classes under a parent."""
        filters = ["(objectClass=dhcpClass)"]
        
        if search:
            filters.append(f"(|(cn=*{search}*)(dhcpComments=*{search}*))")
        
        ldap_filter = f"(&{''.join(filters)})"
        
        entries = await self._ldap.search(
            search_base=parent_dn,
            search_filter=ldap_filter,
            attributes=self.COMMON_ATTRIBUTES + self.CLASS_ATTRIBUTES,
            scope="subtree",
        )
        
        items = [
            DhcpClassListItem(
                dn=entry.dn,
                cn=self._get_first_value(entry, "cn", ""),
                dhcpComments=entry.get("dhcpComments", [None])[0],
            )
            for entry in entries
        ]
        
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        
        return DhcpClassListResponse(
            items=items[start:end],
            total=total,
            page=page,
            page_size=page_size,
        )
    
    async def get_class(self, dn: str) -> DhcpClassRead:
        """Get a class by DN."""
        entry = await self._ldap.get_by_dn(
            dn,
            attributes=self.COMMON_ATTRIBUTES + self.CLASS_ATTRIBUTES,
        )
        
        if entry is None:
            raise LdapNotFoundError(f"Class not found: {dn}")
        
        return DhcpClassRead(
            dn=entry.dn or dn,
            cn=self._get_first_value(entry, "cn", ""),
            dhcpStatements=entry.get("dhcpStatements", []),
            dhcpOption=entry.get("dhcpOption", []),
            dhcpComments=entry.get("dhcpComments", [None])[0],
            parentDn=self._get_parent_dn(dn),
        )
    
    async def create_class(self, parent_dn: str, data: DhcpClassCreate) -> DhcpClassRead:
        """Create a new class."""
        dn = self._get_object_dn(data.cn, parent_dn)
        
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing:
            raise DhcpValidationError(f"Class already exists: {data.cn}")
        
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
            object_classes=self.TYPE_OBJECT_CLASSES[DhcpObjectType.CLASS],
            attributes=attributes,
        )
        
        logger.info("dhcp_class_created", cn=data.cn, dn=dn)
        
        return await self.get_class(dn)
    
    async def update_class(self, dn: str, data: DhcpClassUpdate) -> DhcpClassRead:
        """Update a class."""
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing is None:
            raise LdapNotFoundError(f"Class not found: {dn}")
        
        modifications: Dict[str, List[Any]] = {}
        
        if data.dhcp_statements is not None:
            modifications["dhcpStatements"] = data.dhcp_statements
        if data.dhcp_options is not None:
            modifications["dhcpOption"] = data.dhcp_options
        if data.comments is not None:
            modifications["dhcpComments"] = [data.comments] if data.comments else []
        
        if modifications:
            await self._ldap.modify(dn, modifications)
            logger.info("dhcp_class_updated", dn=dn)
        
        return await self.get_class(dn)
    
    async def delete_class(self, dn: str, recursive: bool = False) -> None:
        """Delete a class."""
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing is None:
            raise LdapNotFoundError(f"Class not found: {dn}")
        
        if recursive:
            await self._delete_children_recursive(dn)
        
        await self._ldap.delete(dn)
        logger.info("dhcp_class_deleted", dn=dn)
    
    # ========================================================================
    # SubClass CRUD Operations
    # ========================================================================
    
    async def get_subclass(self, dn: str) -> SubClassRead:
        """Get a subclass by DN."""
        entry = await self._ldap.get_by_dn(
            dn,
            attributes=self.COMMON_ATTRIBUTES + self.SUBCLASS_ATTRIBUTES,
        )
        
        if entry is None:
            raise LdapNotFoundError(f"SubClass not found: {dn}")
        
        return SubClassRead(
            dn=entry.dn or dn,
            cn=self._get_first_value(entry, "cn", ""),
            dhcpClassData=entry.get("dhcpClassData", [None])[0],
            dhcpStatements=entry.get("dhcpStatements", []),
            dhcpOption=entry.get("dhcpOption", []),
            dhcpComments=entry.get("dhcpComments", [None])[0],
            parentDn=self._get_parent_dn(dn),
        )
    
    async def create_subclass(self, parent_dn: str, data: SubClassCreate) -> SubClassRead:
        """Create a new subclass under a class."""
        dn = self._get_object_dn(data.cn, parent_dn)
        
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing:
            raise DhcpValidationError(f"SubClass already exists: {data.cn}")
        
        attributes: Dict[str, List[Any]] = {
            "cn": [data.cn],
        }
        
        if data.dhcp_class_data:
            attributes["dhcpClassData"] = [data.dhcp_class_data]
        if data.dhcp_statements:
            attributes["dhcpStatements"] = data.dhcp_statements
        if data.dhcp_options:
            attributes["dhcpOption"] = data.dhcp_options
        if data.comments:
            attributes["dhcpComments"] = [data.comments]
        
        await self._ldap.add(
            dn=dn,
            object_classes=self.TYPE_OBJECT_CLASSES[DhcpObjectType.SUBCLASS],
            attributes=attributes,
        )
        
        logger.info("dhcp_subclass_created", cn=data.cn, dn=dn)
        
        return await self.get_subclass(dn)
    
    async def update_subclass(self, dn: str, data: SubClassUpdate) -> SubClassRead:
        """Update a subclass."""
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing is None:
            raise LdapNotFoundError(f"SubClass not found: {dn}")
        
        modifications: Dict[str, List[Any]] = {}
        
        if data.dhcp_class_data is not None:
            modifications["dhcpClassData"] = [data.dhcp_class_data] if data.dhcp_class_data else []
        if data.dhcp_statements is not None:
            modifications["dhcpStatements"] = data.dhcp_statements
        if data.dhcp_options is not None:
            modifications["dhcpOption"] = data.dhcp_options
        if data.comments is not None:
            modifications["dhcpComments"] = [data.comments] if data.comments else []
        
        if modifications:
            await self._ldap.modify(dn, modifications)
            logger.info("dhcp_subclass_updated", dn=dn)
        
        return await self.get_subclass(dn)
    
    async def delete_subclass(self, dn: str) -> None:
        """Delete a subclass."""
        existing = await self._ldap.get_by_dn(dn, attributes=["cn"])
        if existing is None:
            raise LdapNotFoundError(f"SubClass not found: {dn}")
        
        await self._ldap.delete(dn)
        logger.info("dhcp_subclass_deleted", dn=dn)
    
    # ========================================================================
    # TSIG Key CRUD Operations
    # ========================================================================
    
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
            attributes=self.COMMON_ATTRIBUTES + ["dhcpKeyAlgorithm"],  # Don't fetch secret
            scope="subtree",
        )
        
        items = [
            TsigKeyListItem(
                dn=entry.dn,
                cn=self._get_first_value(entry, "cn", ""),
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
            attributes=self.COMMON_ATTRIBUTES + ["dhcpKeyAlgorithm"],
        )
        
        if entry is None:
            raise LdapNotFoundError(f"TSIG key not found: {dn}")
        
        return TsigKeyRead(
            dn=entry.dn or dn,
            cn=self._get_first_value(entry, "cn", ""),
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
            object_classes=self.TYPE_OBJECT_CLASSES[DhcpObjectType.TSIG_KEY],
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
    
    # ========================================================================
    # DNS Zone CRUD Operations
    # ========================================================================
    
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
            attributes=self.COMMON_ATTRIBUTES + self.DNS_ZONE_ATTRIBUTES,
            scope="subtree",
        )
        
        items = [
            DnsZoneListItem(
                dn=entry.dn,
                cn=self._get_first_value(entry, "cn", ""),
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
            attributes=self.COMMON_ATTRIBUTES + self.DNS_ZONE_ATTRIBUTES,
        )
        
        if entry is None:
            raise LdapNotFoundError(f"DNS zone not found: {dn}")
        
        return DnsZoneRead(
            dn=entry.dn or dn,
            cn=self._get_first_value(entry, "cn", ""),
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
            object_classes=self.TYPE_OBJECT_CLASSES[DhcpObjectType.DNS_ZONE],
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
    
    # ========================================================================
    # Failover Peer CRUD Operations
    # ========================================================================
    
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
            attributes=self.COMMON_ATTRIBUTES + self.FAILOVER_PEER_ATTRIBUTES,
            scope="subtree",
        )
        
        items = [
            FailoverPeerListItem(
                dn=entry.dn,
                cn=self._get_first_value(entry, "cn", ""),
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
            attributes=self.COMMON_ATTRIBUTES + self.FAILOVER_PEER_ATTRIBUTES,
        )
        
        if entry is None:
            raise LdapNotFoundError(f"Failover peer not found: {dn}")
        
        return FailoverPeerRead(
            dn=entry.dn or dn,
            cn=self._get_first_value(entry, "cn", ""),
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
            object_classes=self.TYPE_OBJECT_CLASSES[DhcpObjectType.FAILOVER_PEER],
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
    
    # ========================================================================
    # Tree Operations
    # ========================================================================
    
    async def get_service_tree(self, service_cn: str) -> DhcpTreeResponse:
        """Get the full DHCP configuration tree for a service."""
        service = await self.get_service(service_cn)
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
        comments = self._get_first_value(entry, "dhcpComments") if entry else None
        
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
                child_cn = self._get_first_value(child_entry, "cn", "")
                
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
    
    # ========================================================================
    # Systems Integration
    # ========================================================================
    
    async def get_host_by_mac(self, mac_address: str) -> Optional[HostRead]:
        """Find a DHCP host by MAC address."""
        # Normalize MAC format
        from .schemas import validate_mac_address
        try:
            normalized_mac = validate_mac_address(mac_address)
        except ValueError:
            return None
        
        entries = await self._ldap.search(
            search_base=self._dhcp_dn,
            search_filter=f"(&(objectClass=dhcpHost)(dhcpHWAddress={normalized_mac}))",
            attributes=self.COMMON_ATTRIBUTES + self.HOST_ATTRIBUTES,
            scope="subtree",
        )
        
        if not entries:
            return None
        
        entry = entries[0]
        statements = entry.get("dhcpStatements", [])
        fixed_addr = self._extract_fixed_address(statements)
        
        return HostRead(
            dn=entry.dn,
            cn=self._get_first_value(entry, "cn", ""),
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
            attributes=self.COMMON_ATTRIBUTES + self.HOST_ATTRIBUTES,
            scope="subtree",
        )
        
        hosts = []
        for entry in entries:
            statements = entry.get("dhcpStatements", [])
            fixed_addr = self._extract_fixed_address(statements)
            
            hosts.append(HostRead(
                dn=entry.dn,
                cn=self._get_first_value(entry, "cn", ""),
                dhcpHWAddress=entry.get("dhcpHWAddress", [None])[0],
                fixedAddress=fixed_addr,
                dhcpStatements=statements,
                dhcpOption=entry.get("dhcpOption", []),
                dhcpComments=entry.get("dhcpComments", [None])[0],
                parentDn=self._get_parent_dn(entry.dn),
            ))
        
        return hosts

    # ========================================================================
    # TabService Abstract Method Implementations
    # ========================================================================
    # Note: DHCP is a standalone management plugin, not a tab on user/group objects.
    # These methods implement the TabService interface for compatibility.

    async def is_active(self, dn: str) -> bool:
        """
        Check if DHCP attributes exist at the given DN.
        
        For DHCP, this checks if the DN has any DHCP objectClass.
        """
        try:
            entry = await self._ldap.get_by_dn(dn, attributes=["objectClass"])
            if entry is None:
                return False

            object_classes = {oc.lower() for oc in entry.get("objectClass", [])}
            dhcp_classes = {
                "dhcpservice", "dhcpsubnet", "dhcppool", "dhcphost",
                "dhcpsharednetwork", "dhcpgroup", "dhcpclass", "dhcpsubclass",
                "dhcptsigkey", "dhcpdnszone", "dhcpfailoverpeer"
            }
            return bool(object_classes & dhcp_classes)
        except Exception:
            return False

    async def read(self, dn: str) -> Optional[Dict[str, Any]]:
        """
        Read a DHCP object by DN.
        
        Returns the raw DHCP entry data.
        """
        try:
            entry = await self._ldap.get_by_dn(
                dn,
                attributes=["*"]
            )
            if entry is None:
                return None

            return dict(entry)
        except Exception:
            return None

    async def activate(self, dn: str, data: Any) -> Any:
        """
        Activate DHCP on an object.
        
        Not applicable for DHCP standalone management.
        """
        raise NotImplementedError(
            "DHCP is a standalone management plugin. "
            "Use create_service(), create_subnet(), create_host() etc. instead."
        )

    async def update(self, dn: str, data: Any) -> Any:
        """
        Update a DHCP object by DN.
        
        For generic updates, use the specific update methods.
        """
        raise NotImplementedError(
            "Use specific update methods: update_service(), update_subnet(), "
            "update_host(), update_pool() etc."
        )

    async def deactivate(self, dn: str) -> None:
        """
        Deactivate/delete a DHCP object by DN.
        
        For deletions, use the specific delete methods.
        """
        raise NotImplementedError(
            "Use specific delete methods: delete_service(), delete_subnet(), "
            "delete_host(), delete_pool() etc."
        )
