"""
Sudo Service Base
=================

Constants, exceptions, and base configuration for sudo service.
"""

from datetime import datetime, timezone
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


class SudoValidationError(Exception):
    """Raised when sudo validation fails."""
    pass


# Object classes for sudo roles
OBJECT_CLASSES = ["sudoRole"]

# Attributes managed by the sudo service
MANAGED_ATTRIBUTES = [
    "cn",
    "description",
    "sudoUser",
    "sudoHost",
    "sudoCommand",
    "sudoRunAs",  # deprecated but still read
    "sudoRunAsUser",
    "sudoRunAsGroup",
    "sudoOption",
    "sudoOrder",
    "sudoNotBefore",
    "sudoNotAfter",
]


def parse_generalized_time(value: Optional[str]) -> Optional[datetime]:
    """Parse LDAP generalized time to datetime."""
    if not value:
        return None
    try:
        # Format: YYYYMMDDHHMMSSZ or YYYYMMDDHHMMSS.ffffffZ
        value = value.rstrip("Z")
        if "." in value:
            value = value.split(".")[0]
        return datetime.strptime(value, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def datetime_to_generalized(dt: datetime) -> str:
    """Convert datetime to LDAP generalized time."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y%m%d%H%M%SZ")


def is_time_valid(not_before: Optional[datetime], not_after: Optional[datetime]) -> bool:
    """Check if current time is within validity period."""
    now = datetime.now(timezone.utc)
    
    if not_before and now < not_before:
        return False
    if not_after and now > not_after:
        return False
    
    return True
