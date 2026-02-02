"""
SSH Validation Operations Mixin
===============================

Config-based SSH key validation.
"""

from typing import Any, Dict, List, Tuple

import structlog

from ...schemas import parse_ssh_key
from ..base import (
    SSHKeyValidationError,
    DEFAULT_ALLOWED_KEY_TYPES,
    DEFAULT_MIN_RSA_BITS,
    DEFAULT_REJECT_DSA,
    DEFAULT_VALIDATE_FORMAT,
)

logger = structlog.get_logger(__name__)


class ValidationOperationsMixin:
    """Mixin providing SSH key validation operations."""

    async def _get_validation_config(self) -> Dict[str, Any]:
        """
        Get SSH validation config with hot-reload support.
        
        Reads from database config with fallback to init-time config
        and then to defaults.
        """
        try:
            from heracles_api.services.config import get_plugin_config_value
            
            allowed_types = await get_plugin_config_value(
                "ssh", 
                "allowed_key_types", 
                self._config.get("allowed_key_types", DEFAULT_ALLOWED_KEY_TYPES)
            )
            min_rsa_bits = await get_plugin_config_value(
                "ssh",
                "min_rsa_bits",
                self._config.get("min_rsa_bits", DEFAULT_MIN_RSA_BITS)
            )
            reject_dsa = await get_plugin_config_value(
                "ssh",
                "reject_dsa_keys",
                self._config.get("reject_dsa_keys", DEFAULT_REJECT_DSA)
            )
            validate_format = await get_plugin_config_value(
                "ssh",
                "validate_key_format",
                self._config.get("validate_key_format", DEFAULT_VALIDATE_FORMAT)
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
                "allowed_key_types": self._config.get("allowed_key_types", DEFAULT_ALLOWED_KEY_TYPES),
                "min_rsa_bits": self._config.get("min_rsa_bits", DEFAULT_MIN_RSA_BITS),
                "reject_dsa_keys": self._config.get("reject_dsa_keys", DEFAULT_REJECT_DSA),
                "validate_key_format": self._config.get("validate_key_format", DEFAULT_VALIDATE_FORMAT),
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
        allowed_types = config.get("allowed_key_types", DEFAULT_ALLOWED_KEY_TYPES)
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
            min_bits = config.get("min_rsa_bits", DEFAULT_MIN_RSA_BITS)
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
