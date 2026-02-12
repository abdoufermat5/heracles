"""Add plugin_activations column to user_templates

Revision ID: 0003
Revises: 0002
Create Date: 2026-02-11

Adds:
  - plugin_activations JSONB column to user_templates table
    Stores which plugins to activate when using the template.
    Example: {"posix": {"loginShell": "/bin/bash"}, "mail": {"mailDomain": "example.com"}}
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add plugin_activations column to user_templates."""
    bind = op.get_bind()
    inspector = inspect(bind)

    if "user_templates" in inspector.get_table_names():
        columns = [c["name"] for c in inspector.get_columns("user_templates")]
        if "plugin_activations" not in columns:
            op.add_column(
                "user_templates",
                sa.Column("plugin_activations", postgresql.JSONB(), nullable=True),
            )


def downgrade() -> None:
    """Remove plugin_activations column."""
    bind = op.get_bind()
    inspector = inspect(bind)

    if "user_templates" in inspector.get_table_names():
        columns = [c["name"] for c in inspector.get_columns("user_templates")]
        if "plugin_activations" in columns:
            op.drop_column("user_templates", "plugin_activations")
