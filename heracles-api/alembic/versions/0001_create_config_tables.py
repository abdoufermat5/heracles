"""Create configuration tables

Revision ID: 0001
Revises: 
Create Date: 2026-02-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create configuration tables."""
    
    # Configuration Categories
    op.create_table(
        'config_categories',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(100), unique=True, nullable=False),
        sa.Column('label', sa.String(200), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('icon', sa.String(50)),
        sa.Column('display_order', sa.Integer, default=50),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('NOW()')),
    )
    
    # Configuration Settings
    op.create_table(
        'config_settings',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('category_id', sa.Integer, sa.ForeignKey('config_categories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('value', sa.Text),
        sa.Column('default_value', sa.Text),
        sa.Column('label', sa.String(200), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('data_type', sa.String(50), nullable=False, server_default='string'),
        sa.Column('validation_rules', sa.Text),  # JSON
        sa.Column('options', sa.Text),  # JSON for select/multiselect
        sa.Column('requires_restart', sa.Boolean, server_default='false'),
        sa.Column('sensitive', sa.Boolean, server_default='false'),
        sa.Column('section', sa.String(100)),
        sa.Column('display_order', sa.Integer, server_default='50'),
        sa.Column('depends_on', sa.String(100)),
        sa.Column('depends_on_value', sa.Text),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('NOW()')),
        sa.UniqueConstraint('category_id', 'key', name='uq_config_settings_category_key'),
    )
    
    # Create index for faster lookups
    op.create_index('idx_config_settings_category', 'config_settings', ['category_id'])
    
    # Plugin Configurations
    op.create_table(
        'plugin_configs',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('plugin_name', sa.String(100), unique=True, nullable=False),
        sa.Column('enabled', sa.Boolean, server_default='true'),
        sa.Column('priority', sa.Integer, server_default='50'),
        sa.Column('config', sa.Text),  # JSON
        sa.Column('config_schema', sa.Text),  # JSON Schema
        sa.Column('version', sa.String(50)),
        sa.Column('description', sa.Text),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('NOW()')),
        sa.Column('updated_by', sa.String(500)),
    )
    
    # Configuration History (Audit Trail)
    op.create_table(
        'config_history',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('setting_id', sa.Integer, sa.ForeignKey('config_settings.id', ondelete='SET NULL')),
        sa.Column('plugin_config_id', sa.Integer, sa.ForeignKey('plugin_configs.id', ondelete='SET NULL')),
        sa.Column('category', sa.String(100)),
        sa.Column('plugin_name', sa.String(100)),
        sa.Column('setting_key', sa.String(100)),
        sa.Column('old_value', sa.Text),
        sa.Column('new_value', sa.Text),
        sa.Column('changed_by', sa.String(500), nullable=False),
        sa.Column('changed_at', sa.TIMESTAMP, server_default=sa.text('NOW()')),
        sa.Column('reason', sa.Text),
    )
    
    # Create indexes for history lookups
    op.create_index('idx_config_history_setting', 'config_history', ['setting_id'])
    op.create_index('idx_config_history_plugin', 'config_history', ['plugin_config_id'])
    op.create_index('idx_config_history_changed_at', 'config_history', ['changed_at'])
    
    # Seed default categories
    op.execute("""
        INSERT INTO config_categories (name, label, description, icon, display_order) VALUES
        ('general', 'General', 'General application settings', 'settings', 10),
        ('ldap', 'LDAP', 'LDAP connection and directory settings', 'database', 20),
        ('security', 'Security', 'Security and access control settings', 'shield', 30),
        ('password', 'Password Policy', 'Password requirements and validation', 'key', 40),
        ('session', 'Session', 'Session and token settings', 'clock', 50),
        ('audit', 'Audit', 'Audit logging settings', 'file-text', 60)
    """)
    
    # Seed general settings
    op.execute("""
        INSERT INTO config_settings (category_id, key, value, default_value, label, description, data_type, options) 
        SELECT 
            c.id,
            s.key,
            s.value,
            s.default_value,
            s.label,
            s.description,
            s.data_type,
            s.options
        FROM config_categories c
        CROSS JOIN (
            VALUES 
                ('language', '"en"', '"en"', 'Language', 'Default language for the interface', 'select',
                 '[{"value": "en", "label": "English"}, {"value": "fr", "label": "Français"}, {"value": "de", "label": "Deutsch"}]'),
                ('timezone', '"UTC"', '"UTC"', 'Timezone', 'Default timezone for date/time display', 'string', NULL),
                ('items_per_page', '25', '25', 'Items Per Page', 'Default number of items to show in lists', 'integer', NULL),
                ('theme', '"system"', '"system"', 'Theme', 'Color theme for the interface', 'select',
                 '[{"value": "light", "label": "Light"}, {"value": "dark", "label": "Dark"}, {"value": "system", "label": "System"}]')
        ) AS s(key, value, default_value, label, description, data_type, options)
        WHERE c.name = 'general'
    """)
    
    # Seed LDAP settings
    op.execute("""
        INSERT INTO config_settings (category_id, key, value, default_value, label, description, data_type, display_order, section) 
        SELECT c.id, s.key, s.value, s.default_value, s.label, s.description, s.data_type, s.display_order, s.section
        FROM config_categories c
        CROSS JOIN (
            VALUES 
                ('users_rdn', '"ou=people"', '"ou=people"', 'Users RDN', 'Relative DN for user entries', 'string', 10, NULL),
                ('groups_rdn', '"ou=groups"', '"ou=groups"', 'Groups RDN', 'Relative DN for group entries', 'string', 20, NULL),
                ('default_user_objectclasses', '["inetOrgPerson", "organizationalPerson", "person"]', '["inetOrgPerson", "organizationalPerson", "person"]', 'Default User Object Classes', 'Object classes applied to new users', 'list', 30, NULL),
                ('default_group_objectclasses', '["groupOfNames"]', '["groupOfNames"]', 'Default Group Object Classes', 'Object classes applied to new groups', 'list', 40, NULL),
                ('page_size', '100', '100', 'LDAP Page Size', 'Number of entries per page for LDAP queries', 'integer', 50, NULL),
                ('allow_modrdn', 'true', 'true', 'Allow ModRDN Operations', 'Allow LDAP ModRDN operations for moving entries', 'boolean', 100, 'Advanced'),
                ('migrate_on_rdn_change', 'false', 'false', 'Auto-Migrate on RDN Change', 'Automatically migrate entries when an RDN setting changes', 'boolean', 110, 'Advanced'),
                ('rdn_change_confirmation', 'true', 'true', 'Require RDN Change Confirmation', 'Require confirmation before changing RDN settings', 'boolean', 120, 'Advanced')
        ) AS s(key, value, default_value, label, description, data_type, display_order, section)
        WHERE c.name = 'ldap'
    """)
    
    # Seed security settings
    op.execute("""
        INSERT INTO config_settings (category_id, key, value, default_value, label, description, data_type, display_order) 
        SELECT c.id, s.key, s.value, s.default_value, s.label, s.description, s.data_type, s.display_order
        FROM config_categories c
        CROSS JOIN (
            VALUES 
                ('require_https', 'true', 'true', 'Require HTTPS', 'Force HTTPS connections for all requests', 'boolean', 10),
                ('allowed_origins', '["*"]', '["*"]', 'Allowed CORS Origins', 'Origins allowed for CORS requests', 'list', 20),
                ('rate_limit_enabled', 'true', 'true', 'Enable Rate Limiting', 'Enable API rate limiting', 'boolean', 30),
                ('rate_limit_requests', '100', '100', 'Rate Limit Requests', 'Maximum requests per window', 'integer', 40),
                ('rate_limit_window', '60', '60', 'Rate Limit Window', 'Rate limit window in seconds', 'integer', 50)
        ) AS s(key, value, default_value, label, description, data_type, display_order)
        WHERE c.name = 'security'
    """)
    
    # Seed password policy settings
    op.execute("""
        INSERT INTO config_settings (category_id, key, value, default_value, label, description, data_type, options, display_order) 
        SELECT c.id, s.key, s.value, s.default_value, s.label, s.description, s.data_type, s.options, s.display_order
        FROM config_categories c
        CROSS JOIN (
            VALUES 
                ('min_length', '8', '8', 'Minimum Length', 'Minimum password length', 'integer', NULL, 10),
                ('require_uppercase', 'true', 'true', 'Require Uppercase', 'Password must contain uppercase letters', 'boolean', NULL, 20),
                ('require_lowercase', 'true', 'true', 'Require Lowercase', 'Password must contain lowercase letters', 'boolean', NULL, 30),
                ('require_numbers', 'true', 'true', 'Require Numbers', 'Password must contain numbers', 'boolean', NULL, 40),
                ('require_special', 'false', 'false', 'Require Special Characters', 'Password must contain special characters', 'boolean', NULL, 50),
                ('password_hash_algorithm', '"SSHA"', '"SSHA"', 'Hash Algorithm', 'Algorithm for password hashing', 'select', '[{"value": "SSHA", "label": "SSHA (Salted SHA-1)"}, {"value": "SSHA256", "label": "SSHA256"}, {"value": "SSHA512", "label": "SSHA512"}, {"value": "ARGON2", "label": "Argon2"}]', 60)
        ) AS s(key, value, default_value, label, description, data_type, options, display_order)
        WHERE c.name = 'password'
    """)
    
    # Seed session settings
    op.execute("""
        INSERT INTO config_settings (category_id, key, value, default_value, label, description, data_type, display_order) 
        SELECT c.id, s.key, s.value, s.default_value, s.label, s.description, s.data_type, s.display_order
        FROM config_categories c
        CROSS JOIN (
            VALUES 
                ('access_token_expire_minutes', '60', '60', 'Access Token Expiry', 'Access token lifetime in minutes', 'integer', 10),
                ('refresh_token_expire_days', '7', '7', 'Refresh Token Expiry', 'Refresh token lifetime in days', 'integer', 20),
                ('session_timeout_minutes', '30', '30', 'Session Timeout', 'Inactive session timeout in minutes', 'integer', 30),
                ('max_concurrent_sessions', '5', '5', 'Max Concurrent Sessions', 'Maximum sessions per user (0 = unlimited)', 'integer', 40)
        ) AS s(key, value, default_value, label, description, data_type, display_order)
        WHERE c.name = 'session'
    """)
    
    # Seed audit settings
    op.execute("""
        INSERT INTO config_settings (category_id, key, value, default_value, label, description, data_type, options, display_order) 
        SELECT c.id, s.key, s.value, s.default_value, s.label, s.description, s.data_type, s.options, s.display_order
        FROM config_categories c
        CROSS JOIN (
            VALUES 
                ('audit_enabled', 'true', 'true', 'Enable Audit Logging', 'Log all user actions', 'boolean', NULL, 10),
                ('audit_retention_days', '90', '90', 'Audit Retention', 'Days to keep audit logs', 'integer', NULL, 20),
                ('audit_level', '"info"', '"info"', 'Audit Level', 'Minimum level to log', 'select', '[{"value": "debug", "label": "Debug"}, {"value": "info", "label": "Info"}, {"value": "warning", "label": "Warning"}, {"value": "error", "label": "Error"}]', 30),
                ('log_sensitive_data', 'false', 'false', 'Log Sensitive Data', 'Include sensitive data in logs (not recommended)', 'boolean', NULL, 40)
        ) AS s(key, value, default_value, label, description, data_type, options, display_order)
        WHERE c.name = 'audit'
    """)


def downgrade() -> None:
    """Remove configuration tables."""
    op.drop_table('config_history')
    op.drop_table('plugin_configs')
    op.drop_table('config_settings')
    op.drop_table('config_categories')
