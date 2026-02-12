"""
SSH Key Operations Mixin
========================

SSH key management (add, remove, update, search).
"""

from typing import Optional

import structlog

from heracles_api.services.ldap_service import LdapNotFoundError

from ..base import OBJECT_CLASS, SSH_KEY_ATTRIBUTE
from ...schemas import (
    SSHKeyCreate,
    SSHKeyRead,
    UserSSHKeysUpdate,
    UserSSHStatus,
    compute_fingerprint,
)

logger = structlog.get_logger(__name__)


class KeyOperationsMixin:
    """Mixin providing SSH key management operations."""

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
        
        # Validate key against config rules (raises SSHKeyValidationError)
        key_info = await self.validate_ssh_key_or_raise(data.key)
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
        
        # Add key - format: {attr: (operation, values)}
        await self._ldap.modify(user_dn, {
            SSH_KEY_ATTRIBUTE: ("add", [final_key]),
        })
        
        self._log.info("ssh_key_added", uid=uid, fingerprint=new_fingerprint)
        
        return await self.get_user_ssh_status(uid)

    async def remove_key(self, uid: str, fingerprint: str) -> UserSSHStatus:
        """
        Remove an SSH key from a user account.
        
        Args:
            uid: User ID
            fingerprint: SHA256 fingerprint of key to remove
            
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
        
        # Remove key - format: {attr: (operation, values)}
        await self._ldap.modify(user_dn, {
            SSH_KEY_ATTRIBUTE: ("delete", [key_to_remove]),
        })
        
        self._log.info("ssh_key_removed", uid=uid, fingerprint=fingerprint)
        
        return await self.get_user_ssh_status(uid)

    async def update_keys(self, uid: str, data: UserSSHKeysUpdate) -> UserSSHStatus:
        """
        Replace all SSH keys for a user.
        
        Args:
            uid: User ID
            data: New keys to set
            
        Returns:
            Updated UserSSHStatus
        """
        user_dn = await self._find_user_dn(uid)
        
        # Get current status
        status = await self.get_user_ssh_status(uid)
        
        if not status.has_ssh:
            raise ValueError("SSH not enabled for user")
        
        # Validate all keys and collect them
        validated_keys = []
        seen_fingerprints = set()
        
        for key in data.keys:
            key_info = await self.validate_ssh_key_or_raise(key)
            fp = key_info["fingerprint"]
            
            if fp in seen_fingerprints:
                raise ValueError(f"Duplicate key fingerprint: {fp}")
            
            seen_fingerprints.add(fp)
            validated_keys.append(key)
        
        # Replace all keys - format: {attr: (operation, values)}
        if validated_keys:
            await self._ldap.modify(user_dn, {
                SSH_KEY_ATTRIBUTE: ("replace", validated_keys),
            })
        else:
            # Delete all keys if empty
            await self._ldap.modify(user_dn, {
                SSH_KEY_ATTRIBUTE: ("delete", None),
            })
        
        self._log.info("ssh_keys_updated", uid=uid, count=len(validated_keys))
        
        return await self.get_user_ssh_status(uid)

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
            filter_str = f"(objectClass={OBJECT_CLASS})"
        else:
            # Full key - can search directly
            filter_str = f"({SSH_KEY_ATTRIBUTE}={key_or_fingerprint})"
            fingerprint = compute_fingerprint(key_or_fingerprint)
        
        # Search for users with SSH keys from base DN (supports nested OUs)
        from heracles_api.config import settings
        
        results = await self._ldap.search(
            search_base=settings.LDAP_BASE_DN,
            search_filter=filter_str,
            attributes=["uid", SSH_KEY_ATTRIBUTE],
        )
        
        for entry in results:
            uid = entry.get("uid")
            if isinstance(uid, list):
                uid = uid[0]
            
            keys = entry.get(SSH_KEY_ATTRIBUTE, [])
            if isinstance(keys, str):
                keys = [keys]
            
            for key in keys:
                try:
                    if compute_fingerprint(key) == fingerprint:
                        return uid
                except ValueError:
                    continue
        
        return None
