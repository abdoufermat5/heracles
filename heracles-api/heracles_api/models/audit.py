"""
Audit ORM Model
================

General-purpose audit log for all entity CRUD operations.
Stored in PostgreSQL for queryability and retention.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from heracles_api.models.base import Base


class AuditLog(Base):
    """Tracks all significant actions across the system."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # When
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    # Who
    actor_dn: Mapped[str] = mapped_column(String(512), nullable=False)
    actor_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    # What
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    # create, update, delete, login, logout, export, import, password_change

    # On what
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # user, group, role, department, system, dns_zone, dhcp_service, sudo_role,
    # template, config, acl_policy, acl_assignment, plugin

    entity_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    # DN or UUID of the affected entity

    entity_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    # Human-readable name (cn, uid, etc.)

    # Change details
    changes: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    # For updates: {"field": {"old": ..., "new": ...}}
    # For creates: {"field": value, ...}
    # For deletes: snapshot of deleted entity

    # Context
    department_dn: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Outcome
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="success"
    )
    # success, failure, partial
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_audit_logs_timestamp", "timestamp"),
        Index("idx_audit_logs_actor", "actor_dn"),
        Index("idx_audit_logs_action", "action"),
        Index("idx_audit_logs_entity", "entity_type", "entity_id"),
        Index("idx_audit_logs_department", "department_dn"),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, action={self.action}, "
            f"entity_type={self.entity_type}, entity_name={self.entity_name})>"
        )
