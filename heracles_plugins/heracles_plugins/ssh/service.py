"""
SSH Plugin Service
==================

Business logic for managing SSH public keys on user accounts.
"""

from typing import Optional, List, Any, Dict, Tuple
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


class SSHKeyValidationError(Exception):
    """Raised when SSH key validation fails based on config rules."""
    pass


class SSHService(TabService):
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
    
    OBJECT_CLASS = "ldapPublicKey"
    SSH_KEY_ATTRIBUTE = "sshPublicKey"
    
    # Default config values (used if config service unavailable)
    DEFAULT_ALLOWED_KEY_TYPES = [
        "ssh-rsa",
        "ssh-ed25519",
        "ecdsa-sha2-nistp256",
        "ecdsa-sha2-nistp384",
        "ecdsa-sha2-nistp521",
        "sk-ssh-ed25519@openssh.com",
        "sk-ecdsa-sha2-nistp256@openssh.com",
    ]
    DEFAULT_MIN_RSA_BITS = 2048
    DEFAULT_REJECT_DSA = True
    DEFAULT_VALIDATE_FORMAT = True
    
    def __init__(self, ldap_service: LdapService, config: Optional[Dict[str, Any]] = None):
        """Initialize SSH service."""
        self._ldap = ldap_service
        self._config = config or {}
        self._log = logger.bind(service="ssh")
    
    # ========================================================================
    # Config-Based Validation
    # ========================================================================
    
    async def _get_validation_config(self) -> Dict[str, Any]:
        """
        Get SSH validation config with hot-reload support.
        
        Reads from database config with fallback to init-time config
        and then to defaults.
        """
        try:
            from heracles_api.services.config_service import get_plugin_config_value
            
            allowed_types = await get_plugin_config_value(
                "ssh", 
                "allowed_key_types", 
                self._config.get("allowed_key_types", self.DEFAULT_ALLOWED_KEY_TYPES)
            )
            min_rsa_bits = await get_plugin_config_value(
                "ssh",
                "min_rsa_bits",
                self._config.get("min_rsa_bits", self.DEFAULT_MIN_RSA_BITS)
            )
            reject_dsa = await get_plugin_config_value(
                "ssh",
                "reject_dsa_keys",
                self._config.get("reject_dsa_keys", self.DEFAULT_REJECT_DSA)
            )
            validate_format = await get_plugin_config_value(
                "ssh",
                "validate_key_format",
                self._config.get("validate_key_format", self.DEFAULT_VALIDATE_FORMAT)
            )
            
            return {
                "allowed_key_types": allowed_types,
                "min_rsa_bits": int(min_rsa_bits),
                "reject_dsa_keys": reject_dsa,
                "validate_key_format": validate_format,
            }
            
        except Exception as e:
            self._log.warning("ssh_config_load_error", error=str(e))
            # Fall back to init-time config or defaults
            return {
                "allowed_key_types": self._config.get("allowed_key_types", self.DEFAULT_ALLOWED_KEY_TYPES),
                "min_rsa_bits": self._config.get("min_rsa_bits", self.DEFAULT_MIN_RSA_BITS),
                "reject_dsa_keys": self._config.get("reject_dsa_keys", self.DEFAULT_REJECT_DSA),
                "validate_key_format": self._config.get("validate_key_format", self.DEFAULT_VALIDATE_FORMAT),
            }
    
    async def validate_ssh_key(self, key: str) -> Tuple[bool, List[str]]:
        """
        Validate an SSH key against config-based rules.
        
        Args:
            key: SSH public key string
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        config = await self._get_validation_config()
        
        # Parse the key first
        try:
            key_info = parse_ssh_key(key)
        except ValueError as e:
            return False, [f"Invalid SSH key format: {str(e)}"]
        
        key_type = key_info["key_type"]
        bits = key_info.get("bits")
        
        # Check if key type is allowed
        allowed_types = config.get("allowed_key_types", self.DEFAULT_ALLOWED_KEY_TYPES)
        if key_type not in allowed_types:
            errors.append(
                f"Key type '{key_type}' is not allowed. "
                f"Permitted types: {', '.join(allowed_types)}"
            )
        
        # Check DSA rejection
        if config.get("reject_dsa_keys", True) and key_type == "ssh-dss":
            errors.append(
                "DSA keys are not allowed due to security concerns. "
                "Please use RSA (2048+ bits) or Ed25519."
            )
        
        # Check RSA minimum key size
        if key_type == "ssh-rsa" and bits:
            min_bits = config.get("min_rsa_bits", self.DEFAULT_MIN_RSA_BITS)
            if bits < min_bits:
                errors.append(
                    f"RSA key size ({bits} bits) is below minimum requirement ({min_bits} bits). "
                    f"Please use a key with at least {min_bits} bits."
                )
        
        return len(errors) == 0, errors
    
    async def validate_ssh_key_or_raise(self, key: str) -> Dict[str, Any]:
        """
        Validate an SSH key and raise exception if invalid.
        
        Args:
            key: SSH public key string
            
        Returns:
            Parsed key info dict if valid
            
        Raises:
            SSHKeyValidationError: If validation fails
        """
        is_valid, errors = await self.validate_ssh_key(key)
        
        if not is_valid:
            raise SSHKeyValidationError("; ".join(errors))
        
        return parse_ssh_key(key)
    
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
        
        # Build modifications - format: {attr: (operation, values)}
        mods = {
            "objectClass": ("add", [self.OBJECT_CLASS]),
        }
        
        # Add initial key if provided
        if data and data.initial_key:
            # Validate key against config rules (raises SSHKeyValidationError)
            await self.validate_ssh_key_or_raise(data.initial_key)
            mods[self.SSH_KEY_ATTRIBUTE] = ("replace", [data.initial_key])
        
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
            "objectClass": ("delete", [self.OBJECT_CLASS]),
        }
        
        # Only remove sshPublicKey if there are keys
        if status.keys:
            mods[self.SSH_KEY_ATTRIBUTE] = ("delete", None)  # Delete all values
        
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
            self.SSH_KEY_ATTRIBUTE: ("add", [final_key]),
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
        
        # Remove key - format: {attr: (operation, values)}
        await self._ldap.modify(user_dn, {
            self.SSH_KEY_ATTRIBUTE: ("delete", [key_to_remove]),
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
            
        Raises:
            SSHKeyValidationError: If any key fails config-based validation
        """
        user_dn = await self._find_user_dn(uid)
        
        # Ensure SSH is activated
        status = await self.get_user_ssh_status(uid)
        if not status.has_ssh:
            await self.activate_ssh(uid)
        
        # Validate all keys against config rules and check for duplicates
        fingerprints = set()
        validation_errors = []
        
        for key in data.keys:
            # Validate against config
            is_valid, errors = await self.validate_ssh_key(key)
            if not is_valid:
                validation_errors.extend(errors)
                continue
            
            key_info = parse_ssh_key(key)
            fp = key_info["fingerprint"]
            if fp in fingerprints:
                validation_errors.append(f"Duplicate key in request: {fp}")
            fingerprints.add(fp)
        
        if validation_errors:
            raise SSHKeyValidationError("; ".join(validation_errors))
        
        # Replace all keys - format: {attr: (operation, values)}
        if data.keys:
            await self._ldap.modify(user_dn, {
                self.SSH_KEY_ATTRIBUTE: ("replace", data.keys),
            })
        else:
            # Remove all keys
            await self._ldap.modify(user_dn, {
                self.SSH_KEY_ATTRIBUTE: ("delete", None),
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
        
        # Search for users with SSH keys from base DN (supports nested OUs)
        from heracles_api.config import settings
        
        results = await self._ldap.search(
            search_base=settings.LDAP_BASE_DN,
            search_filter=filter_str,
            attributes=["uid", self.SSH_KEY_ATTRIBUTE],
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
        
        Searches the entire LDAP subtree to find users in any OU
        (including department OUs like ou=people,ou=engineering,...).
        
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
    
    # ========================================================================
    # TabService Interface (required abstract methods)
    # ========================================================================
    
    async def is_active(self, dn: str) -> bool:
        """Check if SSH is active on the user."""
        import re
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
        import re
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
        import re
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
        import re
        match = re.search(r"uid=([^,]+)", dn)
        if not match:
            raise ValueError("Invalid user DN")
        
        uid = match.group(1)
        await self.deactivate_ssh(uid)
        return True
    
    async def update(self, dn: str, data: Any) -> UserSSHStatus:
        """Update SSH tab data."""
        import re
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
