"""
Sudo Plugin
===========

Provides sudo role management for defining sudoers rules via LDAP.

Manages the following LDAP objectClasses:
- sudoRole: Defines sudo privileges (who can run what commands where)

Attributes:
- sudoUser: User(s) who may run sudo (uid, %group, #uid)
- sudoHost: Host(s) where sudo is allowed (hostname, IP, ALL)
- sudoCommand: Command(s) allowed (path, ALL)
- sudoRunAsUser: User(s) to run as (default: ALL)
- sudoRunAsGroup: Group(s) to run as
- sudoOption: Options (NOPASSWD, PASSWD, etc.)
- sudoOrder: Priority order
- sudoNotBefore: Valid from timestamp
- sudoNotAfter: Valid until timestamp
"""

from .plugin import SudoPlugin

__plugin__ = SudoPlugin

__all__ = ["SudoPlugin", "__plugin__"]
