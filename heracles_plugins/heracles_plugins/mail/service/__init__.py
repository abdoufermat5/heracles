"""
Mail Plugin Services
====================

Business logic for mail account management.
"""

from .mail_user_service import MailUserService
from .mail_group_service import MailGroupService
from .base import MailValidationError, MailAlreadyExistsError, MailNotFoundError

__all__ = [
    "MailUserService",
    "MailGroupService",
    "MailValidationError",
    "MailAlreadyExistsError",
    "MailNotFoundError",
]
