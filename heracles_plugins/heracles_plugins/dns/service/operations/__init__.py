"""
DNS Service Operations
======================

Operation mixins for DNS zone and record management.
"""

from .zone_ops import ZoneOperationsMixin
from .record_ops import RecordOperationsMixin

__all__ = [
    "ZoneOperationsMixin",
    "RecordOperationsMixin",
]
