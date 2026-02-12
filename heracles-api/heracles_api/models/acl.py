"""
ACL ORM Models
==============

Models for the ACL permission system tables.
Must match schema from migrations 0003 + 0004.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from heracles_api.models.base import Base


class AclPermission(Base):
    __tablename__ = "acl_permissions"

    bit_position: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    plugin: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "bit_position >= 0 AND bit_position <= 127",
            name="ck_acl_permissions_bit_range",
        ),
        UniqueConstraint("scope", "action", name="uq_acl_permissions_scope_action"),
    )


class AclAttributeGroup(Base):
    __tablename__ = "acl_attribute_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    group_name: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    attributes: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    plugin: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        UniqueConstraint("object_type", "group_name", name="uq_acl_attr_groups_object_group"),
        Index("idx_acl_attr_groups_object_type", "object_type"),
    )


class AclPolicy(Base):
    __tablename__ = "acl_policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    perm_low: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    perm_high: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    attr_rules: Mapped[list["AclPolicyAttrRule"]] = relationship(back_populates="policy", cascade="all, delete-orphan")
    assignments: Mapped[list["AclAssignment"]] = relationship(back_populates="policy", cascade="all, delete-orphan")


class AclPolicyAttrRule(Base):
    __tablename__ = "acl_policy_attr_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("acl_policies.id", ondelete="CASCADE"),
        nullable=False,
    )
    object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(8), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(8), nullable=False)
    attr_groups: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)

    policy: Mapped["AclPolicy"] = relationship(back_populates="attr_rules")

    __table_args__ = (
        CheckConstraint("action IN ('read', 'write')", name="ck_acl_policy_attr_action"),
        CheckConstraint("rule_type IN ('allow', 'deny')", name="ck_acl_policy_attr_rule_type"),
        UniqueConstraint(
            "policy_id",
            "object_type",
            "action",
            "rule_type",
            name="uq_acl_policy_attr_rules",
        ),
        Index("idx_acl_policy_attr_rules_policy", "policy_id"),
    )


class AclAssignment(Base):
    __tablename__ = "acl_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("acl_policies.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_type: Mapped[str] = mapped_column(String(8), nullable=False)
    subject_dn: Mapped[str] = mapped_column(String(512), nullable=False)
    scope_dn: Mapped[str] = mapped_column(String(512), nullable=False, server_default="")
    scope_type: Mapped[str] = mapped_column(String(8), nullable=False, server_default="subtree")
    self_only: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    deny: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    policy: Mapped["AclPolicy"] = relationship(back_populates="assignments")

    __table_args__ = (
        CheckConstraint(
            "subject_type IN ('user', 'group', 'role')",
            name="ck_acl_assignments_subject_type",
        ),
        CheckConstraint(
            "scope_type IN ('base', 'subtree')",
            name="ck_acl_assignments_scope_type",
        ),
        UniqueConstraint(
            "policy_id",
            "subject_type",
            "subject_dn",
            "scope_dn",
            "self_only",
            name="uq_acl_assignments",
        ),
        Index("idx_acl_assignments_subject", "subject_type", "subject_dn"),
        Index("idx_acl_assignments_policy", "policy_id"),
    )


class AclAuditLog(Base):
    __tablename__ = "acl_audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    user_dn: Mapped[str] = mapped_column(String(512), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    target_dn: Mapped[str | None] = mapped_column(String(512), nullable=True)
    permission: Mapped[str | None] = mapped_column(String(96), nullable=True)
    result: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("idx_acl_audit_ts", "ts"),
        Index("idx_acl_audit_user", "user_dn"),
    )
