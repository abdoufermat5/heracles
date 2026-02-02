"""
Host Operations
===============

Host validation operations for use by other plugins.
"""

from typing import Any, List, TYPE_CHECKING

import structlog

from heracles_api.services.ldap_service import LdapOperationError

if TYPE_CHECKING:
    from ..base import SystemServiceBase

from ...schemas import SystemType, HostValidationResponse


logger = structlog.get_logger(__name__)


class HostOperationsMixin:
    """Mixin providing host validation methods for other plugins."""
    
    # Type hints for mixin
    _ldap: Any
    _systems_dn: str
    
    async def validate_hosts(self: "SystemServiceBase", hostnames: List[str]) -> HostValidationResponse:
        """
        Validate that hostnames exist as registered systems.
        
        This method is used by other plugins (like POSIX) to validate
        host attributes against actual systems in the directory.
        
        Args:
            hostnames: List of hostnames to validate
            
        Returns:
            HostValidationResponse with valid and invalid hosts
        """
        if not hostnames:
            return HostValidationResponse(valid_hosts=[], invalid_hosts=[])
        
        valid_hosts = []
        invalid_hosts = []
        
        # Build filter to find any of the hostnames
        # Hostnames are stored as CN in systems
        escaped_names = [self._ldap._escape_filter(h) for h in hostnames]
        cn_filters = [f"(cn={name})" for name in escaped_names]
        
        # Match any of our system types
        type_filters = [
            f"(objectClass={SystemType.get_object_class(t)})"
            for t in SystemType
        ]
        
        search_filter = f"(&(|{''.join(type_filters)})(|{''.join(cn_filters)}))"
        
        try:
            entries = await self._ldap.search(
                search_base=self._systems_dn,
                search_filter=search_filter,
                attributes=["cn"],
            )
            
            # Extract found CNs
            found_cns = set()
            for entry in entries:
                cn = entry.get_first("cn") if hasattr(entry, 'get_first') else entry.get("cn", [""])[0]
                if cn:
                    found_cns.add(cn.lower())
            
            # Categorize hostnames
            for hostname in hostnames:
                if hostname.lower() in found_cns:
                    valid_hosts.append(hostname)
                else:
                    invalid_hosts.append(hostname)
            
        except LdapOperationError as e:
            logger.warning("host_validation_failed", error=str(e))
            # On error, mark all as invalid (strict mode)
            invalid_hosts = hostnames
        
        return HostValidationResponse(
            valid_hosts=valid_hosts,
            invalid_hosts=invalid_hosts,
        )
    
    async def host_exists(self: "SystemServiceBase", hostname: str) -> bool:
        """Check if a hostname exists as a registered system."""
        result = await self.validate_hosts([hostname])
        return len(result.valid_hosts) > 0
    
    async def get_all_hostnames(self: "SystemServiceBase") -> List[str]:
        """Get all registered system hostnames (for autocomplete)."""
        try:
            # Match any of our system types
            type_filters = [
                f"(objectClass={SystemType.get_object_class(t)})"
                for t in SystemType
            ]
            search_filter = f"(|{''.join(type_filters)})"
            
            entries = await self._ldap.search(
                search_base=self._systems_dn,
                search_filter=search_filter,
                attributes=["cn"],
            )
            
            hostnames = []
            for entry in entries:
                cn = entry.get_first("cn") if hasattr(entry, 'get_first') else entry.get("cn", [""])[0]
                if cn:
                    hostnames.append(cn)
            
            return sorted(hostnames)
            
        except LdapOperationError as e:
            logger.warning("get_all_hostnames_failed", error=str(e))
            return []
