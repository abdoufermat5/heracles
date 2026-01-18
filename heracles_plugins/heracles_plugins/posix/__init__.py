"""
POSIX Plugin
============

Provides POSIX account management (Unix accounts) for users and groups.

Manages the following LDAP objectClasses:
- posixAccount: Unix user account (uidNumber, gidNumber, homeDirectory, etc.)
- shadowAccount: Password aging/expiration
- posixGroup: Unix group (gidNumber, memberUid)
"""

from .plugin import PosixPlugin

__plugin__ = PosixPlugin

__all__ = ["PosixPlugin", "__plugin__"]
