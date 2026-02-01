"""
Mail Plugin Service Facade
==========================

Re-exports services for backward compatibility.
"""

from .services.mail_user_service import MailUserService
from .services.mail_group_service import MailGroupService
from .services.base import MailValidationError, MailAlreadyExistsError

__all__ = [
    "MailUserService",
    "MailGroupService",
    "MailValidationError",
    "MailAlreadyExistsError",
]
