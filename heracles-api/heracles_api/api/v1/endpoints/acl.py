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
    PermissionResponse,
    AttributeGroupResponse,
    MyPermissionsResponse,
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
                a.self_only, a.deny, a.priority, a.created_at
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
                      self_only, deny, priority, created_at
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
            "SELECT subject_dn FROM acl_assignments WHERE id = $1",
            assignment_id
        )
        
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assignment '{assignment_id}' not found",
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
