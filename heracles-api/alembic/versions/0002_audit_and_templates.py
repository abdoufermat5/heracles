"""Add audit_logs and user_templates tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-11

Adds:
  - audit_logs: General-purpose audit trail for all entity operations
  - user_templates: Reusable templates for bulk user creation
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create audit_logs and user_templates tables."""
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    # -------------------------------------------------------------------------
    # audit_logs
    # -------------------------------------------------------------------------
    if "audit_logs" not in existing_tables:
        op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "timestamp",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("actor_dn", sa.String(512), nullable=False),
        sa.Column("actor_name", sa.String(256), nullable=True),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(512), nullable=True),
        sa.Column("entity_name", sa.String(256), nullable=True),
        sa.Column("changes", postgresql.JSONB(), nullable=True),
        sa.Column("department_dn", sa.String(512), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(16),
            server_default="success",
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
        op.create_index("idx_audit_logs_timestamp", "audit_logs", ["timestamp"])
        op.create_index("idx_audit_logs_actor", "audit_logs", ["actor_dn"])
        op.create_index("idx_audit_logs_action", "audit_logs", ["action"])
        op.create_index(
            "idx_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"]
        )
        op.create_index("idx_audit_logs_department", "audit_logs", ["department_dn"])

    # -------------------------------------------------------------------------
    # user_templates
    # -------------------------------------------------------------------------
    if "user_templates" not in existing_tables:
        op.create_table(
        "user_templates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(128), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "defaults",
            postgresql.JSONB(),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("variables", postgresql.JSONB(), nullable=True),
        sa.Column("department_dn", sa.String(512), nullable=True),
        sa.Column(
            "display_order", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column("created_by", sa.String(512), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "idx_user_templates_department", "user_templates", ["department_dn"]
        )


def downgrade() -> None:
    """Drop audit_logs and user_templates tables."""
    op.drop_table("user_templates")
    op.drop_table("audit_logs")
