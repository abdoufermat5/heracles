"""Add LDAP migration settings

Revision ID: 20250201_0001
Revises: 20250131_0001
Create Date: 2025-02-01

Adds LDAP settings for RDN migration support.
"""
from alembic import op


# revision identifiers
revision = '20250201_0001'
down_revision = '20250131_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add LDAP migration settings."""
    # Add new LDAP settings for migration support
    op.execute("""
        INSERT INTO config_settings (category_id, key, value, default_value, label, description, data_type, options, display_order, section)
        SELECT c.id, s.key, s.value, s.default_value, s.label, s.description, s.data_type, s.options, s.display_order, s.section
        FROM config_categories c
        CROSS JOIN (
            VALUES 
                ('allow_modrdn', 'true', 'true', 'Allow ModRDN Operations', 
                 'Allow LDAP ModRDN operations for moving entries. Required for RDN migration. Disable if your LDAP server does not support it.', 
                 'boolean', NULL, 100, 'Advanced'),
                ('migrate_on_rdn_change', 'false', 'false', 'Auto-Migrate on RDN Change', 
                 'Automatically migrate entries when an RDN setting changes. If disabled, entries will remain in the old location (orphaned).', 
                 'boolean', NULL, 110, 'Advanced'),
                ('rdn_change_confirmation', 'true', 'true', 'Require RDN Change Confirmation', 
                 'Require confirmation before changing RDN settings that would affect existing entries.', 
                 'boolean', NULL, 120, 'Advanced')
        ) AS s(key, value, default_value, label, description, data_type, options, display_order, section)
        WHERE c.name = 'ldap'
        ON CONFLICT (category_id, key) DO NOTHING
    """)


def downgrade() -> None:
    """Remove LDAP migration settings."""
    op.execute("""
        DELETE FROM config_settings
        WHERE key IN ('allow_modrdn', 'migrate_on_rdn_change', 'rdn_change_confirmation')
        AND category_id = (SELECT id FROM config_categories WHERE name = 'ldap')
    """)
