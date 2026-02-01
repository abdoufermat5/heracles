"""
Mail Plugin
===========

Provides mail account management for users and groups.

Manages the following LDAP objectClasses:
- hrcMailAccount: Auxiliary class for user mail accounts
- hrcGroupMail: Auxiliary class for group mailing lists

Attributes:
- mail: Primary email address (from inetOrgPerson)
- hrcMailServer: Assigned mail server
- hrcMailQuota: Mailbox quota in MiB
- hrcMailAlternateAddress: Alternative email addresses (aliases)
- hrcMailForwardingAddress: Forwarding destinations
- hrcMailDeliveryMode: Delivery mode flags (V=vacation, L=local-only, I=forward-only)
- hrcVacationMessage: Auto-reply message text
- hrcVacationStart/Stop: Vacation date range

Features:
- User mail account activation/deactivation
- Primary and alternate email addresses
- Mail forwarding configuration
- Quota management
- Vacation auto-reply with date ranges
- Group mailing lists
"""

from .plugin import MailPlugin

__plugin__ = MailPlugin

__all__ = ["MailPlugin", "__plugin__"]
