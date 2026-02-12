"""
Database Connection
===================

PostgreSQL connection management using SQLAlchemy async engine.
"""

from collections.abc import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from heracles_api.config import settings

logger = structlog.get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_database() -> AsyncEngine:
    """
    Initialize the SQLAlchemy async engine and session factory.

    Returns:
        AsyncEngine: The database engine.
    """
    global _engine, _session_factory

    if _engine is not None:
        return _engine

    db_url = settings.DATABASE_URL

    # Ensure the URL uses the asyncpg driver
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif "+asyncpg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    try:
        _engine = create_async_engine(
            db_url,
            pool_size=10,
            max_overflow=0,
            pool_pre_ping=True,
            pool_timeout=60,
            echo=False,
        )
        _session_factory = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        logger.info("database_engine_initialized")
        return _engine
    except Exception as e:
        logger.error("database_engine_init_failed", error=str(e))
        raise


async def close_database() -> None:
    """Dispose of the engine and reset globals."""
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("database_engine_closed")


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get the session factory for use outside the request cycle (e.g. startup).

    Returns:
        async_sessionmaker: Session factory.

    Raises:
        RuntimeError: If the engine has not been initialized.
    """
    if _session_factory is None:
        raise RuntimeError("Database engine not initialized")
    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an AsyncSession per request.

    Commits on success, rolls back on exception.
    """
    if _session_factory is None:
        raise RuntimeError("Database engine not initialized")

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
