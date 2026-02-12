"""
Config ORM Models
=================

Models for configuration tables.
Must match the actual PostgreSQL schema (UUID PKs, JSONB columns, timestamptz).
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from heracles_api.models.base import Base


class ConfigCategory(Base):
    __tablename__ = "config_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.uuid_generate_v4(),
    )
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    settings: Mapped[list["ConfigSetting"]] = relationship(back_populates="category", cascade="all, delete-orphan")


class ConfigSetting(Base):
    __tablename__ = "config_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.uuid_generate_v4(),
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("config_categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    default_value: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_type: Mapped[str] = mapped_column(String(30), nullable=False)
    validation_rules: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    options: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    requires_restart: Mapped[bool | None] = mapped_column(Boolean, server_default="false")
    sensitive: Mapped[bool | None] = mapped_column(Boolean, server_default="false")
    read_only: Mapped[bool | None] = mapped_column(Boolean, server_default="false")
    section: Mapped[str | None] = mapped_column(String(50), nullable=True)
    display_order: Mapped[int | None] = mapped_column(Integer, server_default="0")
    depends_on: Mapped[str | None] = mapped_column(String(100), nullable=True)
    depends_on_value: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    category: Mapped["ConfigCategory"] = relationship(back_populates="settings")

    __table_args__ = (
        UniqueConstraint("category_id", "key", name="config_settings_category_id_key_key"),
        Index("idx_config_settings_category", "category_id"),
        Index("idx_config_settings_key", "key"),
    )


class PluginConfig(Base):
    __tablename__ = "plugin_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.uuid_generate_v4(),
    )
    plugin_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default="50")
    config: Mapped[Any] = mapped_column(JSONB, nullable=False, server_default="{}")
    config_schema: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (Index("idx_plugin_configs_enabled", "enabled"),)


class ConfigHistory(Base):
    __tablename__ = "config_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.uuid_generate_v4(),
    )
    setting_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("config_settings.id", ondelete="SET NULL"),
        nullable=True,
    )
    plugin_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    setting_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    old_value: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    changed_by: Mapped[str] = mapped_column(String(512), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_config_history_setting", "setting_id"),
        Index("idx_config_history_plugin", "plugin_name"),
        Index("idx_config_history_changed_at", "changed_at"),
        Index("idx_config_history_changed_by", "changed_by"),
    )
