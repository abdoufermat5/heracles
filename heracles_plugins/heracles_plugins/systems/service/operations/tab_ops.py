"""
Tab Operations
==============

TabService abstract method implementations.
"""

from typing import Any, Optional, TYPE_CHECKING

from heracles_api.services.ldap_service import LdapNotFoundError

if TYPE_CHECKING:
    from ..base import SystemServiceBase

from ...schemas import SystemType, SystemCreate, SystemRead, SystemUpdate
from ..base import SystemValidationError


class TabOperationsMixin:
    """Mixin providing TabService abstract method implementations."""
    
    # Type hints for mixin
    _ldap: Any
    get_system: Any
    create_system: Any
    update_system: Any
    delete_system: Any
    
    async def is_active(self: "SystemServiceBase", dn: str) -> bool:
        """
        Check if a system exists at the given DN.
        
        For standalone objects like systems, this checks if the entry exists.
        """
        try:
            entry = await self._ldap.get_by_dn(dn, attributes=["objectClass"])
            if entry is None:
                return False
            
            # Check if any system objectClass is present
            object_classes = {oc.lower() for oc in entry.get("objectClass", [])}
            system_classes = {"hrcserver", "hrcworkstation", "hrcterminal", 
                            "hrcprinter", "device", "hrcphone", "hrcmobilephone"}
            return bool(object_classes & system_classes)
        except Exception:
            return False
    
    async def read(self: "SystemServiceBase", dn: str) -> Optional[SystemRead]:
        """
        Read a system by DN.
        
        Extracts the CN and system type from the DN to use get_system.
        """
        try:
            entry = await self._ldap.get_by_dn(dn, attributes=["objectClass", "cn"])
            if entry is None:
                return None
            
            cn = entry.get("cn", [None])[0]
            if not cn:
                return None
            
            # Determine system type from objectClass
            object_classes = {oc.lower() for oc in entry.get("objectClass", [])}
            system_type = None
            for oc in object_classes:
                system_type = SystemType.from_object_class(oc)
                if system_type:
                    break
            
            if not system_type:
                return None
            
            return await self.get_system(cn, system_type)
        except Exception:
            return None
    
    async def activate(self: "SystemServiceBase", dn: str, data: SystemCreate) -> SystemRead:
        """
        Create/activate a system.
        
        For standalone objects, this is equivalent to create_system.
        """
        return await self.create_system(data)
    
    async def update(self: "SystemServiceBase", dn: str, data: SystemUpdate) -> SystemRead:
        """
        Update a system by DN.
        
        Extracts CN and type from DN to use update_system.
        """
        # Parse CN from DN
        cn_part = dn.split(",")[0]
        if "=" in cn_part:
            cn = cn_part.split("=")[1]
        else:
            raise SystemValidationError(f"Invalid DN format: {dn}")
        
        # Get existing entry to determine type
        entry = await self._ldap.get_by_dn(dn, attributes=["objectClass"])
        if entry is None:
            raise LdapNotFoundError(f"System not found: {dn}")
        
        object_classes = {oc.lower() for oc in entry.get("objectClass", [])}
        system_type = None
        for oc in object_classes:
            system_type = SystemType.from_object_class(oc)
            if system_type:
                break
        
        if not system_type:
            raise SystemValidationError(f"Could not determine system type for: {dn}")
        
        return await self.update_system(cn, system_type, data)
    
    async def deactivate(self: "SystemServiceBase", dn: str) -> None:
        """
        Delete/deactivate a system.
        
        For standalone objects, this deletes the entry.
        """
        # Parse CN from DN
        cn_part = dn.split(",")[0]
        if "=" in cn_part:
            cn = cn_part.split("=")[1]
        else:
            raise SystemValidationError(f"Invalid DN format: {dn}")
        
        # Get existing entry to determine type
        entry = await self._ldap.get_by_dn(dn, attributes=["objectClass"])
        if entry is None:
            raise LdapNotFoundError(f"System not found: {dn}")
        
        object_classes = {oc.lower() for oc in entry.get("objectClass", [])}
        system_type = None
        for oc in object_classes:
            system_type = SystemType.from_object_class(oc)
            if system_type:
                break
        
        if not system_type:
            raise SystemValidationError(f"Could not determine system type for: {dn}")
        
        await self.delete_system(cn, system_type)
