"""
User Template ORM Model
========================

Templates for bulk user creation with variable interpolation.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from heracles_api.models.base import Base


class UserTemplate(Base):
    """Reusable user creation template with default values and variables."""

    __tablename__ = "user_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Template defaults (applied when creating users from this template)
    defaults: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    # Example defaults:
    # {
    #   "objectClasses": ["inetOrgPerson", "posixAccount", "shadowAccount"],
    #   "loginShell": "/bin/bash",
    #   "homeDirectory": "/home/{{uid}}",
    #   "mail": "{{uid}}@{{domain}}",
    #   "gidNumber": 10000,
    #   "groups": ["cn=users,ou=groups,dc=example,dc=com"],
    #   "department": "ou=engineering,dc=example,dc=com"
    # }

    # Template variables documentation
    variables: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # Example:
    # {
    #   "domain": {"default": "example.com", "description": "Mail domain"},
    #   "shell": {"default": "/bin/bash", "description": "Login shell"}
    # }

    # Scope
    department_dn: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Plugin activations — which plugins to activate when using this template
    # Example: {"posix": {"loginShell": "/bin/bash", "gidNumber": 10000}, "mail": {"mailDomain": "example.com"}}
    plugin_activations: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Metadata
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_by: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (Index("idx_user_templates_department", "department_dn"),)

    def __repr__(self) -> str:
        return f"<UserTemplate(id={self.id}, name={self.name})>"
