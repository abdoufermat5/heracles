"""
SSH Activation Operations Mixin
===============================

SSH feature activation/deactivation for users.
"""

from typing import Optional

import structlog

from ..base import OBJECT_CLASS, SSH_KEY_ATTRIBUTE
from ...schemas import SSHKeyCreate, UserSSHActivate, UserSSHStatus

logger = structlog.get_logger(__name__)


class ActivationOperationsMixin:
    """Mixin providing SSH activation operations."""

    async def activate_ssh(
        self,
        uid: str,
        data: Optional[UserSSHActivate] = None
    ) -> UserSSHStatus:
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
        
        # Build modifications - format: {attr: (operation, values)}
        mods = {
            "objectClass": ("add", [OBJECT_CLASS]),
        }
        
        # Add initial key if provided
        if data and data.initial_key:
            # Validate key against config rules (raises SSHKeyValidationError)
            await self.validate_ssh_key_or_raise(data.initial_key)
            mods[SSH_KEY_ATTRIBUTE] = ("replace", [data.initial_key])
        
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
        
        # Remove objectClass and keys - format: {attr: (operation, values)}
        mods = {
            "objectClass": ("delete", [OBJECT_CLASS]),
        }
        
        # Only remove sshPublicKey if there are keys
        if status.keys:
            mods[SSH_KEY_ATTRIBUTE] = ("delete", None)  # Delete all values
        
        await self._ldap.modify(user_dn, mods)
        
        self._log.info("ssh_deactivated", uid=uid, keys_removed=len(status.keys))
        
        return await self.get_user_ssh_status(uid)
