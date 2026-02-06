"""Add builtin column to acl_assignments

Revision ID: 0004
Revises: 0003
Create Date: 2026-02-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add builtin flag to acl_assignments to protect bootstrap assignments."""
    op.add_column(
        'acl_assignments',
        sa.Column('builtin', sa.Boolean, nullable=False, server_default='false'),
    )


def downgrade() -> None:
    """Remove builtin column from acl_assignments."""
    op.drop_column('acl_assignments', 'builtin')
