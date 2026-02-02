"""
SSH Service Base
================

Common constants and exceptions for SSH service.
"""

from typing import List


class SSHKeyValidationError(Exception):
    """Raised when SSH key validation fails based on config rules."""
    pass


# LDAP Schema Constants
OBJECT_CLASS = "ldapPublicKey"
SSH_KEY_ATTRIBUTE = "sshPublicKey"

# Default config values (used if config service unavailable)
DEFAULT_ALLOWED_KEY_TYPES: List[str] = [
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
