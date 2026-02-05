"""Create ACL tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-02-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create ACL tables for the high-performance permission system."""

    # =========================================================================
    # Layer 1: Object-Level Permissions (Bitmap-Indexed)
    # =========================================================================
    op.create_table(
        'acl_permissions',
        sa.Column('bit_position', sa.SmallInteger, primary_key=True),
        sa.Column('scope', sa.String(64), nullable=False),
        sa.Column('action', sa.String(32), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('plugin', sa.String(64), nullable=True),  # NULL = core
        sa.CheckConstraint('bit_position >= 0 AND bit_position <= 127', name='ck_acl_permissions_bit_range'),
        sa.UniqueConstraint('scope', 'action', name='uq_acl_permissions_scope_action'),
    )

    # =========================================================================
    # Layer 2: Attribute Groups (Per Object Type)
    # =========================================================================
    op.create_table(
        'acl_attribute_groups',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('object_type', sa.String(64), nullable=False),
        sa.Column('group_name', sa.String(64), nullable=False),
        sa.Column('label', sa.String(128), nullable=False),
        sa.Column('attributes', sa.ARRAY(sa.Text), nullable=False),
        sa.Column('plugin', sa.String(64), nullable=True),  # NULL = core
        sa.UniqueConstraint('object_type', 'group_name', name='uq_acl_attr_groups_object_group'),
    )
    op.create_index('idx_acl_attr_groups_object_type', 'acl_attribute_groups', ['object_type'])

    # =========================================================================
    # Policies
    # =========================================================================
    op.create_table(
        'acl_policies',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(128), unique=True, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('perm_low', sa.BigInteger, nullable=False, server_default='0'),   # bits 0-63
        sa.Column('perm_high', sa.BigInteger, nullable=False, server_default='0'),  # bits 64-127
        sa.Column('builtin', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
    )

    # =========================================================================
    # Policy Attribute Rules
    # =========================================================================
    op.create_table(
        'acl_policy_attr_rules',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('policy_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('acl_policies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('object_type', sa.String(64), nullable=False),
        sa.Column('action', sa.String(8), nullable=False),
        sa.Column('rule_type', sa.String(8), nullable=False),
        sa.Column('attr_groups', sa.ARRAY(sa.Text), nullable=False),  # Group names
        sa.CheckConstraint("action IN ('read', 'write')", name='ck_acl_policy_attr_action'),
        sa.CheckConstraint("rule_type IN ('allow', 'deny')", name='ck_acl_policy_attr_rule_type'),
        sa.UniqueConstraint('policy_id', 'object_type', 'action', 'rule_type',
                           name='uq_acl_policy_attr_rules'),
    )
    op.create_index('idx_acl_policy_attr_rules_policy', 'acl_policy_attr_rules', ['policy_id'])

    # =========================================================================
    # Assignments
    # =========================================================================
    op.create_table(
        'acl_assignments',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('policy_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('acl_policies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('subject_type', sa.String(8), nullable=False),
        sa.Column('subject_dn', sa.String(512), nullable=False),
        sa.Column('scope_dn', sa.String(512), nullable=False, server_default=''),  # '' = global
        sa.Column('scope_type', sa.String(8), nullable=False, server_default='subtree'),
        sa.Column('self_only', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('deny', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('priority', sa.SmallInteger, nullable=False, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.CheckConstraint("subject_type IN ('user', 'group', 'role')",
                          name='ck_acl_assignments_subject_type'),
        sa.CheckConstraint("scope_type IN ('base', 'subtree')",
                          name='ck_acl_assignments_scope_type'),
        sa.UniqueConstraint('policy_id', 'subject_type', 'subject_dn', 'scope_dn', 'self_only',
                           name='uq_acl_assignments'),
    )
    op.create_index('idx_acl_assignments_subject', 'acl_assignments', ['subject_type', 'subject_dn'])
    op.create_index('idx_acl_assignments_policy', 'acl_assignments', ['policy_id'])

    # =========================================================================
    # Audit Log
    # =========================================================================
    op.create_table(
        'acl_audit_log',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('ts', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('user_dn', sa.String(512), nullable=False),
        sa.Column('action', sa.String(32), nullable=False),
        sa.Column('target_dn', sa.String(512), nullable=True),
        sa.Column('permission', sa.String(96), nullable=True),  # 'user:write' or 'user:write:contact'
        sa.Column('result', sa.Boolean, nullable=True),  # allowed/denied
        sa.Column('details', sa.dialects.postgresql.JSONB, nullable=True),
    )
    op.create_index('idx_acl_audit_ts', 'acl_audit_log', ['ts'])
    op.create_index('idx_acl_audit_user', 'acl_audit_log', ['user_dn'])


def downgrade() -> None:
    """Drop ACL tables."""
    op.drop_table('acl_audit_log')
    op.drop_table('acl_assignments')
    op.drop_table('acl_policy_attr_rules')
    op.drop_table('acl_policies')
    op.drop_table('acl_attribute_groups')
    op.drop_table('acl_permissions')
