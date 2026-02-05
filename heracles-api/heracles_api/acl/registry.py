"""
Permission Registry
===================

Loads ACL definitions from JSON files, syncs to PostgreSQL,
and provides runtime lookups. No hardcoded constants.

Bit positions are assigned by the database (auto-increment on first insert)
and are stable across restarts.
"""

import json
import structlog
from pathlib import Path
from typing import Any, Optional

import asyncpg

logger = structlog.get_logger(__name__)


class PermissionRegistry:
    """
    Central registry for ACL permissions and attribute groups.
    
    Loads definitions from JSON files (core + plugins), syncs to PostgreSQL,
    and provides efficient runtime lookups for permission name → bit position.
    
    Usage:
        registry = PermissionRegistry()
        await registry.load(db_pool, plugins=[...])
        
        # Get bitmap for permission names
        low, high = registry.bitmap("user:read", "user:write")
        
        # Resolve attribute groups to actual attributes
        attrs = registry.resolve_attr_groups("user", ["identity", "contact"])
    """
    
    def __init__(self):
        # "scope:action" -> bit_position
        self._by_name: dict[str, int] = {}
        # bit_position -> "scope:action"
        self._by_bit: dict[int, str] = {}
        # (object_type, group_name) -> [attribute_names]
        self._attr_groups: dict[tuple[str, str], list[str]] = {}
        # Cache of loaded JSON files
        self._loaded_sources: list[str] = []
    
    async def load(
        self,
        db: asyncpg.Pool,
        plugins: Optional[list[Any]] = None,
    ) -> None:
        """
        Load ACL definitions from JSON files and sync to PostgreSQL.
        
        1. Load core_acl.json
        2. For each enabled plugin, load its acl.json (if exists)
        3. Upsert permissions (assign bit positions if new)
        4. Upsert attribute groups
        5. Upsert built-in policies
        6. Build in-memory lookups from database
        
        Args:
            db: PostgreSQL connection pool.
            plugins: List of Plugin instances (optional).
        """
        plugins = plugins or []
        
        # Load core definitions
        core_path = Path(__file__).parent / "core_acl.json"
        if core_path.exists():
            await self._load_json_file(db, core_path, plugin_name=None)
        else:
            logger.warning("core_acl_not_found", path=str(core_path))
        
        # Load plugin definitions
        for plugin in plugins:
            acl_file = getattr(plugin, "acl_file", None)
            if callable(acl_file):
                path = acl_file()
                if path and path.exists():
                    info = plugin.info()
                    await self._load_json_file(db, path, plugin_name=info.name)
        
        # Rebuild in-memory lookups from database
        await self._rebuild_lookups(db)
        
        logger.info(
            "acl_registry_loaded",
            permissions=len(self._by_name),
            attr_groups=len(self._attr_groups),
            sources=self._loaded_sources,
        )
    
    async def _load_json_file(
        self,
        db: asyncpg.Pool,
        path: Path,
        plugin_name: Optional[str],
    ) -> None:
        """Load a single ACL JSON file and sync to database."""
        try:
            with open(path, "r") as f:
                data = json.load(f)
        except Exception as e:
            logger.error("acl_json_load_failed", path=str(path), error=str(e))
            return
        
        source = plugin_name or "core"
        self._loaded_sources.append(source)
        
        async with db.acquire() as conn:
            # Sync permissions
            for perm in data.get("permissions", []):
                await self._upsert_permission(
                    conn,
                    scope=perm["scope"],
                    action=perm["action"],
                    description=perm["description"],
                    plugin=plugin_name,
                )
            
            # Sync attribute groups
            for group in data.get("attribute_groups", []):
                await self._upsert_attr_group(
                    conn,
                    object_type=group["object_type"],
                    group_name=group["group_name"],
                    label=group["label"],
                    attributes=group["attributes"],
                    plugin=plugin_name,
                )
            
            # Sync built-in policies
            for policy in data.get("policies", []):
                if policy.get("builtin", False):
                    await self._upsert_policy(conn, policy, plugin_name)
            
            # Sync initial assignments (only from core, not plugins)
            if plugin_name is None:
                for assignment in data.get("initial_assignments", []):
                    await self._upsert_initial_assignment(conn, assignment)
    
    async def _upsert_permission(
        self,
        conn: asyncpg.Connection,
        scope: str,
        action: str,
        description: str,
        plugin: Optional[str],
    ) -> None:
        """Upsert a permission, assigning bit position if new."""
        # Check if exists
        existing = await conn.fetchrow(
            """
            SELECT bit_position FROM acl_permissions 
            WHERE scope = $1 AND action = $2
            """,
            scope, action
        )
        
        if existing:
            # Update description/plugin only
            await conn.execute(
                """
                UPDATE acl_permissions 
                SET description = $3, plugin = $4
                WHERE scope = $1 AND action = $2
                """,
                scope, action, description, plugin
            )
        else:
            # Assign new bit position
            next_bit = await conn.fetchval(
                "SELECT COALESCE(MAX(bit_position), -1) + 1 FROM acl_permissions"
            )
            if next_bit > 127:
                logger.error(
                    "acl_permission_limit_exceeded",
                    scope=scope,
                    action=action,
                    max_bits=128,
                )
                return
            
            await conn.execute(
                """
                INSERT INTO acl_permissions (bit_position, scope, action, description, plugin)
                VALUES ($1, $2, $3, $4, $5)
                """,
                next_bit, scope, action, description, plugin
            )
            logger.debug(
                "acl_permission_created",
                scope=scope,
                action=action,
                bit=next_bit,
            )
    
    async def _upsert_attr_group(
        self,
        conn: asyncpg.Connection,
        object_type: str,
        group_name: str,
        label: str,
        attributes: list[str],
        plugin: Optional[str],
    ) -> None:
        """Upsert an attribute group."""
        await conn.execute(
            """
            INSERT INTO acl_attribute_groups (object_type, group_name, label, attributes, plugin)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (object_type, group_name) DO UPDATE SET
                label = EXCLUDED.label,
                attributes = EXCLUDED.attributes,
                plugin = EXCLUDED.plugin
            """,
            object_type, group_name, label, attributes, plugin
        )
    
    async def _upsert_policy(
        self,
        conn: asyncpg.Connection,
        policy: dict,
        plugin: Optional[str],
    ) -> None:
        """Upsert a built-in policy with its permission bitmap."""
        name = policy["name"]
        description = policy.get("description", "")
        perm_names = policy.get("permissions", [])
        
        # Handle wildcard "*" - grant all registered permissions
        if perm_names == "*":
            rows = await conn.fetch(
                "SELECT scope || ':' || action AS name FROM acl_permissions"
            )
            perm_names = [row["name"] for row in rows]
        
        # Calculate bitmap from permission names
        perm_low, perm_high = await self._calculate_bitmap(conn, perm_names)
        
        # Upsert policy
        policy_id = await conn.fetchval(
            """
            INSERT INTO acl_policies (name, description, perm_low, perm_high, builtin)
            VALUES ($1, $2, $3, $4, true)
            ON CONFLICT (name) DO UPDATE SET
                description = EXCLUDED.description,
                perm_low = EXCLUDED.perm_low,
                perm_high = EXCLUDED.perm_high,
                updated_at = NOW()
            RETURNING id
            """,
            name, description, perm_low, perm_high
        )
        
        # Delete existing attr rules for this policy
        await conn.execute(
            "DELETE FROM acl_policy_attr_rules WHERE policy_id = $1",
            policy_id
        )
        
        # Insert attr rules
        for rule in policy.get("attr_rules", []):
            await conn.execute(
                """
                INSERT INTO acl_policy_attr_rules 
                    (policy_id, object_type, action, rule_type, attr_groups)
                VALUES ($1, $2, $3, $4, $5)
                """,
                policy_id,
                rule["object_type"],
                rule["action"],
                rule["rule_type"],
                rule["attr_groups"],
            )
    
    async def _upsert_initial_assignment(
        self,
        conn: asyncpg.Connection,
        assignment: dict,
    ) -> None:
        """
        Upsert an initial assignment (bootstrap assignments like superadmin).
        
        The subject_dn can reference a settings value via subject_dn_setting,
        which is resolved from the application config.
        """
        from heracles_api.config import settings
        
        policy_name = assignment["policy"]
        subject_type = assignment["subject_type"]
        
        # Resolve subject DN from settings if specified
        if "subject_dn_setting" in assignment:
            setting_name = assignment["subject_dn_setting"]
            subject_dn = getattr(settings, setting_name, None)
            if not subject_dn:
                logger.warning(
                    "acl_initial_assignment_skipped",
                    policy=policy_name,
                    reason=f"Setting {setting_name} not configured",
                )
                return
        else:
            subject_dn = assignment["subject_dn"]
        
        scope_dn = assignment.get("scope_dn", "")
        scope_type = assignment.get("scope_type", "subtree")
        self_only = assignment.get("self_only", False)
        deny = assignment.get("deny", False)
        priority = assignment.get("priority", 0)
        
        # Get policy ID
        policy_id = await conn.fetchval(
            "SELECT id FROM acl_policies WHERE name = $1",
            policy_name
        )
        if not policy_id:
            logger.error(
                "acl_initial_assignment_failed",
                policy=policy_name,
                reason="Policy not found",
            )
            return
        
        # Upsert assignment
        await conn.execute(
            """
            INSERT INTO acl_assignments 
                (policy_id, subject_type, subject_dn, scope_dn, scope_type, self_only, deny, priority)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (policy_id, subject_type, subject_dn, scope_dn, self_only) 
            DO UPDATE SET
                scope_type = EXCLUDED.scope_type,
                deny = EXCLUDED.deny,
                priority = EXCLUDED.priority
            """,
            policy_id,
            subject_type,
            subject_dn,
            scope_dn,
            scope_type,
            self_only,
            deny,
            priority,
        )
        
        logger.info(
            "acl_initial_assignment_created",
            policy=policy_name,
            subject_dn=subject_dn,
        )
    
    async def _calculate_bitmap(
        self,
        conn: asyncpg.Connection,
        perm_names: list[str],
    ) -> tuple[int, int]:
        """Calculate permission bitmap from permission names."""
        if not perm_names:
            return (0, 0)
        
        # Fetch bit positions for all permissions
        rows = await conn.fetch(
            """
            SELECT bit_position FROM acl_permissions
            WHERE scope || ':' || action = ANY($1)
            """,
            perm_names
        )
        
        bits = 0
        for row in rows:
            bits |= (1 << row["bit_position"])
        
        low = bits & ((1 << 64) - 1)
        high = bits >> 64
        
        # Convert to signed i64 for PostgreSQL BIGINT
        if low >= (1 << 63):
            low -= (1 << 64)
        if high >= (1 << 63):
            high -= (1 << 64)
        
        return (low, high)
    
    async def _rebuild_lookups(self, db: asyncpg.Pool) -> None:
        """Rebuild in-memory lookups from database."""
        async with db.acquire() as conn:
            # Load permissions
            rows = await conn.fetch(
                "SELECT bit_position, scope, action FROM acl_permissions"
            )
            self._by_name.clear()
            self._by_bit.clear()
            for row in rows:
                name = f"{row['scope']}:{row['action']}"
                bit = row["bit_position"]
                self._by_name[name] = bit
                self._by_bit[bit] = name
            
            # Load attribute groups
            rows = await conn.fetch(
                "SELECT object_type, group_name, attributes FROM acl_attribute_groups"
            )
            self._attr_groups.clear()
            for row in rows:
                key = (row["object_type"], row["group_name"])
                self._attr_groups[key] = list(row["attributes"])
    
    def bitmap(self, *permissions: str) -> tuple[int, int]:
        """
        Convert permission names to bitmap halves.
        
        Args:
            permissions: Permission names like "user:read", "user:write"
            
        Returns:
            Tuple of (perm_low, perm_high) suitable for Rust ACL check.
            
        Raises:
            KeyError: If a permission name is not registered.
        """
        bits = 0
        for perm in permissions:
            if perm not in self._by_name:
                raise KeyError(f"Unknown permission: {perm}")
            bits |= (1 << self._by_name[perm])
        
        low = bits & ((1 << 64) - 1)
        high = bits >> 64
        
        # Convert to signed i64 for compatibility
        if low >= (1 << 63):
            low -= (1 << 64)
        if high >= (1 << 63):
            high -= (1 << 64)
        
        return (low, high)
    
    def bitmap_safe(self, *permissions: str) -> tuple[int, int]:
        """
        Like bitmap(), but returns empty bitmap for unknown permissions
        instead of raising KeyError.
        """
        bits = 0
        for perm in permissions:
            if perm in self._by_name:
                bits |= (1 << self._by_name[perm])
        
        low = bits & ((1 << 64) - 1)
        high = bits >> 64
        
        if low >= (1 << 63):
            low -= (1 << 64)
        if high >= (1 << 63):
            high -= (1 << 64)
        
        return (low, high)
    
    def resolve_attr_groups(
        self,
        object_type: str,
        group_names: list[str],
    ) -> set[str]:
        """
        Expand attribute group names into actual LDAP attribute names.
        
        Args:
            object_type: Object type (e.g., "user", "group")
            group_names: List of group names (e.g., ["identity", "contact"])
            
        Returns:
            Set of LDAP attribute names.
        """
        attrs = set()
        for group_name in group_names:
            key = (object_type, group_name)
            if key in self._attr_groups:
                attrs.update(self._attr_groups[key])
        return attrs
    
    def name(self, bit_position: int) -> str:
        """
        Reverse lookup: bit position → 'scope:action'.
        
        Args:
            bit_position: The bit position to look up.
            
        Returns:
            Permission name like "user:read".
            
        Raises:
            KeyError: If bit position is not registered.
        """
        if bit_position not in self._by_bit:
            raise KeyError(f"Unknown bit position: {bit_position}")
        return self._by_bit[bit_position]
    
    def all_permissions(self) -> dict[str, int]:
        """Get all registered permissions as {name: bit_position}."""
        return self._by_name.copy()
    
    def all_attr_groups(self) -> dict[tuple[str, str], list[str]]:
        """Get all registered attribute groups."""
        return {k: list(v) for k, v in self._attr_groups.items()}
    
    def is_loaded(self) -> bool:
        """Check if registry has been loaded."""
        return len(self._by_name) > 0
