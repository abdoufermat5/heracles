"""
Database Seed
=============

Load default configuration categories and settings from a JSON file
into PostgreSQL. Idempotent — existing rows are skipped (ON CONFLICT).

Usage inside container::

    python -m heracles_api.core.seed            # uses default path
    python -m heracles_api.core.seed /path.json  # custom path

Called automatically by ``make seed``.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from heracles_api.config import settings

logger = structlog.get_logger(__name__)

# Default location — inside the mounted /app volume
DEFAULT_SEED_PATH = Path(__file__).resolve().parents[2] / "seed-config.json"


async def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Create a standalone async session factory for seeding."""
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url, pool_size=2, pool_pre_ping=True)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def seed_config(seed_path: Path | None = None) -> dict[str, int]:
    """Seed configuration categories and settings from JSON.

    Args:
        seed_path: Path to the JSON seed file.
                   Defaults to ``heracles-api/seed-config.json``.

    Returns:
        Dict with counts: ``{"categories": N, "settings": M}``.
    """
    path = seed_path or DEFAULT_SEED_PATH
    if not path.exists():
        logger.error("seed_file_not_found", path=str(path))
        raise FileNotFoundError(f"Seed file not found: {path}")

    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    categories = data.get("categories", [])

    factory = await _get_session_factory()
    cat_count = 0
    setting_count = 0

    async with factory() as session:
        for cat_data in categories:
            cat_name = cat_data["name"]

            # --- Upsert category ------------------------------------------
            row = (
                await session.execute(
                    text(
                        "INSERT INTO config_categories "
                        "(name, label, description, icon, display_order) "
                        "VALUES (:name, :label, :desc, :icon, :ord) "
                        "ON CONFLICT (name) DO NOTHING "
                        "RETURNING id"
                    ),
                    {
                        "name": cat_name,
                        "label": cat_data["label"],
                        "desc": cat_data.get("description"),
                        "icon": cat_data.get("icon"),
                        "ord": cat_data.get("display_order", 0),
                    },
                )
            ).fetchone()

            if row is not None:
                cat_id = row[0]
                cat_count += 1
                logger.info("seed_category_created", category=cat_name)
            else:
                # Already exists — fetch its id
                cat_id = (
                    await session.execute(
                        text(
                            "SELECT id FROM config_categories WHERE name = :name"
                        ),
                        {"name": cat_name},
                    )
                ).scalar_one()
                logger.debug("seed_category_exists", category=cat_name)

            # --- Upsert settings ------------------------------------------
            for s in cat_data.get("settings", []):
                inserted = (
                    await session.execute(
                        text(
                            "INSERT INTO config_settings "
                            "(category_id, key, value, default_value, label, "
                            " description, data_type, validation_rules, options, "
                            " section, display_order) "
                            "VALUES (:cat_id, :key, :value, :default_value, :label, "
                            " :description, :data_type, :validation_rules, :options, "
                            " :section, :display_order) "
                            "ON CONFLICT (category_id, key) DO NOTHING "
                            "RETURNING id"
                        ),
                        {
                            "cat_id": cat_id,
                            "key": s["key"],
                            "value": json.dumps(s["value"]),
                            "default_value": json.dumps(s.get("default_value"))
                            if s.get("default_value") is not None
                            else None,
                            "label": s["label"],
                            "description": s.get("description"),
                            "data_type": s["data_type"],
                            "validation_rules": json.dumps(s["validation_rules"])
                            if s.get("validation_rules")
                            else None,
                            "options": json.dumps(s["options"])
                            if s.get("options")
                            else None,
                            "section": s.get("section"),
                            "display_order": s.get("display_order", 0),
                        },
                    )
                ).fetchone()

                if inserted is not None:
                    setting_count += 1

        await session.commit()

    result = {"categories": cat_count, "settings": setting_count}
    logger.info("seed_completed", **result)
    return result


# ---------------------------------------------------------------------------
# CLI entry-point: python -m heracles_api.core.seed [path]
# ---------------------------------------------------------------------------

def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    result = asyncio.run(seed_config(path))
    total = result["categories"] + result["settings"]
    if total:
        print(f"✅ Seeded {result['categories']} categories, {result['settings']} settings")
    else:
        print("ℹ️  Database already seeded — no changes")


if __name__ == "__main__":
    main()
