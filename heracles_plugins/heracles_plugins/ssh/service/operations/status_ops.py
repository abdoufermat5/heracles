"""
SSH Status Operations Mixin
===========================

User SSH status and discovery operations.
"""

from typing import Any, Dict, Optional

import structlog

from heracles_api.services.ldap_service import LdapNotFoundError

from ..base import OBJECT_CLASS, SSH_KEY_ATTRIBUTE
from ...schemas import SSHKeyRead, UserSSHStatus, parse_ssh_key

logger = structlog.get_logger(__name__)


class StatusOperationsMixin:
    """Mixin providing SSH status operations."""

    async def _find_user_dn(self, uid: str) -> str:
        """
        Find user DN by UID.
        
        Searches the entire LDAP subtree to find users in any OU.
        
        Args:
            uid: User ID to find
            
        Returns:
            User DN
            
        Raises:
            LdapNotFoundError: If user not found
        """
        from heracles_api.config import settings
        
        # Search from base DN with subtree scope to find users in any OU
        results = await self._ldap.search(
            search_base=settings.LDAP_BASE_DN,
            search_filter=f"(&(objectClass=inetOrgPerson)(uid={uid}))",
            attributes=["dn"],
            size_limit=1,
        )
        
        if not results:
            raise LdapNotFoundError(f"User not found: {uid}")
        
        return results[0].dn

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
            attributes=["objectClass", SSH_KEY_ATTRIBUTE],
        )
        
        if not entry:
            raise LdapNotFoundError(f"User {uid} not found")
        
        # Check for SSH objectClass
        object_classes = entry.get("objectClass", [])
        if isinstance(object_classes, str):
            object_classes = [object_classes]
        
        has_ssh = OBJECT_CLASS in object_classes
        
        # Parse SSH keys
        keys = []
        raw_keys = entry.get(SSH_KEY_ATTRIBUTE, [])
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
