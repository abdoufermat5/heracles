"""
DNS Service Base
================

Common functionality for DNS service operations.
Includes DN building, configuration, and OU management.
"""

from typing import Any, Dict, Optional

import structlog

from heracles_api.services.ldap_service import (
    LdapService,
    LdapOperationError,
)

from .constants import DNS_BASE_RDN

logger = structlog.get_logger(__name__)


class DnsValidationError(Exception):
    """Raised when DNS validation fails."""
    pass


class DnsServiceBase:
    """
    Base class for DNS service operations.
    
    Provides common functionality:
    - Configuration management
    - DN building utilities
    - OU management
    
    Directory structure:
        ou=dns,dc=example,dc=org                    # DNS container
        └── zoneName=example.org,ou=dns,...         # Zone entry (@ records, SOA, NS)
            │                                       # Has relativeDomainName=@ as attribute
            ├── relativeDomainName=www,...          # www.example.org
            ├── relativeDomainName=mail,...         # mail.example.org
            ├── relativeDomainName=_sip._tcp,...    # SRV record
            └── zoneName=168.192.in-addr.arpa,...   # Reverse zone (nested)
    """

    def __init__(self, ldap_service: LdapService, config: Dict[str, Any]):
        self._ldap = ldap_service
        self._config = config

        # Configuration
        self._dns_rdn = config.get("dns_rdn", DNS_BASE_RDN)
        self._base_dn = config.get("base_dn", ldap_service.base_dn)
        self._dns_base_dn = f"{self._dns_rdn},{self._base_dn}"
        self._default_ttl = config.get("default_ttl", 3600)

    def get_dns_dn(self) -> str:
        """Get the DNS container DN (e.g. ou=dns,dc=heracles,dc=local)."""
        return self._dns_base_dn

    # ========================================================================
    # DN Building Utilities
    # ========================================================================

    def _get_dns_container(self, base_dn: Optional[str] = None) -> str:
        """Get the DNS container DN for the given context.
        
        If base_dn is provided (department context), returns ou=dns,{base_dn}.
        Otherwise returns the default ou=dns,{root_base_dn}.
        """
        if base_dn:
            return f"{self._dns_rdn},{base_dn}"
        return self._dns_base_dn

    def _get_zone_dn(self, zone_name: str, base_dn: Optional[str] = None) -> str:
        """Get the DN for a zone entry (the @ apex record)."""
        container = self._get_dns_container(base_dn)
        return f"zoneName={zone_name},{container}"

    def _get_record_dn(self, zone_name: str, name: str, base_dn: Optional[str] = None) -> str:
        """
        Get the DN for a record entry.
        
        For compatibility:
        - @ (apex) records are stored at the zone entry itself (zoneName=X,ou=dns,...)
        - Other records are children (relativeDomainName=www,zoneName=X,ou=dns,...)
        """
        zone_dn = self._get_zone_dn(zone_name, base_dn=base_dn)
        if name == "@":
            # Apex record is the zone entry itself
            return zone_dn
        return f"relativeDomainName={name},{zone_dn}"

    # ========================================================================
    # OU Management
    # ========================================================================

    async def _ensure_dns_ou(self) -> None:
        """Ensure the DNS OU exists."""
        try:
            exists = await self._ldap.get_by_dn(
                self._dns_base_dn,
                attributes=["ou"]
            )
            if exists is None:
                await self._ldap.add(
                    dn=self._dns_base_dn,
                    object_classes=["organizationalUnit"],
                    attributes={"ou": ["dns"]},
                )
                logger.info("dns_ou_created", dn=self._dns_base_dn)
        except LdapOperationError as e:
            logger.warning("dns_ou_check_failed", error=str(e))
