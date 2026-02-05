"""
ACL Guard
=========

Thin wrapper around the Rust ACL engine for endpoint usage.
Provides a convenient API for permission checks and attribute filtering.
"""

import structlog
from typing import Optional

from fastapi import HTTPException, status

from heracles_api.acl.registry import PermissionRegistry

logger = structlog.get_logger(__name__)


class AclGuard:
    """
    High-level ACL guard for API endpoints.
    
    Wraps the compiled PyUserAcl and provides convenient methods
    for permission checks with proper error handling.
    
    Usage:
        @router.get("/users/{uid}")
        async def get_user(uid: str, guard: AclGuardDep):
            target_dn = f"uid={uid},ou=users,{base_dn}"
            guard.require(target_dn, "user:read")
            
            user = await user_repo.find_by_uid(uid)
            visible = guard.filter_read(target_dn, "user", list(user.keys()))
            return {k: v for k, v in user.items() if k in visible}
    """
    
    def __init__(
        self,
        acl: "PyUserAcl",
        registry: PermissionRegistry,
        user_dn: str,
    ):
        """
        Initialize the ACL guard.
        
        Args:
            acl: Compiled PyUserAcl from Rust engine.
            registry: Permission registry for name→bitmap conversion.
            user_dn: The current user's DN.
        """
        self._acl = acl
        self._reg = registry
        self._user_dn = user_dn
    
    @property
    def user_dn(self) -> str:
        """Get the current user's DN."""
        return self._user_dn
    
    def require(self, target_dn: str, *permissions: str) -> None:
        """
        Require ALL of the listed permissions.
        
        Raises HTTP 403 if ANY permission is denied.
        
        Args:
            target_dn: The DN of the object being accessed.
            *permissions: Permission names like "user:read", "user:write".
            
        Raises:
            HTTPException: 403 if permission denied.
        """
        low, high = self._reg.bitmap(*permissions)
        
        if not self._acl.check(target_dn, low, high):
            logger.warning(
                "acl_denied",
                user_dn=self._user_dn,
                target_dn=target_dn,
                permissions=permissions,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "ACL_DENIED",
                        "message": "Permission denied",
                    }
                },
            )
    
    def require_any(self, target_dn: str, *permissions: str) -> None:
        """
        Require ANY of the listed permissions.
        
        Raises HTTP 403 if NONE of the permissions are granted.
        
        Args:
            target_dn: The DN of the object being accessed.
            *permissions: Permission names (at least one must be granted).
            
        Raises:
            HTTPException: 403 if no permission granted.
        """
        for perm in permissions:
            if self.can(target_dn, perm):
                return
        
        logger.warning(
            "acl_denied_any",
            user_dn=self._user_dn,
            target_dn=target_dn,
            permissions=permissions,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "ACL_DENIED",
                    "message": "Permission denied",
                }
            },
        )
    
    def can(self, target_dn: str, permission: str) -> bool:
        """
        Check a single permission without raising.
        
        Args:
            target_dn: The DN of the object being accessed.
            permission: Permission name like "user:read".
            
        Returns:
            True if permitted, False otherwise.
        """
        try:
            low, high = self._reg.bitmap(permission)
            return self._acl.check(target_dn, low, high)
        except KeyError:
            logger.error("unknown_permission", permission=permission)
            return False
    
    def can_all(self, target_dn: str, *permissions: str) -> bool:
        """
        Check if ALL permissions are granted.
        
        Args:
            target_dn: The DN of the object being accessed.
            *permissions: Permission names.
            
        Returns:
            True if all permitted, False otherwise.
        """
        try:
            low, high = self._reg.bitmap(*permissions)
            return self._acl.check(target_dn, low, high)
        except KeyError:
            return False
    
    def can_any(self, target_dn: str, *permissions: str) -> bool:
        """
        Check if ANY permission is granted.
        
        Args:
            target_dn: The DN of the object being accessed.
            *permissions: Permission names.
            
        Returns:
            True if any permitted, False otherwise.
        """
        for perm in permissions:
            if self.can(target_dn, perm):
                return True
        return False
    
    def can_attribute(
        self,
        target_dn: str,
        permission: str,
        object_type: str,
        action: str,
        attribute: str,
    ) -> bool:
        """
        Check object-level + attribute-level permission.
        
        Args:
            target_dn: The DN of the object.
            permission: Base permission (e.g., "user:read").
            object_type: Object type (e.g., "user").
            action: Action ("read" or "write").
            attribute: Specific attribute name.
            
        Returns:
            True if the attribute is accessible, False otherwise.
        """
        try:
            low, high = self._reg.bitmap(permission)
            return self._acl.check_attribute(
                target_dn, low, high, object_type, action, attribute
            )
        except KeyError:
            return False
    
    def filter_read(
        self,
        target_dn: str,
        object_type: str,
        attributes: list[str],
        permission: str = None,
    ) -> list[str]:
        """
        Filter attributes for a read operation.
        
        Returns only the attributes the user is allowed to read.
        
        Args:
            target_dn: The DN of the object.
            object_type: Object type (e.g., "user").
            attributes: List of attribute names to filter.
            permission: Base permission (default: "{object_type}:read").
            
        Returns:
            Filtered list of readable attributes.
        """
        permission = permission or f"{object_type}:read"
        try:
            low, high = self._reg.bitmap(permission)
            return self._acl.filter_attributes(
                target_dn, low, high, object_type, "read", attributes
            )
        except KeyError:
            return []
    
    def filter_write(
        self,
        target_dn: str,
        object_type: str,
        attributes: list[str],
        permission: str = None,
    ) -> list[str]:
        """
        Filter attributes for a write operation.
        
        Returns only the attributes the user is allowed to write.
        
        Args:
            target_dn: The DN of the object.
            object_type: Object type (e.g., "user").
            attributes: List of attribute names to filter.
            permission: Base permission (default: "{object_type}:write").
            
        Returns:
            Filtered list of writable attributes.
        """
        permission = permission or f"{object_type}:write"
        try:
            low, high = self._reg.bitmap(permission)
            return self._acl.filter_attributes(
                target_dn, low, high, object_type, "write", attributes
            )
        except KeyError:
            return []
    
    def filter_data_read(
        self,
        target_dn: str,
        object_type: str,
        data: dict,
        permission: str = None,
    ) -> dict:
        """
        Filter a data dictionary for read, keeping only readable keys.
        
        Args:
            target_dn: The DN of the object.
            object_type: Object type (e.g., "user").
            data: Dictionary of attribute→value.
            permission: Base permission.
            
        Returns:
            Filtered dictionary with only readable attributes.
        """
        readable = set(self.filter_read(
            target_dn, object_type, list(data.keys()), permission
        ))
        return {k: v for k, v in data.items() if k in readable}
    
    def filter_data_write(
        self,
        target_dn: str,
        object_type: str,
        data: dict,
        permission: str = None,
    ) -> dict:
        """
        Filter a data dictionary for write, keeping only writable keys.
        
        Args:
            target_dn: The DN of the object.
            object_type: Object type (e.g., "user").
            data: Dictionary of attribute→value to write.
            permission: Base permission.
            
        Returns:
            Filtered dictionary with only writable attributes.
        """
        writable = set(self.filter_write(
            target_dn, object_type, list(data.keys()), permission
        ))
        return {k: v for k, v in data.items() if k in writable}
    
    def is_self(self, target_dn: str) -> bool:
        """
        Check if target_dn is the user's own entry.
        
        Useful for self-service checks.
        """
        return self._acl.is_self(target_dn)
    
    def effective_permissions(self, target_dn: str) -> list[str]:
        """
        Get list of effective permission names for a target DN.
        
        Useful for debugging and UI permission display.
        """
        bitmap = self._acl.effective_permissions(target_dn)
        bits = bitmap.to_bits()
        
        result = []
        for bit in bits:
            try:
                result.append(self._reg.name(bit))
            except KeyError:
                result.append(f"bit:{bit}")
        
        return result


class AclGuardFactory:
    """
    Factory for creating AclGuard instances.
    
    Used as a FastAPI dependency to create guards for each request.
    """
    
    def __init__(self, registry: PermissionRegistry):
        """
        Initialize the factory.
        
        Args:
            registry: Permission registry (shared across requests).
        """
        self.registry = registry
    
    def create(self, acl: "PyUserAcl", user_dn: str) -> AclGuard:
        """
        Create an AclGuard for a request.
        
        Args:
            acl: Compiled PyUserAcl for the current user.
            user_dn: The current user's DN.
            
        Returns:
            AclGuard instance for permission checks.
        """
        return AclGuard(acl, self.registry, user_dn)
