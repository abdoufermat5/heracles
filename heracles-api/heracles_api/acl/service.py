"""
ACL Service
===========

Compiles user ACLs at login, caches in Redis, and handles invalidation.

The ACL service bridges the Python API with the Rust ACL engine,
providing efficient permission checking across the application.
"""

import json
import structlog
from typing import Optional

import asyncpg
from redis.asyncio import Redis

from heracles_api.acl.registry import PermissionRegistry

logger = structlog.get_logger(__name__)

# Redis key prefix and TTL
ACL_CACHE_PREFIX = "acl:user:"
ACL_CACHE_TTL = 3600  # 1 hour


class AclService:
    """
    ACL compilation, caching, and enforcement service.
    
    Responsibilities:
    - Compile user ACLs from database at login
    - Cache compiled ACLs in Redis
    - Invalidate caches when policies/assignments change
    - Load cached ACLs for request handling
    
    Usage:
        service = AclService(db, redis, registry)
        
        # At login
        user_acl = await service.compile_for_user(user_dn)
        
        # During request
        user_acl = await service.get_or_compile(user_dn)
        if user_acl.check(target_dn, perm_low, perm_high):
            # allowed
    """
    
    def __init__(
        self,
        db: asyncpg.Pool,
        redis: Optional[Redis],
        registry: PermissionRegistry,
    ):
        """
        Initialize the ACL service.
        
        Args:
            db: PostgreSQL connection pool.
            redis: Redis connection (optional, disables caching if None).
            registry: Permission registry for name→bit lookups.
        """
        self.db = db
        self.redis = redis
        self.registry = registry
    
    async def compile_for_user(
        self,
        user_dn: str,
        group_dns: list[str] = None,
        role_dns: list[str] = None,
    ) -> "PyUserAcl":
        """
        Compile ACL for a user from database.
        
        Fetches all applicable assignments (direct user, groups, roles)
        and compiles them into a UserAcl using the Rust engine.
        
        Args:
            user_dn: The user's DN.
            group_dns: List of group DNs the user belongs to.
            role_dns: List of role DNs the user belongs to.
            
        Returns:
            Compiled PyUserAcl for runtime checks.
        """
        from heracles_core import AclRow, AttrRuleRow, compile_user_acl
        
        group_dns = group_dns or []
        role_dns = role_dns or []
        
        async with self.db.acquire() as conn:
            # Fetch all applicable assignments with policy data
            rows = await self._fetch_acl_rows(conn, user_dn, group_dns, role_dns)
        
        # Convert to Rust-compatible format
        acl_rows = []
        for row in rows:
            # Expand attribute groups to actual attributes
            attr_rules = []
            for rule in row.get("attr_rules", []):
                attrs = self.registry.resolve_attr_groups(
                    rule["object_type"],
                    rule["attr_groups"],
                )
                attr_rules.append(AttrRuleRow(
                    object_type=rule["object_type"],
                    action=rule["action"],
                    rule_type=rule["rule_type"],
                    attributes=list(attrs),
                ))
            
            acl_rows.append(AclRow(
                policy_name=row["policy_name"],
                perm_low=row["perm_low"],
                perm_high=row["perm_high"],
                scope_dn=row["scope_dn"],
                scope_type=row["scope_type"],
                self_only=row["self_only"],
                deny=row["deny"],
                priority=row["priority"],
                attr_rules=attr_rules,
            ))
        
        # Compile using Rust engine
        user_acl = compile_user_acl(user_dn, acl_rows)
        
        # Cache in Redis
        if self.redis:
            await self._cache_acl(user_dn, user_acl)
        
        logger.debug(
            "acl_compiled",
            user_dn=user_dn,
            assignments=len(rows),
        )
        
        return user_acl
    
    async def _fetch_acl_rows(
        self,
        conn: asyncpg.Connection,
        user_dn: str,
        group_dns: list[str],
        role_dns: list[str],
    ) -> list[dict]:
        """
        Fetch all ACL rows applicable to a user.
        
        Joins acl_assignments + acl_policies + acl_policy_attr_rules
        for the user, their groups, and their roles.
        """
        # Build separate lists for query (avoids asyncpg record[] issue)
        group_dns = group_dns or []
        role_dns = role_dns or []
        
        # Fetch assignments with policies
        # Match user, any of their groups, or any of their roles
        rows = await conn.fetch(
            """
            SELECT 
                p.name as policy_name,
                p.perm_low,
                p.perm_high,
                a.scope_dn,
                a.scope_type,
                a.self_only,
                a.deny,
                a.priority,
                a.policy_id
            FROM acl_assignments a
            JOIN acl_policies p ON p.id = a.policy_id
            WHERE (a.subject_type = 'user' AND a.subject_dn = $1)
               OR (a.subject_type = 'group' AND a.subject_dn = ANY($2))
               OR (a.subject_type = 'role' AND a.subject_dn = ANY($3))
            ORDER BY a.priority ASC
            """,
            user_dn,
            group_dns,
            role_dns,
        )
        
        result = []
        for row in rows:
            # Fetch attr rules for this policy
            attr_rules = await conn.fetch(
                """
                SELECT object_type, action, rule_type, attr_groups
                FROM acl_policy_attr_rules
                WHERE policy_id = $1
                """,
                row["policy_id"]
            )
            
            result.append({
                "policy_name": row["policy_name"],
                "perm_low": row["perm_low"],
                "perm_high": row["perm_high"],
                "scope_dn": row["scope_dn"],
                "scope_type": row["scope_type"],
                "self_only": row["self_only"],
                "deny": row["deny"],
                "priority": row["priority"],
                "attr_rules": [
                    {
                        "object_type": r["object_type"],
                        "action": r["action"],
                        "rule_type": r["rule_type"],
                        "attr_groups": list(r["attr_groups"]),
                    }
                    for r in attr_rules
                ],
            })
        
        return result
    
    async def _cache_acl(self, user_dn: str, user_acl: "PyUserAcl") -> None:
        """Cache compiled ACL in Redis."""
        if not self.redis:
            return
        
        key = f"{ACL_CACHE_PREFIX}{user_dn}"
        try:
            json_data = user_acl.to_json()
            await self.redis.setex(key, ACL_CACHE_TTL, json_data)
        except Exception as e:
            logger.warning("acl_cache_set_failed", user_dn=user_dn, error=str(e))
    
    async def get_cached(self, user_dn: str) -> Optional["PyUserAcl"]:
        """
        Get cached ACL from Redis.
        
        Returns None if not cached or cache is invalid.
        """
        if not self.redis:
            return None
        
        from heracles_core import UserAcl as PyUserAcl
        
        key = f"{ACL_CACHE_PREFIX}{user_dn}"
        try:
            json_data = await self.redis.get(key)
            if json_data:
                return PyUserAcl.from_json(json_data.decode("utf-8"))
        except Exception as e:
            logger.warning("acl_cache_get_failed", user_dn=user_dn, error=str(e))
        
        return None
    
    async def get_or_compile(
        self,
        user_dn: str,
        group_dns: list[str] = None,
        role_dns: list[str] = None,
    ) -> "PyUserAcl":
        """
        Get ACL from cache or compile if not cached.
        
        This is the primary method for request handling.
        """
        # Try cache first
        cached = await self.get_cached(user_dn)
        if cached:
            return cached
        
        # Compile and cache
        return await self.compile_for_user(user_dn, group_dns, role_dns)
    
    async def invalidate_user(self, user_dn: str) -> None:
        """Invalidate cached ACL for a specific user."""
        if not self.redis:
            return
        
        key = f"{ACL_CACHE_PREFIX}{user_dn}"
        try:
            await self.redis.delete(key)
            logger.debug("acl_cache_invalidated", user_dn=user_dn)
        except Exception as e:
            logger.warning("acl_cache_invalidate_failed", user_dn=user_dn, error=str(e))
    
    async def invalidate_policy(self, policy_id: str) -> None:
        """
        Invalidate all cached ACLs for users affected by a policy change.
        
        This finds all assignments for the policy and invalidates
        the cache for each affected subject.
        """
        async with self.db.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT subject_type, subject_dn 
                FROM acl_assignments 
                WHERE policy_id = $1
                """,
                policy_id
            )
        
        for row in rows:
            if row["subject_type"] == "user":
                await self.invalidate_user(row["subject_dn"])
            elif row["subject_type"] == "group":
                # Need to invalidate all users in the group
                # This is expensive - in production, use a membership cache
                await self._invalidate_group_members(row["subject_dn"])
    
    async def _invalidate_group_members(self, group_dn: str) -> None:
        """Invalidate caches for all members of a group."""
        if not self.redis:
            return
        
        # In a production system, you'd have a cache of group memberships
        # For now, we just invalidate all cached ACLs (expensive but correct)
        logger.warning(
            "acl_group_invalidation_expensive",
            group_dn=group_dn,
            note="Consider implementing membership cache",
        )
        
        # Pattern-based deletion
        try:
            pattern = f"{ACL_CACHE_PREFIX}*"
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
                if keys:
                    await self.redis.delete(*keys)
                if cursor == 0:
                    break
        except Exception as e:
            logger.error("acl_bulk_invalidate_failed", error=str(e))
    
    async def invalidate_all(self) -> None:
        """Invalidate all cached ACLs (use sparingly)."""
        if not self.redis:
            return
        
        try:
            pattern = f"{ACL_CACHE_PREFIX}*"
            cursor = 0
            count = 0
            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
                if keys:
                    await self.redis.delete(*keys)
                    count += len(keys)
                if cursor == 0:
                    break
            logger.info("acl_cache_cleared", count=count)
        except Exception as e:
            logger.error("acl_bulk_invalidate_failed", error=str(e))
    
    async def log_check(
        self,
        user_dn: str,
        action: str,
        target_dn: Optional[str],
        permission: str,
        result: bool,
        details: Optional[dict] = None,
    ) -> None:
        """
        Log an ACL check to the audit log.
        
        This is called asynchronously (non-blocking) after permission checks.
        """
        try:
            async with self.db.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO acl_audit_log 
                        (user_dn, action, target_dn, permission, result, details)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    user_dn,
                    action,
                    target_dn,
                    permission,
                    result,
                    json.dumps(details) if details else None,
                )
        except Exception as e:
            # Don't fail the request if audit logging fails
            logger.error("acl_audit_log_failed", error=str(e))
