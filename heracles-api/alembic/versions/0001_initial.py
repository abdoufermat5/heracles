"""Initial schema — all tables from models

Revision ID: 0001
Revises:
Create Date: 2026-02-06

Creates every table defined in heracles_api.models.
Seed data is managed separately via ``heracles_api.core.seed``.
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tables_exist(connection) -> bool:
    """Check if core tables already exist (e.g. from legacy init.sql)."""
    inspector = inspect(connection)
    return "config_categories" in inspector.get_table_names()


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    """Create all tables from ORM models."""
    from heracles_api.models import Base

    bind = op.get_bind()

    if _tables_exist(bind):
        Base.metadata.create_all(bind=bind, checkfirst=True)
    else:
        Base.metadata.create_all(bind=bind)


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------

def downgrade() -> None:
    """Drop all model-managed tables (reverse order for FK deps)."""
    for table in (
        "acl_audit_log",
        "acl_assignments",
        "acl_policy_attr_rules",
        "acl_policies",
        "acl_attribute_groups",
        "acl_permissions",
        "config_history",
        "plugin_configs",
        "config_settings",
        "config_categories",
    ):
        op.drop_table(table)
