"""
Database Migrations
===================

Run Alembic migrations programmatically on API startup.
This ensures the database schema is always up-to-date with
the SQLAlchemy models defined in heracles_api.models.
"""

import asyncio
from pathlib import Path

import structlog
from alembic.config import Config

from alembic import command
from heracles_api.config import settings

logger = structlog.get_logger(__name__)


def _get_alembic_config() -> Config:
    """Build Alembic config pointing to the project's alembic.ini."""
    # alembic.ini is at heracles-api/ root (one level above heracles_api/)
    ini_path = Path(__file__).resolve().parents[2] / "alembic.ini"
    cfg = Config(str(ini_path))

    # Override the DB URL so Alembic uses the same connection as the app
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    cfg.set_main_option("sqlalchemy.url", db_url)

    return cfg


async def run_migrations() -> None:
    """Run ``alembic upgrade head`` in a thread to avoid blocking the loop."""
    cfg = _get_alembic_config()

    def _upgrade() -> None:
        command.upgrade(cfg, "head")

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _upgrade)
    logger.info("alembic_upgrade_completed")
