"""
Database Connection
===================

PostgreSQL connection pool management using asyncpg.
"""

from typing import Optional
import asyncpg
import structlog

from heracles_api.config import settings

logger = structlog.get_logger(__name__)

# Global connection pool
_db_pool: Optional[asyncpg.Pool] = None


async def init_database() -> asyncpg.Pool:
    """
    Initialize the PostgreSQL connection pool.
    
    Returns:
        asyncpg.Pool: The database connection pool
    """
    global _db_pool
    
    if _db_pool is not None:
        return _db_pool
    
    # Parse DATABASE_URL (postgresql+asyncpg://user:pass@host:port/dbname)
    db_url = settings.DATABASE_URL
    
    # Remove the +asyncpg part if present (asyncpg doesn't need it)
    if "+asyncpg" in db_url:
        db_url = db_url.replace("+asyncpg", "")
    
    try:
        _db_pool = await asyncpg.create_pool(
            db_url,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )
        logger.info("database_pool_initialized")
        return _db_pool
    except Exception as e:
        logger.error("database_pool_init_failed", error=str(e))
        raise


async def close_database() -> None:
    """Close the database connection pool."""
    global _db_pool
    
    if _db_pool is not None:
        await _db_pool.close()
        _db_pool = None
        logger.info("database_pool_closed")


def get_database() -> asyncpg.Pool:
    """
    Get the database connection pool.
    
    Returns:
        asyncpg.Pool: The database connection pool
        
    Raises:
        RuntimeError: If the pool is not initialized
    """
    if _db_pool is None:
        raise RuntimeError("Database pool not initialized")
    return _db_pool
