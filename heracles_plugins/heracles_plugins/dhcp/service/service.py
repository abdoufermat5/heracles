"""
DHCP Service
============

Main DHCP service class that composes all operation mixins.
Provides a unified interface for DHCP configuration management.
"""

from typing import Any, Dict, Optional

import structlog

from heracles_api.plugins.base import TabService
from heracles_api.services.ldap_service import LdapService

from .base import DhcpServiceBase, DhcpValidationError
from .operations import (
    ServiceOperationsMixin,
    SubnetOperationsMixin,
    PoolOperationsMixin,
    HostOperationsMixin,
    SharedNetworkOperationsMixin,
    GroupOperationsMixin,
    ClassOperationsMixin,
    TsigKeyOperationsMixin,
    DnsZoneOperationsMixin,
    FailoverPeerOperationsMixin,
    TreeOperationsMixin,
)

logger = structlog.get_logger(__name__)


class DhcpService(
    ServiceOperationsMixin,
    SubnetOperationsMixin,
    PoolOperationsMixin,
    HostOperationsMixin,
    SharedNetworkOperationsMixin,
    GroupOperationsMixin,
    ClassOperationsMixin,
    TsigKeyOperationsMixin,
    DnsZoneOperationsMixin,
    FailoverPeerOperationsMixin,
    TreeOperationsMixin,
    TabService,
):
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
    
    This class composes multiple operation mixins to provide
    a clean separation of concerns while maintaining a unified API.
    """

    def __init__(self, ldap_service: LdapService, config: Dict[str, Any]):
        # Initialize TabService first
        TabService.__init__(self, ldap_service, config)
        
        # Initialize base (shared by all mixins via MRO)
        DhcpServiceBase.__init__(self, ldap_service, config)
    
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


# Re-export DhcpValidationError for backward compatibility
__all__ = ["DhcpService", "DhcpValidationError"]
