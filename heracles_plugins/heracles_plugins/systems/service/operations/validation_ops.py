"""
Validation Operations
=====================

System validation and uniqueness checking operations.
"""

from typing import Any, List, Optional, TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from ..base import SystemServiceBase

from ...schemas import SystemCreate


logger = structlog.get_logger(__name__)


class ValidationOperationsMixin:
    """Mixin providing validation and uniqueness checking methods."""
    
    # Type hints for mixin
    _ldap: Any
    _get_validation_config: Any
    _get_systems_container: Any
    
    async def _check_hostname_uniqueness(
        self: "SystemServiceBase", 
        hostname: str, 
        exclude_dn: Optional[str] = None,
        base_dn: Optional[str] = None
    ) -> Optional[str]:
        """
        Check if hostname is unique across all system types.
        
        Returns error message if duplicate found, None if unique.
        """
        config = await self._get_validation_config()
        
        if not config.get("require_unique_hostname", True):
            return None
        
        # Search across all system types
        search_base = self._get_systems_container(base_dn)
        search_filter = f"(cn={self._ldap._escape_filter(hostname)})"
        
        try:
            entries = await self._ldap.search(
                search_base=search_base,
                search_filter=search_filter,
                attributes=["cn"],
                size_limit=2,  # Only need to find one duplicate
            )
            
            for entry in entries:
                if exclude_dn and entry.dn == exclude_dn:
                    continue
                return f"Hostname '{hostname}' is already in use"
            
            return None
            
        except Exception as e:
            logger.warning("hostname_uniqueness_check_error", hostname=hostname, error=str(e))
            return None
    
    async def _check_ip_uniqueness(
        self: "SystemServiceBase", 
        ip_addresses: List[str],
        exclude_dn: Optional[str] = None,
        base_dn: Optional[str] = None
    ) -> List[str]:
        """
        Check if IP addresses are unique.
        
        Returns list of error messages for duplicates.
        """
        config = await self._get_validation_config()
        
        if not config.get("require_unique_ip", False):
            return []
        
        errors = []
        search_base = self._get_systems_container(base_dn)
        
        for ip in ip_addresses:
            search_filter = f"(ipHostNumber={self._ldap._escape_filter(ip)})"
            
            try:
                entries = await self._ldap.search(
                    search_base=search_base,
                    search_filter=search_filter,
                    attributes=["cn", "ipHostNumber"],
                    size_limit=2,
                )
                
                for entry in entries:
                    if exclude_dn and entry.dn == exclude_dn:
                        continue
                    errors.append(f"IP address '{ip}' is already assigned to '{entry.get_first('cn')}'")
                    break
                    
            except Exception as e:
                logger.warning("ip_uniqueness_check_error", ip=ip, error=str(e))
        
        return errors
    
    async def _check_mac_uniqueness(
        self: "SystemServiceBase", 
        mac_addresses: List[str],
        exclude_dn: Optional[str] = None,
        base_dn: Optional[str] = None
    ) -> List[str]:
        """
        Check if MAC addresses are unique.
        
        Returns list of error messages for duplicates.
        """
        config = await self._get_validation_config()
        
        if not config.get("require_unique_mac", True):
            return []
        
        errors = []
        search_base = self._get_systems_container(base_dn)
        
        for mac in mac_addresses:
            # Normalize MAC to uppercase for search
            mac_upper = mac.upper()
            search_filter = f"(macAddress={self._ldap._escape_filter(mac_upper)})"
            
            try:
                entries = await self._ldap.search(
                    search_base=search_base,
                    search_filter=search_filter,
                    attributes=["cn", "macAddress"],
                    size_limit=2,
                )
                
                for entry in entries:
                    if exclude_dn and entry.dn == exclude_dn:
                        continue
                    errors.append(f"MAC address '{mac}' is already assigned to '{entry.get_first('cn')}'")
                    break
                    
            except Exception as e:
                logger.warning("mac_uniqueness_check_error", mac=mac, error=str(e))
        
        return errors
    
    async def validate_system(
        self: "SystemServiceBase", 
        data: SystemCreate,
        exclude_dn: Optional[str] = None,
        base_dn: Optional[str] = None
    ) -> List[str]:
        """
        Validate a system against config-based rules.
        
        Checks:
        - Hostname uniqueness (if enabled)
        - IP address uniqueness (if enabled)
        - MAC address uniqueness (if enabled)
        
        Returns:
            List of validation errors (empty if all valid)
        """
        errors = []
        
        # Check hostname uniqueness
        hostname_error = await self._check_hostname_uniqueness(data.cn, exclude_dn, base_dn)
        if hostname_error:
            errors.append(hostname_error)
        
        # Check IP uniqueness
        if data.ip_addresses:
            ip_errors = await self._check_ip_uniqueness(data.ip_addresses, exclude_dn, base_dn)
            errors.extend(ip_errors)
        
        # Check MAC uniqueness
        if data.mac_addresses:
            mac_errors = await self._check_mac_uniqueness(data.mac_addresses, exclude_dn, base_dn)
            errors.extend(mac_errors)
        
        return errors
