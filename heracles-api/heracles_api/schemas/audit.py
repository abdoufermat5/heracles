"""
Audit Pydantic Schemas
======================

Request/response models for the audit log API.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------

class AuditLogEntry(BaseModel):
    """Single audit log entry."""

    id: int
    timestamp: datetime
    actorDn: str = Field(alias="actor_dn")
    actorName: Optional[str] = Field(None, alias="actor_name")
    action: str
    entityType: str = Field(alias="entity_type")
    entityId: Optional[str] = Field(None, alias="entity_id")
    entityName: Optional[str] = Field(None, alias="entity_name")
    changes: Optional[dict[str, Any]] = None
    departmentDn: Optional[str] = Field(None, alias="department_dn")
    ipAddress: Optional[str] = Field(None, alias="ip_address")
    status: str = "success"
    errorMessage: Optional[str] = Field(None, alias="error_message")

    class Config:
        from_attributes = True
        populate_by_name = True


class AuditLogListResponse(BaseModel):
    """Paginated audit log response."""

    entries: list[AuditLogEntry]
    total: int
    page: int
    pageSize: int = Field(alias="page_size")
    hasMore: bool = Field(alias="has_more")

    class Config:
        populate_by_name = True


# ---------------------------------------------------------------------------
# Query Parameters
# ---------------------------------------------------------------------------

class AuditLogFilters(BaseModel):
    """Filter parameters for audit log queries."""

    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=200)
    actor_dn: Optional[str] = None
    action: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    department_dn: Optional[str] = None
    status: Optional[str] = None
    from_ts: Optional[datetime] = None
    to_ts: Optional[datetime] = None
    search: Optional[str] = None


# ---------------------------------------------------------------------------
# Sensitive Field Masking Configuration
# ---------------------------------------------------------------------------

# Fields that should be masked in audit change details
SENSITIVE_FIELDS = frozenset({
    "userPassword",
    "password",
    "secret_key",
    "token",
    "refresh_token",
    "access_token",
    "sshPublicKey",
})


def mask_sensitive_data(
    changes: Optional[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    """Mask sensitive fields in change details before storing."""
    if not changes:
        return changes

    masked = {}
    for key, value in changes.items():
        if key.lower() in {f.lower() for f in SENSITIVE_FIELDS}:
            if isinstance(value, dict):
                masked[key] = {
                    k: "***REDACTED***" for k in value
                }
            else:
                masked[key] = "***REDACTED***"
        else:
            masked[key] = value
    return masked
