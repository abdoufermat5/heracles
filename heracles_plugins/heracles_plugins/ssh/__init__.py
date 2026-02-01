"""
SSH Plugin
==========

Provides SSH public key management for user accounts.

Manages the following LDAP objectClasses:
- ldapPublicKey: Auxiliary class for SSH key storage

Attributes:
- sshPublicKey: Multi-valued attribute containing SSH public keys

Features:
- Add/remove SSH keys per user
- SHA256 fingerprint calculation
- Key type validation (RSA, Ed25519, ECDSA, etc.)
- Config-based key restrictions (allowed types, min RSA bits, DSA rejection)
- Key lookup (find user by key)
- Compatible with OpenSSH LDAP integration
"""

from .plugin import SSHPlugin
from .service import SSHKeyValidationError

__plugin__ = SSHPlugin

__all__ = ["SSHPlugin", "SSHKeyValidationError", "__plugin__"]
