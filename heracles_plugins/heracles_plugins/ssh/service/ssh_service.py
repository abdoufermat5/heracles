"""
SSH Plugin Service
==================

Business logic for managing SSH public keys on user accounts.
"""

from typing import Any, Dict, Optional
import re

import structlog

from heracles_api.plugins.base import TabService
from heracles_api.services.ldap_service import LdapService

from ..schemas import (
    SSHKeyCreate,
    UserSSHStatus,
    UserSSHActivate,
    UserSSHKeysUpdate,
)

from .base import SSHKeyValidationError
from .operations import (
    ValidationOperationsMixin,
    StatusOperationsMixin,
    ActivationOperationsMixin,
    KeyOperationsMixin,
)

logger = structlog.get_logger(__name__)


class SSHService(
    ValidationOperationsMixin,
    StatusOperationsMixin,
    ActivationOperationsMixin,
    KeyOperationsMixin,
    TabService,
):
    """
    Service for managing SSH public keys.
    
    Manages the ldapPublicKey objectClass and sshPublicKey attribute.
    
    LDAP Schema:
        objectClass: ldapPublicKey (auxiliary)
        attribute: sshPublicKey (multi-valued)
    
    Config-based validation:
        - allowed_key_types: List of permitted key types
        - min_rsa_bits: Minimum RSA key size (default: 2048)
        - reject_dsa_keys: Whether to reject DSA keys (default: True)
        - validate_key_format: Whether to validate key format (default: True)
    """

    def __init__(self, ldap_service: LdapService, config: Optional[Dict[str, Any]] = None):
        """Initialize SSH service."""
        self._ldap = ldap_service
        self._config = config or {}
        self._log = logger.bind(service="ssh")

    def get_base_dn(self) -> str:
        """Get the LDAP base DN for scope-based ACL checks."""
        return self._ldap.base_dn

    # ========================================================================
    # TabService Interface (required abstract methods)
    # ========================================================================

    async def is_active(self, dn: str) -> bool:
        """Check if SSH is active on the user."""
        match = re.search(r"uid=([^,]+)", dn)
        if not match:
            return False
        
        uid = match.group(1)
        try:
            status = await self.get_user_ssh_status(uid)
            return status.has_ssh
        except Exception:
            return False

    async def read(self, dn: str) -> Optional[UserSSHStatus]:
        """Read SSH tab data from the object."""
        match = re.search(r"uid=([^,]+)", dn)
        if not match:
            return None
        
        uid = match.group(1)
        try:
            return await self.get_user_ssh_status(uid)
        except Exception:
            return None

    async def activate(self, dn: str, data: Any = None) -> UserSSHStatus:
        """Activate SSH on a user."""
        match = re.search(r"uid=([^,]+)", dn)
        if not match:
            raise ValueError("Invalid user DN")
        
        uid = match.group(1)
        activate_data = None
        if data and isinstance(data, dict):
            activate_data = UserSSHActivate(**data)
        elif isinstance(data, UserSSHActivate):
            activate_data = data
        
        return await self.activate_ssh(uid, activate_data)

    async def deactivate(self, dn: str) -> bool:
        """Deactivate SSH on a user."""
        match = re.search(r"uid=([^,]+)", dn)
        if not match:
            raise ValueError("Invalid user DN")
        
        uid = match.group(1)
        await self.deactivate_ssh(uid)
        return True

    async def update(self, dn: str, data: Any) -> UserSSHStatus:
        """Update SSH tab data."""
        match = re.search(r"uid=([^,]+)", dn)
        if not match:
            raise ValueError("Invalid user DN")
        
        uid = match.group(1)
        
        # Handle different update types
        if isinstance(data, dict) and "keys" in data:
            update = UserSSHKeysUpdate(keys=data["keys"])
            return await self.update_keys(uid, update)
        
        # Just return current status
        return await self.get_user_ssh_status(uid)

    # ========================================================================
    # Legacy TabService Interface (kept for compatibility)
    # ========================================================================

    async def get_tab_data(self, dn: str) -> Optional[Dict[str, Any]]:
        """Get SSH tab data for an object."""
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

    # ========================================================================
    # Import / Export / Template extension points
    # ========================================================================

    @classmethod
    def get_import_fields(cls) -> list:
        from heracles_api.plugins.base import PluginFieldDefinition
        return [
            PluginFieldDefinition(
                name="sshPublicKey", label="SSH Public Key",
                description="Full SSH public key string",
            ),
        ]

    @classmethod
    def get_export_fields(cls) -> list:
        from heracles_api.plugins.base import PluginFieldDefinition
        return [
            PluginFieldDefinition(
                name="sshPublicKey", label="SSH Public Key",
                description="SSH public keys (multi-valued)",
            ),
        ]

    @classmethod
    def get_template_fields(cls) -> list:
        """SSH has no template-configurable defaults (keys are per-user)."""
        return []