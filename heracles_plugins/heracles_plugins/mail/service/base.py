"""
Mail Plugin Base Classes
========================

Shared exceptions and utilities for mail services.
"""


class MailValidationError(Exception):
    """Raised when mail validation fails."""

    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(message)


class MailNotFoundError(Exception):
    """Raised when mail account is not found."""

    pass


class MailAlreadyExistsError(Exception):
    """Raised when email address is already in use."""

    def __init__(self, email: str):
        self.email = email
        super().__init__(f"Email address already in use: {email}")
