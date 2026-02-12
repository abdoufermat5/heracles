"""
Permission Registry
===================

Loads ACL definitions from JSON files, syncs to PostgreSQL,
and provides runtime lookups. No hardcoded constants.

Bit positions are assigned by the database (auto-increment on first insert)
and are stable across restarts.
"""

import json
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from heracles_api.repositories.acl_repository import AclRepository

logger = structlog.get_logger(__name__)


class PermissionRegistry:
    """
    Central registry for ACL permissions and attribute groups.

    Loads definitions from JSON files (core + plugins), syncs to PostgreSQL,
    and provides efficient runtime lookups for permission name -> bit position.

    Usage:
        registry = PermissionRegistry()
        await registry.load(plugins=[...])

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
        # Policy names that used "*" wildcard (need recompile after all plugins load)
        self._wildcard_policies: set[str] = set()

    async def load(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        plugins: list[Any] | None = None,
    ) -> None:
        """
        Load ACL definitions from JSON files and sync to PostgreSQL.

        1. Load core_acl.json
        2. For each enabled plugin, load its acl.json (if exists)
        3. Upsert permissions (assign bit positions if new)
        4. Upsert attribute groups
        5. Upsert built-in policies
        6. Build in-memory lookups from database
        """
        plugins = plugins or []

        # Load core definitions
        core_path = Path(__file__).parent / "core_acl.json"
        if core_path.exists():
            await self._load_json_file(session_factory, core_path, plugin_name=None)
        else:
            logger.warning("core_acl_not_found", path=str(core_path))

        # Load plugin definitions
        for plugin in plugins:
            acl_file = getattr(plugin, "acl_file", None)
            if callable(acl_file):
                path = acl_file()
                if path and path.exists():
                    info = plugin.info()
                    await self._load_json_file(session_factory, path, plugin_name=info.name)

        # Recompile wildcard policies now that ALL permissions are registered
        if self._wildcard_policies:
            await self._recompile_wildcard_policies(session_factory)

        # Rebuild in-memory lookups from database
        await self._rebuild_lookups(session_factory)

        logger.info(
            "acl_registry_loaded",
            permissions=len(self._by_name),
            attr_groups=len(self._attr_groups),
            sources=self._loaded_sources,
        )

    async def _load_json_file(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        path: Path,
        plugin_name: str | None,
    ) -> None:
        """Load a single ACL JSON file and sync to database."""
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception as e:
            logger.error("acl_json_load_failed", path=str(path), error=str(e))
            return

        source = plugin_name or "core"
        self._loaded_sources.append(source)

        async with session_factory() as session:
            repo = AclRepository(session)

            # Sync permissions
            for perm in data.get("permissions", []):
                result = await repo.upsert_permission(
                    scope=perm["scope"],
                    action=perm["action"],
                    description=perm["description"],
                    plugin=plugin_name,
                )
                if result is not None:
                    logger.debug(
                        "acl_permission_created",
                        scope=perm["scope"],
                        action=perm["action"],
                        bit=result,
                    )

            # Sync attribute groups
            for group in data.get("attribute_groups", []):
                await repo.upsert_attribute_group(
                    object_type=group["object_type"],
                    group_name=group["group_name"],
                    label=group["label"],
                    attributes=group["attributes"],
                    plugin=plugin_name,
                )

            # Sync built-in policies
            for policy in data.get("policies", []):
                if policy.get("builtin", False):
                    await self._upsert_policy(repo, policy, plugin_name)

            # Sync initial assignments (only from core, not plugins)
            if plugin_name is None:
                for assignment in data.get("initial_assignments", []):
                    await self._upsert_initial_assignment(repo, assignment)

            await session.commit()

    async def _upsert_policy(
        self,
        repo: AclRepository,
        policy: dict,
        plugin: str | None,
    ) -> None:
        """Upsert a built-in policy with its permission bitmap."""
        name = policy["name"]
        description = policy.get("description", "")
        perm_names = policy.get("permissions", [])

        # Handle wildcard "*" - grant all registered permissions
        if perm_names == "*":
            self._wildcard_policies.add(name)
            perm_names = await repo.get_all_permission_names()

        # Calculate bitmap from permission names
        perm_low, perm_high = await self._calculate_bitmap(repo, perm_names)

        # Upsert policy
        policy_id = await repo.upsert_builtin_policy(
            name=name,
            description=description,
            perm_low=perm_low,
            perm_high=perm_high,
        )

        # Delete existing attr rules and re-insert
        await repo.delete_all_attr_rules_for_policy(policy_id)

        for rule in policy.get("attr_rules", []):
            await repo.create_attr_rule(
                policy_id=policy_id,
                object_type=rule["object_type"],
                action=rule["action"],
                rule_type=rule["rule_type"],
                attr_groups=rule["attr_groups"],
            )

    async def _upsert_initial_assignment(
        self,
        repo: AclRepository,
        assignment: dict,
    ) -> None:
        """Upsert an initial assignment (bootstrap assignments like superadmin)."""
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
        policy = await repo.get_policy_by_name(policy_name)
        if not policy:
            logger.error(
                "acl_initial_assignment_failed",
                policy=policy_name,
                reason="Policy not found",
            )
            return

        # Upsert assignment (mark as builtin so it cannot be deleted via API)
        await repo.upsert_builtin_assignment(
            policy_id=policy.id,
            subject_type=subject_type,
            subject_dn=subject_dn,
            scope_dn=scope_dn,
            scope_type=scope_type,
            self_only=self_only,
            deny=deny,
            priority=priority,
        )

        logger.info(
            "acl_initial_assignment_created",
            policy=policy_name,
            subject_dn=subject_dn,
        )

    async def _recompile_wildcard_policies(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Recompile bitmaps for policies that used the "*" wildcard."""
        async with session_factory() as session:
            repo = AclRepository(session)

            all_perm_names = await repo.get_all_permission_names()
            if not all_perm_names:
                return

            perm_low, perm_high = await self._calculate_bitmap(repo, all_perm_names)

            for policy_name in self._wildcard_policies:
                await repo.update_wildcard_policy_bitmap(policy_name, perm_low, perm_high)
                logger.info(
                    "acl_wildcard_policy_recompiled",
                    policy=policy_name,
                    total_permissions=len(all_perm_names),
                )

            await session.commit()

    async def _calculate_bitmap(
        self,
        repo: AclRepository,
        perm_names: list[str],
    ) -> tuple[int, int]:
        """Calculate permission bitmap from permission names."""
        if not perm_names:
            return (0, 0)

        bit_positions = await repo.get_bit_positions_for_names(perm_names)

        bits = 0
        for bit in bit_positions:
            bits |= 1 << bit

        low = bits & ((1 << 64) - 1)
        high = bits >> 64

        # Convert to signed i64 for PostgreSQL BIGINT
        if low >= (1 << 63):
            low -= 1 << 64
        if high >= (1 << 63):
            high -= 1 << 64

        return (low, high)

    async def _rebuild_lookups(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Rebuild in-memory lookups from database."""
        async with session_factory() as session:
            repo = AclRepository(session)

            # Load permissions
            self._by_name, self._by_bit = await repo.get_all_permission_lookups()

            # Load attribute groups
            self._attr_groups = await repo.get_all_attr_group_lookups()

    def bitmap(self, *permissions: str) -> tuple[int, int]:
        """
        Convert permission names to bitmap halves.

        Returns:
            Tuple of (perm_low, perm_high) suitable for Rust ACL check.

        Raises:
            KeyError: If a permission name is not registered.
        """
        bits = 0
        for perm in permissions:
            if perm not in self._by_name:
                raise KeyError(f"Unknown permission: {perm}")
            bits |= 1 << self._by_name[perm]

        low = bits & ((1 << 64) - 1)
        high = bits >> 64

        # Convert to signed i64 for compatibility
        if low >= (1 << 63):
            low -= 1 << 64
        if high >= (1 << 63):
            high -= 1 << 64

        return (low, high)

    def bitmap_safe(self, *permissions: str) -> tuple[int, int]:
        """
        Like bitmap(), but returns empty bitmap for unknown permissions
        instead of raising KeyError.
        """
        bits = 0
        for perm in permissions:
            if perm in self._by_name:
                bits |= 1 << self._by_name[perm]

        low = bits & ((1 << 64) - 1)
        high = bits >> 64

        if low >= (1 << 63):
            low -= 1 << 64
        if high >= (1 << 63):
            high -= 1 << 64

        return (low, high)

    def resolve_attr_groups(
        self,
        object_type: str,
        group_names: list[str],
    ) -> set[str]:
        """Expand attribute group names into actual LDAP attribute names."""
        attrs = set()
        for group_name in group_names:
            key = (object_type, group_name)
            if key in self._attr_groups:
                attrs.update(self._attr_groups[key])
        return attrs

    def name(self, bit_position: int) -> str:
        """Reverse lookup: bit position -> 'scope:action'."""
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
