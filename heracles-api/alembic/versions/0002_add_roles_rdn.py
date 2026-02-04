"""Add roles_rdn LDAP setting

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add roles_rdn setting to LDAP category."""
    
    # Add roles_rdn setting
    op.execute("""
        INSERT INTO config_settings (category_id, key, value, default_value, label, description, data_type, display_order, section) 
        SELECT c.id, 'roles_rdn', '"ou=roles"', '"ou=roles"', 'Roles RDN', 'Relative DN for organizational role entries', 'string', 25, NULL
        FROM config_categories c
        WHERE c.name = 'ldap'
        AND NOT EXISTS (
            SELECT 1 FROM config_settings s 
            WHERE s.category_id = c.id AND s.key = 'roles_rdn'
        )
    """)


def downgrade() -> None:
    """Remove roles_rdn setting."""
    op.execute("""
        DELETE FROM config_settings 
        WHERE key = 'roles_rdn' 
        AND category_id = (SELECT id FROM config_categories WHERE name = 'ldap')
    """)
