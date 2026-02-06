"""
ACL Repository
==============

Data access layer for ACL PostgreSQL operations.
Replaces raw asyncpg queries with SQLAlchemy ORM.
"""

import json
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from heracles_api.models.acl import (
    AclAssignment,
    AclAttributeGroup,
    AclAuditLog,
    AclPermission,
    AclPolicy,
    AclPolicyAttrRule,
)


class AclRepository:
    """Repository for ACL database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # =========================================================================
    # Permissions
    # =========================================================================

    async def get_all_permissions(self) -> list[AclPermission]:
        stmt = (
            select(AclPermission).order_by(AclPermission.scope, AclPermission.action)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_permission_by_scope_action(
        self, scope: str, action: str
    ) -> Optional[AclPermission]:
        stmt = select(AclPermission).where(
            AclPermission.scope == scope, AclPermission.action == action
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_max_bit_position(self) -> int:
        stmt = select(func.coalesce(func.max(AclPermission.bit_position), -1))
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def upsert_permission(
        self,
        scope: str,
        action: str,
        description: str,
        plugin: Optional[str],
    ) -> Optional[int]:
        """Upsert a permission. Returns bit_position if newly created, else None."""
        existing = await self.get_permission_by_scope_action(scope, action)

        if existing:
            existing.description = description
            existing.plugin = plugin
            return None
        else:
            next_bit = (await self.get_max_bit_position()) + 1
            if next_bit > 127:
                return None
            perm = AclPermission(
                bit_position=next_bit,
                scope=scope,
                action=action,
                description=description,
                plugin=plugin,
            )
            self.session.add(perm)
            return next_bit

    async def get_all_permission_names(self) -> list[str]:
        """Get all permission names as 'scope:action'."""
        stmt = select(AclPermission.scope, AclPermission.action)
        result = await self.session.execute(stmt)
        return [f"{row.scope}:{row.action}" for row in result.all()]

    async def get_bit_positions_for_names(self, perm_names: list[str]) -> list[int]:
        """Get bit positions for a list of 'scope:action' names."""
        if not perm_names:
            return []
        stmt = select(AclPermission.bit_position).where(
            (AclPermission.scope + ":" + AclPermission.action).in_(perm_names)
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def get_all_permission_lookups(
        self,
    ) -> tuple[dict[str, int], dict[int, str]]:
        """Get by_name and by_bit lookup dicts."""
        stmt = select(
            AclPermission.bit_position, AclPermission.scope, AclPermission.action
        )
        result = await self.session.execute(stmt)
        by_name: dict[str, int] = {}
        by_bit: dict[int, str] = {}
        for row in result.all():
            name = f"{row.scope}:{row.action}"
            by_name[name] = row.bit_position
            by_bit[row.bit_position] = name
        return by_name, by_bit

    # =========================================================================
    # Attribute Groups
    # =========================================================================

    async def get_all_attribute_groups(
        self, object_type: Optional[str] = None
    ) -> list[AclAttributeGroup]:
        stmt = select(AclAttributeGroup)
        if object_type:
            stmt = stmt.where(AclAttributeGroup.object_type == object_type)
        stmt = stmt.order_by(
            AclAttributeGroup.object_type, AclAttributeGroup.group_name
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def upsert_attribute_group(
        self,
        object_type: str,
        group_name: str,
        label: str,
        attributes: list[str],
        plugin: Optional[str],
    ) -> None:
        stmt = pg_insert(AclAttributeGroup).values(
            object_type=object_type,
            group_name=group_name,
            label=label,
            attributes=attributes,
            plugin=plugin,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_acl_attr_groups_object_group",
            set_={
                "label": stmt.excluded.label,
                "attributes": stmt.excluded.attributes,
                "plugin": stmt.excluded.plugin,
            },
        )
        await self.session.execute(stmt)

    async def get_all_attr_group_lookups(
        self,
    ) -> dict[tuple[str, str], list[str]]:
        """Get (object_type, group_name) -> attributes lookup dict."""
        stmt = select(
            AclAttributeGroup.object_type,
            AclAttributeGroup.group_name,
            AclAttributeGroup.attributes,
        )
        result = await self.session.execute(stmt)
        return {
            (row.object_type, row.group_name): list(row.attributes)
            for row in result.all()
        }

    # =========================================================================
    # Policies
    # =========================================================================

    async def get_policy_by_id(self, policy_id: UUID) -> Optional[AclPolicy]:
        stmt = select(AclPolicy).where(AclPolicy.id == policy_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_policy_by_name(self, name: str) -> Optional[AclPolicy]:
        stmt = select(AclPolicy).where(AclPolicy.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def policy_name_exists(self, name: str) -> bool:
        stmt = select(func.count()).select_from(AclPolicy).where(AclPolicy.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    async def list_policies(
        self,
        page: int,
        page_size: int,
        builtin: Optional[bool] = None,
    ) -> tuple[list[AclPolicy], int]:
        count_stmt = select(func.count()).select_from(AclPolicy)
        query_stmt = select(AclPolicy).order_by(AclPolicy.name)

        if builtin is not None:
            count_stmt = count_stmt.where(AclPolicy.builtin == builtin)
            query_stmt = query_stmt.where(AclPolicy.builtin == builtin)

        total = (await self.session.execute(count_stmt)).scalar_one()
        query_stmt = query_stmt.limit(page_size).offset((page - 1) * page_size)
        result = await self.session.execute(query_stmt)
        return list(result.scalars().all()), total

    async def create_policy(
        self,
        name: str,
        description: Optional[str],
        perm_low: int,
        perm_high: int,
        builtin: bool = False,
    ) -> AclPolicy:
        policy = AclPolicy(
            name=name,
            description=description,
            perm_low=perm_low,
            perm_high=perm_high,
            builtin=builtin,
        )
        self.session.add(policy)
        await self.session.flush()
        return policy

    async def delete_policy(self, policy_id: UUID) -> None:
        stmt = delete(AclPolicy).where(AclPolicy.id == policy_id)
        await self.session.execute(stmt)

    async def upsert_builtin_policy(
        self,
        name: str,
        description: str,
        perm_low: int,
        perm_high: int,
    ) -> UUID:
        """Upsert a builtin policy, returning its id."""
        stmt = pg_insert(AclPolicy).values(
            name=name,
            description=description,
            perm_low=perm_low,
            perm_high=perm_high,
            builtin=True,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["name"],
            set_={
                "description": stmt.excluded.description,
                "perm_low": stmt.excluded.perm_low,
                "perm_high": stmt.excluded.perm_high,
                "updated_at": func.now(),
            },
        )
        stmt = stmt.returning(AclPolicy.id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update_wildcard_policy_bitmap(
        self, name: str, perm_low: int, perm_high: int
    ) -> None:
        stmt = (
            update(AclPolicy)
            .where(AclPolicy.name == name, AclPolicy.builtin == True)
            .values(perm_low=perm_low, perm_high=perm_high, updated_at=func.now())
        )
        await self.session.execute(stmt)

    # =========================================================================
    # Policy Attr Rules
    # =========================================================================

    async def get_attr_rules_for_policy(
        self, policy_id: UUID
    ) -> list[AclPolicyAttrRule]:
        stmt = (
            select(AclPolicyAttrRule)
            .where(AclPolicyAttrRule.policy_id == policy_id)
            .order_by(
                AclPolicyAttrRule.object_type,
                AclPolicyAttrRule.action,
                AclPolicyAttrRule.rule_type,
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_attr_rule(
        self,
        policy_id: UUID,
        object_type: str,
        action: str,
        rule_type: str,
        attr_groups: list[str],
    ) -> AclPolicyAttrRule:
        rule = AclPolicyAttrRule(
            policy_id=policy_id,
            object_type=object_type,
            action=action,
            rule_type=rule_type,
            attr_groups=attr_groups,
        )
        self.session.add(rule)
        await self.session.flush()
        return rule

    async def delete_attr_rule(self, rule_id: UUID) -> None:
        stmt = delete(AclPolicyAttrRule).where(AclPolicyAttrRule.id == rule_id)
        await self.session.execute(stmt)

    async def delete_all_attr_rules_for_policy(self, policy_id: UUID) -> None:
        stmt = delete(AclPolicyAttrRule).where(
            AclPolicyAttrRule.policy_id == policy_id
        )
        await self.session.execute(stmt)

    async def attr_rule_exists(
        self,
        policy_id: UUID,
        object_type: str,
        action: str,
        rule_type: str,
    ) -> bool:
        stmt = (
            select(func.count())
            .select_from(AclPolicyAttrRule)
            .where(
                AclPolicyAttrRule.policy_id == policy_id,
                AclPolicyAttrRule.object_type == object_type,
                AclPolicyAttrRule.action == action,
                AclPolicyAttrRule.rule_type == rule_type,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    async def attr_rule_belongs_to_policy(
        self, rule_id: UUID, policy_id: UUID
    ) -> bool:
        stmt = (
            select(func.count())
            .select_from(AclPolicyAttrRule)
            .where(
                AclPolicyAttrRule.id == rule_id,
                AclPolicyAttrRule.policy_id == policy_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    # =========================================================================
    # Assignments
    # =========================================================================

    async def get_assignment_by_id(
        self, assignment_id: UUID
    ) -> Optional[AclAssignment]:
        stmt = select(AclAssignment).where(AclAssignment.id == assignment_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_assignments(
        self,
        page: int,
        page_size: int,
        policy_id: Optional[UUID] = None,
        subject_dn: Optional[str] = None,
    ) -> tuple[list[tuple[AclAssignment, str]], int]:
        """Returns list of (assignment, policy_name) tuples and total count."""
        base_where = []
        if policy_id:
            base_where.append(AclAssignment.policy_id == policy_id)
        if subject_dn:
            base_where.append(AclAssignment.subject_dn == subject_dn)

        count_stmt = select(func.count()).select_from(AclAssignment)
        if base_where:
            count_stmt = count_stmt.where(*base_where)
        total = (await self.session.execute(count_stmt)).scalar_one()

        query_stmt = (
            select(AclAssignment, AclPolicy.name)
            .join(AclPolicy, AclAssignment.policy_id == AclPolicy.id)
            .order_by(AclAssignment.priority, AclAssignment.created_at)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        if base_where:
            query_stmt = query_stmt.where(*base_where)

        result = await self.session.execute(query_stmt)
        rows = [(row[0], row[1]) for row in result.all()]
        return rows, total

    async def get_assignment_with_policy_name(
        self, assignment_id: UUID
    ) -> Optional[tuple[AclAssignment, str]]:
        stmt = (
            select(AclAssignment, AclPolicy.name)
            .join(AclPolicy, AclAssignment.policy_id == AclPolicy.id)
            .where(AclAssignment.id == assignment_id)
        )
        result = await self.session.execute(stmt)
        row = result.one_or_none()
        return (row[0], row[1]) if row else None

    async def create_assignment(
        self,
        policy_id: UUID,
        subject_type: str,
        subject_dn: str,
        scope_dn: str = "",
        scope_type: str = "subtree",
        self_only: bool = False,
        deny: bool = False,
        priority: int = 0,
    ) -> AclAssignment:
        assignment = AclAssignment(
            policy_id=policy_id,
            subject_type=subject_type,
            subject_dn=subject_dn,
            scope_dn=scope_dn,
            scope_type=scope_type,
            self_only=self_only,
            deny=deny,
            priority=priority,
        )
        self.session.add(assignment)
        await self.session.flush()
        return assignment

    async def delete_assignment(self, assignment_id: UUID) -> None:
        stmt = delete(AclAssignment).where(AclAssignment.id == assignment_id)
        await self.session.execute(stmt)

    async def assignment_exists(
        self,
        policy_id: UUID,
        subject_type: str,
        subject_dn: str,
        scope_dn: str,
        self_only: bool,
    ) -> bool:
        stmt = (
            select(func.count())
            .select_from(AclAssignment)
            .where(
                AclAssignment.policy_id == policy_id,
                AclAssignment.subject_type == subject_type,
                AclAssignment.subject_dn == subject_dn,
                AclAssignment.scope_dn == scope_dn,
                AclAssignment.self_only == self_only,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    async def upsert_builtin_assignment(
        self,
        policy_id: UUID,
        subject_type: str,
        subject_dn: str,
        scope_dn: str,
        scope_type: str,
        self_only: bool,
        deny: bool,
        priority: int,
    ) -> None:
        stmt = pg_insert(AclAssignment).values(
            policy_id=policy_id,
            subject_type=subject_type,
            subject_dn=subject_dn,
            scope_dn=scope_dn,
            scope_type=scope_type,
            self_only=self_only,
            deny=deny,
            priority=priority,
            builtin=True,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_acl_assignments",
            set_={
                "scope_type": stmt.excluded.scope_type,
                "deny": stmt.excluded.deny,
                "priority": stmt.excluded.priority,
                "builtin": True,
            },
        )
        await self.session.execute(stmt)

    async def get_affected_subject_dns(self, policy_id: UUID) -> list[str]:
        stmt = (
            select(AclAssignment.subject_dn)
            .where(AclAssignment.policy_id == policy_id)
            .distinct()
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def fetch_user_acl_rows(
        self,
        user_dn: str,
        group_dns: list[str],
        role_dns: list[str],
    ) -> list[dict]:
        """Fetch all ACL data needed for ACL compilation."""
        conditions = [
            and_(
                AclAssignment.subject_type == "user",
                AclAssignment.subject_dn == user_dn,
            )
        ]
        if group_dns:
            conditions.append(
                and_(
                    AclAssignment.subject_type == "group",
                    AclAssignment.subject_dn.in_(group_dns),
                )
            )
        if role_dns:
            conditions.append(
                and_(
                    AclAssignment.subject_type == "role",
                    AclAssignment.subject_dn.in_(role_dns),
                )
            )

        stmt = (
            select(
                AclPolicy.name.label("policy_name"),
                AclPolicy.perm_low,
                AclPolicy.perm_high,
                AclAssignment.scope_dn,
                AclAssignment.scope_type,
                AclAssignment.self_only,
                AclAssignment.deny,
                AclAssignment.priority,
                AclAssignment.policy_id,
            )
            .join(AclPolicy, AclAssignment.policy_id == AclPolicy.id)
            .where(or_(*conditions))
            .order_by(AclAssignment.priority)
        )
        result = await self.session.execute(stmt)
        assignment_rows = result.all()

        # For each assignment, fetch attr rules
        output = []
        for row in assignment_rows:
            rules_stmt = select(
                AclPolicyAttrRule.object_type,
                AclPolicyAttrRule.action,
                AclPolicyAttrRule.rule_type,
                AclPolicyAttrRule.attr_groups,
            ).where(AclPolicyAttrRule.policy_id == row.policy_id)
            rules_result = await self.session.execute(rules_stmt)

            output.append(
                {
                    "policy_name": row.policy_name,
                    "perm_low": row.perm_low,
                    "perm_high": row.perm_high,
                    "scope_dn": row.scope_dn,
                    "scope_type": row.scope_type,
                    "self_only": row.self_only,
                    "deny": row.deny,
                    "priority": row.priority,
                    "attr_rules": [
                        {
                            "object_type": r.object_type,
                            "action": r.action,
                            "rule_type": r.rule_type,
                            "attr_groups": list(r.attr_groups),
                        }
                        for r in rules_result.all()
                    ],
                }
            )
        return output

    # =========================================================================
    # Audit Log
    # =========================================================================

    async def insert_audit_log(
        self,
        user_dn: str,
        action: str,
        target_dn: Optional[str],
        permission: Optional[str],
        result: Optional[bool],
        details: Optional[dict],
    ) -> None:
        log = AclAuditLog(
            user_dn=user_dn,
            action=action,
            target_dn=target_dn,
            permission=permission,
            result=result,
            details=details,
        )
        self.session.add(log)

    async def list_audit_logs(
        self,
        page: int,
        page_size: int,
        user_dn: Optional[str] = None,
        action: Optional[str] = None,
        target_dn: Optional[str] = None,
        result: Optional[bool] = None,
        from_ts: Optional[str] = None,
        to_ts: Optional[str] = None,
    ) -> tuple[list[AclAuditLog], int]:
        conditions = []
        if user_dn:
            conditions.append(AclAuditLog.user_dn.ilike(f"%{user_dn}%"))
        if action:
            conditions.append(AclAuditLog.action == action)
        if target_dn:
            conditions.append(AclAuditLog.target_dn.ilike(f"%{target_dn}%"))
        if result is not None:
            conditions.append(AclAuditLog.result == result)
        if from_ts:
            conditions.append(AclAuditLog.ts >= from_ts)
        if to_ts:
            conditions.append(AclAuditLog.ts <= to_ts)

        count_stmt = select(func.count()).select_from(AclAuditLog)
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total = (await self.session.execute(count_stmt)).scalar_one()

        query_stmt = (
            select(AclAuditLog)
            .order_by(AclAuditLog.ts.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        if conditions:
            query_stmt = query_stmt.where(*conditions)

        rows = (await self.session.execute(query_stmt)).scalars().all()
        return list(rows), total
