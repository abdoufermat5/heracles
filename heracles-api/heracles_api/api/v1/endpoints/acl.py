"""
ACL Endpoints
=============

ACL management endpoints for policies, assignments, and permissions.
"""

from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Query, Request, status

from heracles_api.acl.schemas import (
    AssignmentCreate,
    AssignmentListResponse,
    AssignmentResponse,
    AssignmentUpdate,
    AttributeGroupResponse,
    AuditLogEntry,
    AuditLogListResponse,
    MyPermissionsResponse,
    PermissionResponse,
    PolicyAttrRuleCreate,
    PolicyAttrRuleResponse,
    PolicyCreate,
    PolicyListResponse,
    PolicyResponse,
    PolicyUpdate,
)
from heracles_api.core.dependencies import AclGuardDep, AclRepoDep, CurrentUser, RedisDep

logger = structlog.get_logger(__name__)
router = APIRouter()


# ============================================================================
# Permissions (read-only)
# ============================================================================


@router.get("/permissions", response_model=list[PermissionResponse])
async def list_permissions(
    current_user: CurrentUser,
    guard: AclGuardDep,
    acl_repo: AclRepoDep,
):
    """
    List all registered permissions.

    Requires: acl:read
    """
    guard.require(current_user.user_dn, "acl:read")

    permissions = await acl_repo.get_all_permissions()

    return [
        PermissionResponse(
            bit_position=p.bit_position,
            name=f"{p.scope}:{p.action}",
            scope=p.scope,
            action=p.action,
            description=p.description,
            plugin=p.plugin,
        )
        for p in permissions
    ]


# ============================================================================
# Attribute Groups (read-only)
# ============================================================================


@router.get("/attribute-groups", response_model=list[AttributeGroupResponse])
async def list_attribute_groups(
    current_user: CurrentUser,
    guard: AclGuardDep,
    acl_repo: AclRepoDep,
    object_type: str | None = Query(None, description="Filter by object type"),
):
    """
    List all attribute groups.

    Requires: acl:read
    """
    guard.require(current_user.user_dn, "acl:read")

    groups = await acl_repo.get_all_attribute_groups(object_type=object_type)

    return [
        AttributeGroupResponse(
            id=g.id,
            object_type=g.object_type,
            group_name=g.group_name,
            label=g.label,
            attributes=list(g.attributes),
            plugin=g.plugin,
        )
        for g in groups
    ]


# ============================================================================
# Policies
# ============================================================================


def _resolve_perm_names(registry, perm_low: int, perm_high: int) -> list[str]:
    """Resolve permission names from bitmap halves using the registry."""
    perm_names = []
    if registry:
        from heracles_core import PermissionBitmap

        bitmap = PermissionBitmap.from_halves(perm_low, perm_high)
        for name, bit_pos in registry._by_name.items():
            if bitmap.has_bit(bit_pos):
                perm_names.append(name)
    return perm_names


@router.get("/policies", response_model=PolicyListResponse)
async def list_policies(
    current_user: CurrentUser,
    guard: AclGuardDep,
    acl_repo: AclRepoDep,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    builtin: bool | None = Query(None, description="Filter by builtin status"),
):
    """
    List all ACL policies.

    Requires: acl:read
    """
    guard.require(current_user.user_dn, "acl:read")

    policies, total = await acl_repo.list_policies(page, page_size, builtin=builtin)

    registry = getattr(request.app.state, "acl_registry", None)

    result = []
    for p in policies:
        perm_names = _resolve_perm_names(registry, p.perm_low, p.perm_high)
        result.append(
            PolicyResponse(
                id=p.id,
                name=p.name,
                description=p.description,
                permissions=perm_names,
                builtin=p.builtin,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
        )

    return PolicyListResponse(
        policies=result,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.get("/policies/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: UUID,
    current_user: CurrentUser,
    guard: AclGuardDep,
    acl_repo: AclRepoDep,
    request: Request,
):
    """
    Get a specific policy by ID.

    Requires: acl:read
    """
    guard.require(current_user.user_dn, "acl:read")

    policy = await acl_repo.get_policy_by_id(policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy '{policy_id}' not found",
        )

    registry = getattr(request.app.state, "acl_registry", None)
    perm_names = _resolve_perm_names(registry, policy.perm_low, policy.perm_high)

    return PolicyResponse(
        id=policy.id,
        name=policy.name,
        description=policy.description,
        permissions=perm_names,
        builtin=policy.builtin,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


@router.post("/policies", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(
    body: PolicyCreate,
    current_user: CurrentUser,
    guard: AclGuardDep,
    acl_repo: AclRepoDep,
    request: Request,
):
    """
    Create a new ACL policy.

    Requires: acl:manage
    """
    guard.require(current_user.user_dn, "acl:manage")

    registry = getattr(request.app.state, "acl_registry", None)
    if not registry:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ACL registry not initialized",
        )

    # Convert permission names to bitmap
    try:
        perm_low, perm_high = registry.bitmap(*body.permissions)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Check for duplicate name
    if await acl_repo.policy_name_exists(body.name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Policy '{body.name}' already exists",
        )

    policy = await acl_repo.create_policy(
        name=body.name,
        description=body.description,
        perm_low=perm_low,
        perm_high=perm_high,
    )

    logger.info(
        "acl_policy_created",
        policy_id=str(policy.id),
        name=body.name,
        by=current_user.uid,
    )

    return PolicyResponse(
        id=policy.id,
        name=policy.name,
        description=policy.description,
        permissions=body.permissions,
        builtin=policy.builtin,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


@router.patch("/policies/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: UUID,
    body: PolicyUpdate,
    current_user: CurrentUser,
    guard: AclGuardDep,
    acl_repo: AclRepoDep,
    request: Request,
    redis: RedisDep,
):
    """
    Update an ACL policy.

    Requires: acl:manage
    """
    guard.require(current_user.user_dn, "acl:manage")

    registry = getattr(request.app.state, "acl_registry", None)
    if not registry:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ACL registry not initialized",
        )

    policy = await acl_repo.get_policy_by_id(policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy '{policy_id}' not found",
        )

    if policy.builtin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify built-in policies",
        )

    # Apply updates
    has_updates = False
    if body.name is not None:
        policy.name = body.name
        has_updates = True
    if body.description is not None:
        policy.description = body.description
        has_updates = True
    if body.permissions is not None:
        try:
            perm_low, perm_high = registry.bitmap(*body.permissions)
        except KeyError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        policy.perm_low = perm_low
        policy.perm_high = perm_high
        has_updates = True

    if not has_updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    from sqlalchemy.sql import func

    policy.updated_at = func.now()
    await acl_repo.session.flush()

    # Invalidate cached ACLs for affected users
    if redis:
        affected_dns = await acl_repo.get_affected_subject_dns(policy_id)
        for dn in affected_dns:
            await redis.delete(f"acl:user:{dn}")

    perm_names = _resolve_perm_names(registry, policy.perm_low, policy.perm_high)

    logger.info(
        "acl_policy_updated",
        policy_id=str(policy_id),
        by=current_user.uid,
    )

    return PolicyResponse(
        id=policy.id,
        name=policy.name,
        description=policy.description,
        permissions=perm_names,
        builtin=policy.builtin,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


@router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy(
    policy_id: UUID,
    current_user: CurrentUser,
    guard: AclGuardDep,
    acl_repo: AclRepoDep,
    redis: RedisDep,
):
    """
    Delete an ACL policy.

    Requires: acl:manage
    """
    guard.require(current_user.user_dn, "acl:manage")

    policy = await acl_repo.get_policy_by_id(policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy '{policy_id}' not found",
        )

    if policy.builtin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete built-in policies",
        )

    # Get affected users before deletion for cache invalidation
    affected_dns = []
    if redis:
        affected_dns = await acl_repo.get_affected_subject_dns(policy_id)

    await acl_repo.delete_policy(policy_id)

    # Invalidate caches
    if redis:
        for dn in affected_dns:
            await redis.delete(f"acl:user:{dn}")

    logger.info(
        "acl_policy_deleted",
        policy_id=str(policy_id),
        by=current_user.uid,
    )


# ============================================================================
# Assignments
# ============================================================================


@router.get("/assignments", response_model=AssignmentListResponse)
async def list_assignments(
    current_user: CurrentUser,
    guard: AclGuardDep,
    acl_repo: AclRepoDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    policy_id: UUID | None = Query(None, description="Filter by policy ID"),
    subject_dn: str | None = Query(None, description="Filter by subject DN"),
):
    """
    List all ACL assignments.

    Requires: acl:read
    """
    guard.require(current_user.user_dn, "acl:read")

    rows, total = await acl_repo.list_assignments(page, page_size, policy_id=policy_id, subject_dn=subject_dn)

    assignments = [
        AssignmentResponse(
            id=a.id,
            policy_id=a.policy_id,
            policy_name=policy_name,
            subject_type=a.subject_type,
            subject_dn=a.subject_dn,
            scope_dn=a.scope_dn,
            scope_type=a.scope_type,
            self_only=a.self_only,
            deny=a.deny,
            priority=a.priority,
            builtin=a.builtin,
            created_at=a.created_at,
        )
        for a, policy_name in rows
    ]

    return AssignmentListResponse(
        assignments=assignments,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.post("/assignments", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    body: AssignmentCreate,
    current_user: CurrentUser,
    guard: AclGuardDep,
    acl_repo: AclRepoDep,
    redis: RedisDep,
):
    """
    Create a new ACL assignment.

    Requires: acl:manage
    """
    guard.require(current_user.user_dn, "acl:manage")

    # Verify policy exists
    policy = await acl_repo.get_policy_by_id(body.policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Policy '{body.policy_id}' not found",
        )

    # Check for duplicate
    if await acl_repo.assignment_exists(
        body.policy_id,
        body.subject_type,
        body.subject_dn,
        body.scope_dn or "",
        body.self_only or False,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assignment already exists",
        )

    assignment = await acl_repo.create_assignment(
        policy_id=body.policy_id,
        subject_type=body.subject_type,
        subject_dn=body.subject_dn,
        scope_dn=body.scope_dn or "",
        scope_type=body.scope_type or "subtree",
        self_only=body.self_only or False,
        deny=body.deny or False,
        priority=body.priority or 0,
    )

    # Invalidate cache for the subject
    if redis:
        await redis.delete(f"acl:user:{body.subject_dn}")

    logger.info(
        "acl_assignment_created",
        assignment_id=str(assignment.id),
        policy=policy.name,
        subject_dn=body.subject_dn,
        by=current_user.uid,
    )

    return AssignmentResponse(
        id=assignment.id,
        policy_id=assignment.policy_id,
        policy_name=policy.name,
        subject_type=assignment.subject_type,
        subject_dn=assignment.subject_dn,
        scope_dn=assignment.scope_dn,
        scope_type=assignment.scope_type,
        self_only=assignment.self_only,
        deny=assignment.deny,
        priority=assignment.priority,
        builtin=assignment.builtin,
        created_at=assignment.created_at,
    )


@router.get("/assignments/{assignment_id}", response_model=AssignmentResponse)
async def get_assignment(
    assignment_id: UUID,
    current_user: CurrentUser,
    guard: AclGuardDep,
    acl_repo: AclRepoDep,
):
    """
    Get a single ACL assignment by ID.

    Requires: acl:read
    """
    guard.require(current_user.user_dn, "acl:read")

    result = await acl_repo.get_assignment_with_policy_name(assignment_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment '{assignment_id}' not found",
        )

    a, policy_name = result
    return AssignmentResponse(
        id=a.id,
        policy_id=a.policy_id,
        policy_name=policy_name,
        subject_type=a.subject_type,
        subject_dn=a.subject_dn,
        scope_dn=a.scope_dn,
        scope_type=a.scope_type,
        self_only=a.self_only,
        deny=a.deny,
        priority=a.priority,
        builtin=a.builtin,
        created_at=a.created_at,
    )


@router.patch("/assignments/{assignment_id}", response_model=AssignmentResponse)
async def update_assignment(
    assignment_id: UUID,
    body: AssignmentUpdate,
    current_user: CurrentUser,
    guard: AclGuardDep,
    acl_repo: AclRepoDep,
    redis: RedisDep,
):
    """
    Update an ACL assignment.

    Only scope_dn, scope_type, self_only, deny, and priority can be updated.

    Requires: acl:manage
    """
    guard.require(current_user.user_dn, "acl:manage")

    result = await acl_repo.get_assignment_with_policy_name(assignment_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment '{assignment_id}' not found",
        )

    assignment, policy_name = result

    if assignment.builtin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify built-in assignments",
        )

    # Apply updates
    has_updates = False
    if body.scope_dn is not None:
        assignment.scope_dn = body.scope_dn
        has_updates = True
    if body.scope_type is not None:
        assignment.scope_type = body.scope_type
        has_updates = True
    if body.self_only is not None:
        assignment.self_only = body.self_only
        has_updates = True
    if body.deny is not None:
        assignment.deny = body.deny
        has_updates = True
    if body.priority is not None:
        assignment.priority = body.priority
        has_updates = True

    if not has_updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    await acl_repo.session.flush()

    # Invalidate cache for the subject
    if redis:
        await redis.delete(f"acl:user:{assignment.subject_dn}")

    logger.info(
        "acl_assignment_updated",
        assignment_id=str(assignment_id),
        by=current_user.uid,
    )

    return AssignmentResponse(
        id=assignment.id,
        policy_id=assignment.policy_id,
        policy_name=policy_name,
        subject_type=assignment.subject_type,
        subject_dn=assignment.subject_dn,
        scope_dn=assignment.scope_dn,
        scope_type=assignment.scope_type,
        self_only=assignment.self_only,
        deny=assignment.deny,
        priority=assignment.priority,
        builtin=assignment.builtin,
        created_at=assignment.created_at,
    )


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    assignment_id: UUID,
    current_user: CurrentUser,
    guard: AclGuardDep,
    acl_repo: AclRepoDep,
    redis: RedisDep,
):
    """
    Delete an ACL assignment.

    Requires: acl:manage
    """
    guard.require(current_user.user_dn, "acl:manage")

    assignment = await acl_repo.get_assignment_by_id(assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment '{assignment_id}' not found",
        )

    if assignment.builtin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete built-in assignments",
        )

    subject_dn = assignment.subject_dn
    await acl_repo.delete_assignment(assignment_id)

    # Invalidate cache
    if redis:
        await redis.delete(f"acl:user:{subject_dn}")

    logger.info(
        "acl_assignment_deleted",
        assignment_id=str(assignment_id),
        by=current_user.uid,
    )


# ============================================================================
# My Permissions (for current user)
# ============================================================================


@router.get("/me/permissions", response_model=MyPermissionsResponse)
async def get_my_permissions(
    current_user: CurrentUser,
    guard: AclGuardDep,
    request: Request,
):
    """
    Get the current user's resolved permissions.

    No special permissions required.
    """
    registry = getattr(request.app.state, "acl_registry", None)

    if not registry:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ACL registry not initialized",
        )

    permissions = []
    for perm_name in registry._by_name.keys():
        if guard.can(current_user.user_dn, perm_name):
            permissions.append(perm_name)

    permissions.sort()

    return MyPermissionsResponse(
        user_dn=current_user.user_dn,
        permissions=permissions,
    )


# ============================================================================
# Audit Log
# ============================================================================


@router.get("/audit", response_model=AuditLogListResponse)
async def list_audit_logs(
    current_user: CurrentUser,
    guard: AclGuardDep,
    acl_repo: AclRepoDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user_dn: str | None = Query(None, description="Filter by user DN"),
    action: str | None = Query(None, description="Filter by action"),
    target_dn: str | None = Query(None, description="Filter by target DN"),
    result: bool | None = Query(None, description="Filter by result (true=allowed, false=denied)"),
    from_ts: str | None = Query(None, description="Filter from timestamp (ISO 8601)", alias="fromTs"),
    to_ts: str | None = Query(None, description="Filter to timestamp (ISO 8601)", alias="toTs"),
):
    """
    List audit log entries with optional filters.

    Requires: audit:read
    """
    guard.require(current_user.user_dn, "audit:read")

    rows, total = await acl_repo.list_audit_logs(
        page,
        page_size,
        user_dn=user_dn,
        action=action,
        target_dn=target_dn,
        result=result,
        from_ts=from_ts,
        to_ts=to_ts,
    )

    entries = [
        AuditLogEntry(
            id=r.id,
            ts=r.ts,
            user_dn=r.user_dn,
            action=r.action,
            target_dn=r.target_dn,
            permission=r.permission,
            result=r.result,
            details=r.details,
        )
        for r in rows
    ]

    return AuditLogListResponse(
        entries=entries,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


# ============================================================================
# Policy Attribute Rules
# ============================================================================


@router.get("/policies/{policy_id}/attr-rules", response_model=list[PolicyAttrRuleResponse])
async def list_policy_attr_rules(
    policy_id: UUID,
    current_user: CurrentUser,
    guard: AclGuardDep,
    acl_repo: AclRepoDep,
):
    """
    List attribute rules for a policy.

    Requires: acl:read
    """
    guard.require(current_user.user_dn, "acl:read")

    rules = await acl_repo.get_attr_rules_for_policy(policy_id)

    return [
        PolicyAttrRuleResponse(
            id=r.id,
            policy_id=r.policy_id,
            object_type=r.object_type,
            action=r.action,
            rule_type=r.rule_type,
            attr_groups=list(r.attr_groups),
        )
        for r in rules
    ]


@router.post(
    "/policies/{policy_id}/attr-rules", response_model=PolicyAttrRuleResponse, status_code=status.HTTP_201_CREATED
)
async def create_policy_attr_rule(
    policy_id: UUID,
    body: PolicyAttrRuleCreate,
    current_user: CurrentUser,
    guard: AclGuardDep,
    acl_repo: AclRepoDep,
    redis: RedisDep,
):
    """
    Add an attribute rule to a policy.

    Requires: acl:manage
    """
    guard.require(current_user.user_dn, "acl:manage")

    # Verify policy exists and is not builtin
    policy = await acl_repo.get_policy_by_id(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")
    if policy.builtin:
        raise HTTPException(status_code=403, detail="Cannot modify built-in policies")

    # Check for duplicate
    if await acl_repo.attr_rule_exists(policy_id, body.object_type, body.action, body.rule_type):
        raise HTTPException(status_code=409, detail="Attribute rule already exists for this combination")

    rule = await acl_repo.create_attr_rule(
        policy_id=policy_id,
        object_type=body.object_type,
        action=body.action,
        rule_type=body.rule_type,
        attr_groups=body.attr_groups,
    )

    # Invalidate caches for affected users
    if redis:
        affected_dns = await acl_repo.get_affected_subject_dns(policy_id)
        for dn in affected_dns:
            await redis.delete(f"acl:user:{dn}")

    logger.info(
        "acl_attr_rule_created",
        policy_id=str(policy_id),
        object_type=body.object_type,
        action=body.action,
        rule_type=body.rule_type,
        by=current_user.uid,
    )

    return PolicyAttrRuleResponse(
        id=rule.id,
        policy_id=rule.policy_id,
        object_type=rule.object_type,
        action=rule.action,
        rule_type=rule.rule_type,
        attr_groups=list(rule.attr_groups),
    )


@router.delete("/policies/{policy_id}/attr-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy_attr_rule(
    policy_id: UUID,
    rule_id: UUID,
    current_user: CurrentUser,
    guard: AclGuardDep,
    acl_repo: AclRepoDep,
    redis: RedisDep,
):
    """
    Delete an attribute rule from a policy.

    Requires: acl:manage
    """
    guard.require(current_user.user_dn, "acl:manage")

    # Verify policy is not builtin
    policy = await acl_repo.get_policy_by_id(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")
    if policy.builtin:
        raise HTTPException(status_code=403, detail="Cannot modify built-in policies")

    if not await acl_repo.attr_rule_belongs_to_policy(rule_id, policy_id):
        raise HTTPException(status_code=404, detail="Attribute rule not found")

    await acl_repo.delete_attr_rule(rule_id)

    if redis:
        affected_dns = await acl_repo.get_affected_subject_dns(policy_id)
        for dn in affected_dns:
            await redis.delete(f"acl:user:{dn}")

    logger.info(
        "acl_attr_rule_deleted",
        policy_id=str(policy_id),
        rule_id=str(rule_id),
        by=current_user.uid,
    )
