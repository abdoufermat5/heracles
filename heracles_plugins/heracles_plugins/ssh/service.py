"""
SSH Plugin Service
==================

Business logic for managing SSH public keys on user accounts.
"""

from typing import Optional, List, Any, Dict
from datetime import datetime

import structlog

from heracles_api.plugins.base import TabService
from heracles_api.services.ldap_service import (
    LdapService,
    LdapOperationError,
    LdapNotFoundError,
)

from .schemas import (
    SSHKeyCreate,
    SSHKeyRead,
    SSHKeyUpdate,
    UserSSHStatus,
    UserSSHActivate,
    UserSSHKeysUpdate,
    parse_ssh_key,
    compute_fingerprint,
    SSH_KEY_TYPES,
)


logger = structlog.get_logger(__name__)


class SSHService(TabService):
    """
    Service for managing SSH public keys.
    
    Manages the ldapPublicKey objectClass and sshPublicKey attribute.
    
    LDAP Schema:
        objectClass: ldapPublicKey (auxiliary)
        attribute: sshPublicKey (multi-valued)
    """
    
    OBJECT_CLASS = "ldapPublicKey"
    SSH_KEY_ATTRIBUTE = "sshPublicKey"
    
    def __init__(self, ldap_service: LdapService, config: Optional[Dict[str, Any]] = None):
        """Initialize SSH service."""
        self._ldap = ldap_service
        self._config = config or {}
        self._log = logger.bind(service="ssh")
    
    # ========================================================================
    # User SSH Status
    # ========================================================================
    
    async def get_user_ssh_status(self, uid: str) -> UserSSHStatus:
        """
        Get SSH status for a user.
        
        Args:
            uid: User ID to check
            
        Returns:
            UserSSHStatus with key information
            
        Raises:
            LdapNotFoundError: If user not found
        """
        # Find user
        user_dn = await self._find_user_dn(uid)
        
        # Get user entry
        entry = await self._ldap.get_by_dn(
            user_dn,
            attributes=["objectClass", self.SSH_KEY_ATTRIBUTE],
        )
        
        if not entry:
            raise LdapNotFoundError(f"User {uid} not found")
        
        # Check for SSH objectClass
        object_classes = entry.get("objectClass", [])
        if isinstance(object_classes, str):
            object_classes = [object_classes]
        
        has_ssh = self.OBJECT_CLASS in object_classes
        
        # Parse SSH keys
        keys = []
        raw_keys = entry.get(self.SSH_KEY_ATTRIBUTE, [])
        if isinstance(raw_keys, str):
            raw_keys = [raw_keys]
        
        for raw_key in raw_keys:
            try:
                key_info = parse_ssh_key(raw_key)
                keys.append(SSHKeyRead(
                    key=raw_key,
                    keyType=key_info["key_type"],
                    fingerprint=key_info["fingerprint"],
                    comment=key_info["comment"],
                    bits=key_info["bits"],
                ))
            except ValueError as e:
                self._log.warning("invalid_ssh_key_in_ldap", uid=uid, error=str(e))
                # Still include malformed keys with minimal info
                keys.append(SSHKeyRead(
                    key=raw_key,
                    keyType="unknown",
                    fingerprint="invalid",
                    comment=None,
                    bits=None,
                ))
        
        return UserSSHStatus(
            uid=uid,
            dn=user_dn,
            hasSsh=has_ssh,
            keys=keys,
            keyCount=len(keys),
        )
    
    # ========================================================================
    # Activate/Deactivate SSH
    # ========================================================================
    
    async def activate_ssh(self, uid: str, data: Optional[UserSSHActivate] = None) -> UserSSHStatus:
        """
        Activate SSH for a user account.
        
        Adds ldapPublicKey objectClass to enable SSH key storage.
        
        Args:
            uid: User ID
            data: Optional initial key to add
            
        Returns:
            Updated UserSSHStatus
        """
        user_dn = await self._find_user_dn(uid)
        
        # Check current status
        status = await self.get_user_ssh_status(uid)
        
        if status.has_ssh:
            self._log.info("ssh_already_active", uid=uid)
            # If initial key provided, add it
            if data and data.initial_key:
                return await self.add_key(uid, SSHKeyCreate(key=data.initial_key))
            return status
        
        # Build modifications
        mods = {
            "objectClass": {
                "action": "add",
                "values": [self.OBJECT_CLASS],
            }
        }
        
        # Add initial key if provided
        if data and data.initial_key:
            # Validate key first
            parse_ssh_key(data.initial_key)
            mods[self.SSH_KEY_ATTRIBUTE] = {
                "action": "replace",
                "values": [data.initial_key],
            }
        
        # Apply modifications
        await self._ldap.modify(user_dn, mods)
        
        self._log.info("ssh_activated", uid=uid, with_key=bool(data and data.initial_key))
        
        return await self.get_user_ssh_status(uid)
    
    async def deactivate_ssh(self, uid: str) -> UserSSHStatus:
        """
        Deactivate SSH for a user account.
        
        Removes ldapPublicKey objectClass and all SSH keys.
        
        Args:
            uid: User ID
            
        Returns:
            Updated UserSSHStatus
        """
        user_dn = await self._find_user_dn(uid)
        
        # Check current status
        status = await self.get_user_ssh_status(uid)
        
        if not status.has_ssh:
            self._log.info("ssh_already_inactive", uid=uid)
            return status
        
        # Remove objectClass and keys
        mods = {
            "objectClass": {
                "action": "delete",
                "values": [self.OBJECT_CLASS],
            }
        }
        
        # Only remove sshPublicKey if there are keys
        if status.keys:
            mods[self.SSH_KEY_ATTRIBUTE] = {
                "action": "delete",
                "values": None,  # Delete all values
            }
        
        await self._ldap.modify(user_dn, mods)
        
        self._log.info("ssh_deactivated", uid=uid, keys_removed=len(status.keys))
        
        return await self.get_user_ssh_status(uid)
    
    # ========================================================================
    # Key Management
    # ========================================================================
    
    async def add_key(self, uid: str, data: SSHKeyCreate) -> UserSSHStatus:
        """
        Add an SSH key to a user account.
        
        Args:
            uid: User ID
            data: SSH key to add
            
        Returns:
            Updated UserSSHStatus
            
        Raises:
            ValueError: If key already exists or is invalid
        """
        user_dn = await self._find_user_dn(uid)
        
        # Get current status
        status = await self.get_user_ssh_status(uid)
        
        # Ensure SSH is activated
        if not status.has_ssh:
            await self.activate_ssh(uid)
        
        # Parse and validate key
        key_info = parse_ssh_key(data.key)
        new_fingerprint = key_info["fingerprint"]
        
        # Check for duplicate
        for existing_key in status.keys:
            if existing_key.fingerprint == new_fingerprint:
                raise ValueError(f"SSH key already exists: {new_fingerprint}")
        
        # Normalize key (add/update comment if provided)
        key_parts = data.key.split()[:2]  # Type and key data
        if data.comment:
            final_key = f"{key_parts[0]} {key_parts[1]} {data.comment}"
        else:
            final_key = data.key
        
        # Add key
        await self._ldap.modify(user_dn, {
            self.SSH_KEY_ATTRIBUTE: {
                "action": "add",
                "values": [final_key],
            }
        })
        
        self._log.info(
            "ssh_key_added",
            uid=uid,
            fingerprint=new_fingerprint,
            key_type=key_info["key_type"],
        )
        
        return await self.get_user_ssh_status(uid)
    
    async def remove_key(self, uid: str, fingerprint: str) -> UserSSHStatus:
        """
        Remove an SSH key from a user account by fingerprint.
        
        Args:
            uid: User ID
            fingerprint: SHA256 fingerprint of the key to remove
            
        Returns:
            Updated UserSSHStatus
            
        Raises:
            LdapNotFoundError: If key not found
        """
        user_dn = await self._find_user_dn(uid)
        
        # Get current status
        status = await self.get_user_ssh_status(uid)
        
        # Find key to remove
        key_to_remove = None
        for key in status.keys:
            if key.fingerprint == fingerprint:
                key_to_remove = key.key
                break
        
        if not key_to_remove:
            raise LdapNotFoundError(f"SSH key not found: {fingerprint}")
        
        # Remove key
        await self._ldap.modify(user_dn, {
            self.SSH_KEY_ATTRIBUTE: {
                "action": "delete",
                "values": [key_to_remove],
            }
        })
        
        self._log.info("ssh_key_removed", uid=uid, fingerprint=fingerprint)
        
        return await self.get_user_ssh_status(uid)
    
    async def update_keys(self, uid: str, data: UserSSHKeysUpdate) -> UserSSHStatus:
        """
        Replace all SSH keys for a user.
        
        Args:
            uid: User ID
            data: Complete list of keys
            
        Returns:
            Updated UserSSHStatus
        """
        user_dn = await self._find_user_dn(uid)
        
        # Ensure SSH is activated
        status = await self.get_user_ssh_status(uid)
        if not status.has_ssh:
            await self.activate_ssh(uid)
        
        # Validate all keys and check for duplicates
        fingerprints = set()
        for key in data.keys:
            key_info = parse_ssh_key(key)
            fp = key_info["fingerprint"]
            if fp in fingerprints:
                raise ValueError(f"Duplicate key in request: {fp}")
            fingerprints.add(fp)
        
        # Replace all keys
        if data.keys:
            await self._ldap.modify(user_dn, {
                self.SSH_KEY_ATTRIBUTE: {
                    "action": "replace",
                    "values": data.keys,
                }
            })
        else:
            # Remove all keys
            await self._ldap.modify(user_dn, {
                self.SSH_KEY_ATTRIBUTE: {
                    "action": "delete",
                    "values": None,
                }
            })
        
        self._log.info("ssh_keys_updated", uid=uid, count=len(data.keys))
        
        return await self.get_user_ssh_status(uid)
    
    # ========================================================================
    # Key Lookup
    # ========================================================================
    
    async def get_key_by_fingerprint(self, uid: str, fingerprint: str) -> SSHKeyRead:
        """
        Get a specific SSH key by fingerprint.
        
        Args:
            uid: User ID
            fingerprint: SHA256 fingerprint
            
        Returns:
            SSHKeyRead
            
        Raises:
            LdapNotFoundError: If key not found
        """
        status = await self.get_user_ssh_status(uid)
        
        for key in status.keys:
            if key.fingerprint == fingerprint:
                return key
        
        raise LdapNotFoundError(f"SSH key not found: {fingerprint}")
    
    async def find_user_by_key(self, key_or_fingerprint: str) -> Optional[str]:
        """
        Find a user by SSH key or fingerprint.
        
        Args:
            key_or_fingerprint: Full SSH key or SHA256 fingerprint
            
        Returns:
            User UID if found, None otherwise
        """
        # Determine if it's a fingerprint or full key
        if key_or_fingerprint.startswith("SHA256:"):
            fingerprint = key_or_fingerprint
            # Need to search all users (expensive)
            filter_str = f"(objectClass={self.OBJECT_CLASS})"
        else:
            # Full key - can search directly
            filter_str = f"({self.SSH_KEY_ATTRIBUTE}={key_or_fingerprint})"
            fingerprint = compute_fingerprint(key_or_fingerprint)
        
        # Search for users with SSH keys
        from heracles_api.config import settings
        users_base = f"ou=people,{settings.LDAP_BASE_DN}"
        
        results = await self._ldap.search(
            base_dn=users_base,
            filter_str=filter_str,
            attributes=["uid", self.SSH_KEY_ATTRIBUTE],
            scope="sub",
        )
        
        for entry in results:
            uid = entry.get("uid")
            if isinstance(uid, list):
                uid = uid[0]
            
            keys = entry.get(self.SSH_KEY_ATTRIBUTE, [])
            if isinstance(keys, str):
                keys = [keys]
            
            for key in keys:
                try:
                    if compute_fingerprint(key) == fingerprint:
                        return uid
                except ValueError:
                    continue
        
        return None
    
    # ========================================================================
    # Helpers
    # ========================================================================
    
    async def _find_user_dn(self, uid: str) -> str:
        """
        Find user DN by UID.
        
        Args:
            uid: User ID to find
            
        Returns:
            User DN
            
        Raises:
            LdapNotFoundError: If user not found
        """
        from heracles_api.config import settings
        
        users_base = f"ou=people,{settings.LDAP_BASE_DN}"
        
        results = await self._ldap.search(
            base_dn=users_base,
            filter_str=f"(uid={uid})",
            attributes=["dn"],
            scope="sub",
            limit=1,
        )
        
        if not results:
            raise LdapNotFoundError(f"User not found: {uid}")
        
        return results[0].get("dn")
    
    # ========================================================================
    # TabService Interface
    # ========================================================================
    
    async def get_tab_data(self, dn: str) -> Optional[Dict[str, Any]]:
        """Get SSH tab data for an object."""
        # Extract UID from DN
        import re
        match = re.search(r"uid=([^,]+)", dn)
        if not match:
            return None
        
        uid = match.group(1)
        
        try:
            status = await self.get_user_ssh_status(uid)
            return status.model_dump(by_alias=True)
        except Exception:
            return None
    
    async def update_tab_data(self, dn: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update SSH tab data."""
        import re
        match = re.search(r"uid=([^,]+)", dn)
        if not match:
            raise ValueError("Invalid user DN")
        
        uid = match.group(1)
        
        # Handle different update types
        if "keys" in data:
            update = UserSSHKeysUpdate(keys=data["keys"])
            status = await self.update_keys(uid, update)
        else:
            # Just return current status
            status = await self.get_user_ssh_status(uid)
        
        return status.model_dump(by_alias=True)
