"""
ACL Endpoints
=============

ACL management endpoints for policies, assignments, and permissions.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Query, Depends

from heracles_api.core.dependencies import CurrentUser, AclGuardDep, RedisDep
from heracles_api.acl.schemas import (
    PolicyResponse,
    PolicyListResponse,
    PolicyCreate,
    PolicyUpdate,
    AssignmentResponse,
    AssignmentListResponse,
    AssignmentCreate,
    AssignmentUpdate,
    PermissionResponse,
    AttributeGroupResponse,
    MyPermissionsResponse,
    AuditLogEntry,
    AuditLogListResponse,
    PolicyAttrRuleResponse,
    PolicyAttrRuleCreate,
    PolicyDetailResponse,
)

import structlog
import asyncpg
from fastapi import Request

logger = structlog.get_logger(__name__)
router = APIRouter()


# ============================================================================
# Helper: Get DB pool from app state
# ============================================================================


async def get_db_pool(request: Request) -> asyncpg.Pool:
    """Get database pool from app state."""
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database not initialized",
        )
    return pool


DbPoolDep = Depends(get_db_pool)


# ============================================================================
# Permissions (read-only)
# ============================================================================


@router.get("/permissions", response_model=list[PermissionResponse])
async def list_permissions(
    current_user: CurrentUser,
    guard: AclGuardDep,
    request: Request,
):
    """
    List all registered permissions.
    
    Requires: acl:read
    """
    guard.require(current_user.user_dn, "acl:read")
    
    pool = await get_db_pool(request)
    
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT bit_position, scope, action, description, plugin
            FROM acl_permissions
            ORDER BY scope, action
            """
        )
    
    return [
        PermissionResponse(
            bit_position=r["bit_position"],
            name=f"{r['scope']}:{r['action']}",
            scope=r["scope"],
            action=r["action"],
            description=r["description"],
            plugin=r["plugin"],
        )
        for r in rows
    ]


# ============================================================================
# Attribute Groups (read-only)
# ============================================================================


@router.get("/attribute-groups", response_model=list[AttributeGroupResponse])
async def list_attribute_groups(
    current_user: CurrentUser,
    guard: AclGuardDep,
    request: Request,
    object_type: Optional[str] = Query(None, description="Filter by object type"),
):
    """
    List all attribute groups.
    
    Requires: acl:read
    """
    guard.require(current_user.user_dn, "acl:read")
    
    pool = await get_db_pool(request)
    
    async with pool.acquire() as conn:
        if object_type:
            rows = await conn.fetch(
                """
                SELECT id, object_type, group_name, label, attributes, plugin
                FROM acl_attribute_groups
                WHERE object_type = $1
                ORDER BY object_type, group_name
                """,
                object_type
            )
        else:
            rows = await conn.fetch(
                """
                SELECT id, object_type, group_name, label, attributes, plugin
                FROM acl_attribute_groups
                ORDER BY object_type, group_name
                """
            )
    
    return [
        AttributeGroupResponse(
            id=r["id"],
            object_type=r["object_type"],
            group_name=r["group_name"],
            label=r["label"],
            attributes=list(r["attributes"]),
            plugin=r["plugin"],
        )
        for r in rows
    ]


# ============================================================================
# Policies
# ============================================================================


@router.get("/policies", response_model=PolicyListResponse)
async def list_policies(
    current_user: CurrentUser,
    guard: AclGuardDep,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    builtin: Optional[bool] = Query(None, description="Filter by builtin status"),
):
    """
    List all ACL policies.
    
    Requires: acl:read
    """
    guard.require(current_user.user_dn, "acl:read")
    
    pool = await get_db_pool(request)
    
    async with pool.acquire() as conn:
        # Count total
        if builtin is not None:
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM acl_policies WHERE builtin = $1",
                builtin
            )
            rows = await conn.fetch(
                """
                SELECT id, name, description, perm_low, perm_high, builtin, created_at, updated_at
                FROM acl_policies
                WHERE builtin = $1
                ORDER BY name
                LIMIT $2 OFFSET $3
                """,
                builtin,
                page_size,
                (page - 1) * page_size
            )
        else:
            total = await conn.fetchval("SELECT COUNT(*) FROM acl_policies")
            rows = await conn.fetch(
                """
                SELECT id, name, description, perm_low, perm_high, builtin, created_at, updated_at
                FROM acl_policies
                ORDER BY name
                LIMIT $1 OFFSET $2
                """,
                page_size,
                (page - 1) * page_size
            )
    
    # Get registry for permission name resolution
    registry = getattr(request.app.state, "acl_registry", None)
    
    policies = []
    for r in rows:
        # Resolve permission names from bitmap
        perm_names = []
        if registry:
            from heracles_core import PermissionBitmap
            bitmap = PermissionBitmap.from_halves(r["perm_low"], r["perm_high"])
            for name, bit_pos in registry._by_name.items():
                if bitmap.has_bit(bit_pos):
                    perm_names.append(name)
        
        policies.append(PolicyResponse(
            id=r["id"],
            name=r["name"],
            description=r["description"],
            permissions=perm_names,
            builtin=r["builtin"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        ))
    
    return PolicyListResponse(
        policies=policies,
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
    request: Request,
):
    """
    Get a specific policy by ID.
    
    Requires: acl:read
    """
    guard.require(current_user.user_dn, "acl:read")
    
    pool = await get_db_pool(request)
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, name, description, perm_low, perm_high, builtin, created_at, updated_at
            FROM acl_policies
            WHERE id = $1
            """,
            policy_id
        )
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy '{policy_id}' not found",
        )
    
    # Get registry for permission name resolution
    registry = getattr(request.app.state, "acl_registry", None)
    perm_names = []
    if registry:
        from heracles_core import PermissionBitmap
        bitmap = PermissionBitmap.from_halves(row["perm_low"], row["perm_high"])
        for name, bit_pos in registry._by_name.items():
            if bitmap.has_bit(bit_pos):
                perm_names.append(name)
    
    return PolicyResponse(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        permissions=perm_names,
        builtin=row["builtin"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post("/policies", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(
    body: PolicyCreate,
    current_user: CurrentUser,
    guard: AclGuardDep,
    request: Request,
):
    """
    Create a new ACL policy.
    
    Requires: acl:manage
    """
    guard.require(current_user.user_dn, "acl:manage")
    
    pool = await get_db_pool(request)
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
    
    async with pool.acquire() as conn:
        # Check for duplicate name
        existing = await conn.fetchval(
            "SELECT 1 FROM acl_policies WHERE name = $1",
            body.name
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Policy '{body.name}' already exists",
            )
        
        row = await conn.fetchrow(
            """
            INSERT INTO acl_policies (name, description, perm_low, perm_high, builtin)
            VALUES ($1, $2, $3, $4, FALSE)
            RETURNING id, name, description, perm_low, perm_high, builtin, created_at, updated_at
            """,
            body.name,
            body.description,
            perm_low,
            perm_high
        )
    
    logger.info(
        "acl_policy_created",
        policy_id=str(row["id"]),
        name=body.name,
        by=current_user.uid,
    )
    
    return PolicyResponse(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        permissions=body.permissions,
        builtin=row["builtin"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.patch("/policies/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: UUID,
    body: PolicyUpdate,
    current_user: CurrentUser,
    guard: AclGuardDep,
    request: Request,
    redis: RedisDep,
):
    """
    Update an ACL policy.
    
    Requires: acl:manage
    
    Note: Updating a policy invalidates cached ACLs for all users with assignments to this policy.
    """
    guard.require(current_user.user_dn, "acl:manage")
    
    pool = await get_db_pool(request)
    registry = getattr(request.app.state, "acl_registry", None)
    
    if not registry:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ACL registry not initialized",
        )
    
    async with pool.acquire() as conn:
        # Get existing policy
        existing = await conn.fetchrow(
            "SELECT builtin FROM acl_policies WHERE id = $1",
            policy_id
        )
        
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Policy '{policy_id}' not found",
            )
        
        if existing["builtin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify built-in policies",
            )
        
        # Build update query dynamically
        updates = []
        params = []
        param_idx = 1
        
        if body.name is not None:
            updates.append(f"name = ${param_idx}")
            params.append(body.name)
            param_idx += 1
        
        if body.description is not None:
            updates.append(f"description = ${param_idx}")
            params.append(body.description)
            param_idx += 1
        
        if body.permissions is not None:
            try:
                perm_low, perm_high = registry.bitmap(*body.permissions)
            except KeyError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )
            updates.append(f"perm_low = ${param_idx}")
            params.append(perm_low)
            param_idx += 1
            updates.append(f"perm_high = ${param_idx}")
            params.append(perm_high)
            param_idx += 1
        
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update",
            )
        
        updates.append(f"updated_at = NOW()")
        params.append(policy_id)
        
        row = await conn.fetchrow(
            f"""
            UPDATE acl_policies
            SET {', '.join(updates)}
            WHERE id = ${param_idx}
            RETURNING id, name, description, perm_low, perm_high, builtin, created_at, updated_at
            """,
            *params
        )
        
        # Invalidate cached ACLs for affected users
        if redis:
            affected_dns = await conn.fetch(
                "SELECT DISTINCT subject_dn FROM acl_assignments WHERE policy_id = $1",
                policy_id
            )
            for r in affected_dns:
                await redis.delete(f"acl:user:{r['subject_dn']}")
    
    # Resolve permission names
    perm_names = []
    from heracles_core import PermissionBitmap
    bitmap = PermissionBitmap.from_halves(row["perm_low"], row["perm_high"])
    for name, bit_pos in registry._by_name.items():
        if bitmap.has_bit(bit_pos):
            perm_names.append(name)
    
    logger.info(
        "acl_policy_updated",
        policy_id=str(policy_id),
        by=current_user.uid,
    )
    
    return PolicyResponse(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        permissions=perm_names,
        builtin=row["builtin"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy(
    policy_id: UUID,
    current_user: CurrentUser,
    guard: AclGuardDep,
    request: Request,
    redis: RedisDep,
):
    """
    Delete an ACL policy.
    
    Requires: acl:manage
    
    Note: This will also delete all assignments using this policy.
    """
    guard.require(current_user.user_dn, "acl:manage")
    
    pool = await get_db_pool(request)
    
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT builtin FROM acl_policies WHERE id = $1",
            policy_id
        )
        
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Policy '{policy_id}' not found",
            )
        
        if existing["builtin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete built-in policies",
            )
        
        # Get affected users before deletion for cache invalidation
        if redis:
            affected_dns = await conn.fetch(
                "SELECT DISTINCT subject_dn FROM acl_assignments WHERE policy_id = $1",
                policy_id
            )
        
        # Delete (cascades to assignments)
        await conn.execute(
            "DELETE FROM acl_policies WHERE id = $1",
            policy_id
        )
        
        # Invalidate caches
        if redis:
            for r in affected_dns:
                await redis.delete(f"acl:user:{r['subject_dn']}")
    
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
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    policy_id: Optional[UUID] = Query(None, description="Filter by policy ID"),
    subject_dn: Optional[str] = Query(None, description="Filter by subject DN"),
):
    """
    List all ACL assignments.
    
    Requires: acl:read
    """
    guard.require(current_user.user_dn, "acl:read")
    
    pool = await get_db_pool(request)
    
    async with pool.acquire() as conn:
        # Build query with optional filters
        where_clauses = []
        params = []
        param_idx = 1
        
        if policy_id:
            where_clauses.append(f"a.policy_id = ${param_idx}")
            params.append(policy_id)
            param_idx += 1
        
        if subject_dn:
            where_clauses.append(f"a.subject_dn = ${param_idx}")
            params.append(subject_dn)
            param_idx += 1
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        # Count
        count_sql = f"SELECT COUNT(*) FROM acl_assignments a {where_sql}"
        total = await conn.fetchval(count_sql, *params)
        
        # Fetch with policy name
        params.extend([page_size, (page - 1) * page_size])
        rows = await conn.fetch(
            f"""
            SELECT 
                a.id, a.policy_id, p.name as policy_name,
                a.subject_type, a.subject_dn, a.scope_dn, a.scope_type,
                a.self_only, a.deny, a.priority, a.builtin, a.created_at
            FROM acl_assignments a
            JOIN acl_policies p ON p.id = a.policy_id
            {where_sql}
            ORDER BY a.priority, a.created_at
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
            """,
            *params
        )
    
    assignments = [
        AssignmentResponse(
            id=r["id"],
            policy_id=r["policy_id"],
            policy_name=r["policy_name"],
            subject_type=r["subject_type"],
            subject_dn=r["subject_dn"],
            scope_dn=r["scope_dn"],
            scope_type=r["scope_type"],
            self_only=r["self_only"],
            deny=r["deny"],
            priority=r["priority"],
            builtin=r["builtin"],
            created_at=r["created_at"],
        )
        for r in rows
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
    request: Request,
    redis: RedisDep,
):
    """
    Create a new ACL assignment.
    
    Requires: acl:manage
    """
    guard.require(current_user.user_dn, "acl:manage")
    
    pool = await get_db_pool(request)
    
    async with pool.acquire() as conn:
        # Verify policy exists
        policy = await conn.fetchrow(
            "SELECT id, name FROM acl_policies WHERE id = $1",
            body.policy_id
        )
        if not policy:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Policy '{body.policy_id}' not found",
            )
        
        # Check for duplicate
        existing = await conn.fetchval(
            """
            SELECT 1 FROM acl_assignments
            WHERE policy_id = $1 AND subject_type = $2 AND subject_dn = $3
              AND scope_dn = $4 AND self_only = $5
            """,
            body.policy_id,
            body.subject_type,
            body.subject_dn,
            body.scope_dn or "",
            body.self_only or False,
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Assignment already exists",
            )
        
        row = await conn.fetchrow(
            """
            INSERT INTO acl_assignments 
                (policy_id, subject_type, subject_dn, scope_dn, scope_type, self_only, deny, priority)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id, policy_id, subject_type, subject_dn, scope_dn, scope_type, 
                      self_only, deny, priority, builtin, created_at
            """,
            body.policy_id,
            body.subject_type,
            body.subject_dn,
            body.scope_dn or "",
            body.scope_type or "subtree",
            body.self_only or False,
            body.deny or False,
            body.priority or 0,
        )
    
    # Invalidate cache for the subject
    if redis:
        await redis.delete(f"acl:user:{body.subject_dn}")
    
    logger.info(
        "acl_assignment_created",
        assignment_id=str(row["id"]),
        policy=policy["name"],
        subject_dn=body.subject_dn,
        by=current_user.uid,
    )
    
    return AssignmentResponse(
        id=row["id"],
        policy_id=row["policy_id"],
        policy_name=policy["name"],
        subject_type=row["subject_type"],
        subject_dn=row["subject_dn"],
        scope_dn=row["scope_dn"],
        scope_type=row["scope_type"],
        self_only=row["self_only"],
        deny=row["deny"],
        priority=row["priority"],
        builtin=row["builtin"],
        created_at=row["created_at"],
    )


@router.get("/assignments/{assignment_id}", response_model=AssignmentResponse)
async def get_assignment(
    assignment_id: UUID,
    current_user: CurrentUser,
    guard: AclGuardDep,
    request: Request,
):
    """
    Get a single ACL assignment by ID.
    
    Requires: acl:read
    """
    guard.require(current_user.user_dn, "acl:read")
    
    pool = await get_db_pool(request)
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT 
                a.id, a.policy_id, p.name as policy_name,
                a.subject_type, a.subject_dn, a.scope_dn, a.scope_type,
                a.self_only, a.deny, a.priority, a.builtin, a.created_at
            FROM acl_assignments a
            JOIN acl_policies p ON p.id = a.policy_id
            WHERE a.id = $1
            """,
            assignment_id
        )
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment '{assignment_id}' not found",
        )
    
    return AssignmentResponse(
        id=row["id"],
        policy_id=row["policy_id"],
        policy_name=row["policy_name"],
        subject_type=row["subject_type"],
        subject_dn=row["subject_dn"],
        scope_dn=row["scope_dn"],
        scope_type=row["scope_type"],
        self_only=row["self_only"],
        deny=row["deny"],
        priority=row["priority"],
        builtin=row["builtin"],
        created_at=row["created_at"],
    )


@router.patch("/assignments/{assignment_id}", response_model=AssignmentResponse)
async def update_assignment(
    assignment_id: UUID,
    body: AssignmentUpdate,
    current_user: CurrentUser,
    guard: AclGuardDep,
    request: Request,
    redis: RedisDep,
):
    """
    Update an ACL assignment.
    
    Only scope_dn, scope_type, self_only, deny, and priority can be updated.
    To change the policy or subject, delete and recreate the assignment.
    
    Requires: acl:manage
    """
    guard.require(current_user.user_dn, "acl:manage")
    
    pool = await get_db_pool(request)
    
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            """
            SELECT a.id, a.builtin, a.subject_dn, p.name as policy_name
            FROM acl_assignments a
            JOIN acl_policies p ON p.id = a.policy_id
            WHERE a.id = $1
            """,
            assignment_id
        )
        
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assignment '{assignment_id}' not found",
            )
        
        if existing["builtin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify built-in assignments",
            )
        
        # Build dynamic UPDATE
        updates = []
        params = []
        param_idx = 1
        
        if body.scope_dn is not None:
            updates.append(f"scope_dn = ${param_idx}")
            params.append(body.scope_dn)
            param_idx += 1
        
        if body.scope_type is not None:
            updates.append(f"scope_type = ${param_idx}")
            params.append(body.scope_type)
            param_idx += 1
        
        if body.self_only is not None:
            updates.append(f"self_only = ${param_idx}")
            params.append(body.self_only)
            param_idx += 1
        
        if body.deny is not None:
            updates.append(f"deny = ${param_idx}")
            params.append(body.deny)
            param_idx += 1
        
        if body.priority is not None:
            updates.append(f"priority = ${param_idx}")
            params.append(body.priority)
            param_idx += 1
        
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update",
            )
        
        params.append(assignment_id)
        row = await conn.fetchrow(
            f"""
            UPDATE acl_assignments
            SET {', '.join(updates)}
            WHERE id = ${param_idx}
            RETURNING id, policy_id, subject_type, subject_dn, scope_dn, scope_type,
                      self_only, deny, priority, builtin, created_at
            """,
            *params
        )
    
    # Invalidate cache for the subject
    if redis:
        await redis.delete(f"acl:user:{row['subject_dn']}")
    
    logger.info(
        "acl_assignment_updated",
        assignment_id=str(assignment_id),
        by=current_user.uid,
    )
    
    return AssignmentResponse(
        id=row["id"],
        policy_id=row["policy_id"],
        policy_name=existing["policy_name"],
        subject_type=row["subject_type"],
        subject_dn=row["subject_dn"],
        scope_dn=row["scope_dn"],
        scope_type=row["scope_type"],
        self_only=row["self_only"],
        deny=row["deny"],
        priority=row["priority"],
        builtin=row["builtin"],
        created_at=row["created_at"],
    )


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    assignment_id: UUID,
    current_user: CurrentUser,
    guard: AclGuardDep,
    request: Request,
    redis: RedisDep,
):
    """
    Delete an ACL assignment.
    
    Requires: acl:manage
    """
    guard.require(current_user.user_dn, "acl:manage")
    
    pool = await get_db_pool(request)
    
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT subject_dn, builtin FROM acl_assignments WHERE id = $1",
            assignment_id
        )
        
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assignment '{assignment_id}' not found",
            )
        
        if existing["builtin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete built-in assignments",
            )
        
        await conn.execute(
            "DELETE FROM acl_assignments WHERE id = $1",
            assignment_id
        )
    
    # Invalidate cache
    if redis:
        await redis.delete(f"acl:user:{existing['subject_dn']}")
    
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
    
    Returns the user's effective permissions based on all their assignments.
    No special permissions required - users can always see their own permissions.
    """
    registry = getattr(request.app.state, "acl_registry", None)
    
    if not registry:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ACL registry not initialized",
        )
    
    # Get all permissions the user has
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
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user_dn: Optional[str] = Query(None, description="Filter by user DN"),
    action: Optional[str] = Query(None, description="Filter by action"),
    target_dn: Optional[str] = Query(None, description="Filter by target DN"),
    result: Optional[bool] = Query(None, description="Filter by result (true=allowed, false=denied)"),
    from_ts: Optional[str] = Query(None, description="Filter from timestamp (ISO 8601)", alias="fromTs"),
    to_ts: Optional[str] = Query(None, description="Filter to timestamp (ISO 8601)", alias="toTs"),
):
    """
    List audit log entries with optional filters.
    
    Requires: audit:read
    """
    guard.require(current_user.user_dn, "audit:read")
    
    pool = await get_db_pool(request)
    
    async with pool.acquire() as conn:
        where_clauses = []
        params = []
        param_idx = 1
        
        if user_dn:
            where_clauses.append(f"user_dn ILIKE ${param_idx}")
            params.append(f"%{user_dn}%")
            param_idx += 1
        
        if action:
            where_clauses.append(f"action = ${param_idx}")
            params.append(action)
            param_idx += 1
        
        if target_dn:
            where_clauses.append(f"target_dn ILIKE ${param_idx}")
            params.append(f"%{target_dn}%")
            param_idx += 1
        
        if result is not None:
            where_clauses.append(f"result = ${param_idx}")
            params.append(result)
            param_idx += 1
        
        if from_ts:
            where_clauses.append(f"ts >= ${param_idx}::timestamptz")
            params.append(from_ts)
            param_idx += 1
        
        if to_ts:
            where_clauses.append(f"ts <= ${param_idx}::timestamptz")
            params.append(to_ts)
            param_idx += 1
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        count_sql = f"SELECT COUNT(*) FROM acl_audit_log {where_sql}"
        total = await conn.fetchval(count_sql, *params)
        
        params.extend([page_size, (page - 1) * page_size])
        rows = await conn.fetch(
            f"""
            SELECT id, ts, user_dn, action, target_dn, permission, result, details
            FROM acl_audit_log
            {where_sql}
            ORDER BY ts DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
            """,
            *params
        )
    
    import json as json_mod
    entries = [
        AuditLogEntry(
            id=r["id"],
            ts=r["ts"],
            user_dn=r["user_dn"],
            action=r["action"],
            target_dn=r["target_dn"],
            permission=r["permission"],
            result=r["result"],
            details=json_mod.loads(r["details"]) if r["details"] else None,
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
    request: Request,
):
    """
    List attribute rules for a policy.
    
    Requires: acl:read
    """
    guard.require(current_user.user_dn, "acl:read")
    
    pool = await get_db_pool(request)
    
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, policy_id, object_type, action, rule_type, attr_groups
            FROM acl_policy_attr_rules
            WHERE policy_id = $1
            ORDER BY object_type, action, rule_type
            """,
            policy_id
        )
    
    return [
        PolicyAttrRuleResponse(
            id=r["id"],
            policy_id=r["policy_id"],
            object_type=r["object_type"],
            action=r["action"],
            rule_type=r["rule_type"],
            attr_groups=list(r["attr_groups"]),
        )
        for r in rows
    ]


@router.post("/policies/{policy_id}/attr-rules", response_model=PolicyAttrRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_policy_attr_rule(
    policy_id: UUID,
    body: PolicyAttrRuleCreate,
    current_user: CurrentUser,
    guard: AclGuardDep,
    request: Request,
    redis: RedisDep,
):
    """
    Add an attribute rule to a policy.
    
    Requires: acl:manage
    """
    guard.require(current_user.user_dn, "acl:manage")
    
    pool = await get_db_pool(request)
    
    async with pool.acquire() as conn:
        # Verify policy exists and is not builtin
        policy = await conn.fetchrow(
            "SELECT id, builtin FROM acl_policies WHERE id = $1",
            policy_id
        )
        if not policy:
            raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")
        if policy["builtin"]:
            raise HTTPException(status_code=403, detail="Cannot modify built-in policies")
        
        # Check for duplicate
        existing = await conn.fetchval(
            """
            SELECT 1 FROM acl_policy_attr_rules
            WHERE policy_id = $1 AND object_type = $2 AND action = $3 AND rule_type = $4
            """,
            policy_id, body.object_type, body.action, body.rule_type
        )
        if existing:
            raise HTTPException(status_code=409, detail="Attribute rule already exists for this combination")
        
        row = await conn.fetchrow(
            """
            INSERT INTO acl_policy_attr_rules (policy_id, object_type, action, rule_type, attr_groups)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, policy_id, object_type, action, rule_type, attr_groups
            """,
            policy_id, body.object_type, body.action, body.rule_type, body.attr_groups
        )
    
    # Invalidate caches for affected users
    if redis:
        async with pool.acquire() as conn:
            affected = await conn.fetch(
                "SELECT DISTINCT subject_dn FROM acl_assignments WHERE policy_id = $1",
                policy_id
            )
            for r in affected:
                await redis.delete(f"acl:user:{r['subject_dn']}")
    
    logger.info(
        "acl_attr_rule_created",
        policy_id=str(policy_id),
        object_type=body.object_type,
        action=body.action,
        rule_type=body.rule_type,
        by=current_user.uid,
    )
    
    return PolicyAttrRuleResponse(
        id=row["id"],
        policy_id=row["policy_id"],
        object_type=row["object_type"],
        action=row["action"],
        rule_type=row["rule_type"],
        attr_groups=list(row["attr_groups"]),
    )


@router.delete("/policies/{policy_id}/attr-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy_attr_rule(
    policy_id: UUID,
    rule_id: UUID,
    current_user: CurrentUser,
    guard: AclGuardDep,
    request: Request,
    redis: RedisDep,
):
    """
    Delete an attribute rule from a policy.
    
    Requires: acl:manage
    """
    guard.require(current_user.user_dn, "acl:manage")
    
    pool = await get_db_pool(request)
    
    async with pool.acquire() as conn:
        # Verify policy is not builtin
        policy = await conn.fetchrow(
            "SELECT builtin FROM acl_policies WHERE id = $1",
            policy_id
        )
        if not policy:
            raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")
        if policy["builtin"]:
            raise HTTPException(status_code=403, detail="Cannot modify built-in policies")
        
        existing = await conn.fetchval(
            "SELECT 1 FROM acl_policy_attr_rules WHERE id = $1 AND policy_id = $2",
            rule_id, policy_id
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Attribute rule not found")
        
        await conn.execute("DELETE FROM acl_policy_attr_rules WHERE id = $1", rule_id)
    
    if redis:
        async with pool.acquire() as conn:
            affected = await conn.fetch(
                "SELECT DISTINCT subject_dn FROM acl_assignments WHERE policy_id = $1",
                policy_id
            )
            for r in affected:
                await redis.delete(f"acl:user:{r['subject_dn']}")
    
    logger.info(
        "acl_attr_rule_deleted",
        policy_id=str(policy_id),
        rule_id=str(rule_id),
        by=current_user.uid,
    )
