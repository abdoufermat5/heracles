"""
Health Check Endpoints
======================

Reports health status for LDAP, PostgreSQL, and Redis.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from heracles_api.core.dependencies import get_ldap, get_redis
from heracles_api.core.database import get_db_session
from heracles_api.services import LdapService

router = APIRouter()


@router.get("/health")
async def health_check(
    ldap: LdapService = Depends(get_ldap),
    redis: Optional[Redis] = Depends(get_redis),
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    services: Dict[str, Dict[str, str]] = {}
    overall_ok = True

    # LDAP health
    try:
        await ldap.search(
            search_base=ldap.base_dn,
            search_filter="(objectClass=*)",
            scope="base",
            attributes=["dn"],
            size_limit=1,
        )
        services["ldap"] = {"status": "ok"}
    except Exception as exc:
        overall_ok = False
        services["ldap"] = {"status": "error", "message": str(exc)}

    # Redis health
    if redis is None:
        overall_ok = False
        services["redis"] = {"status": "error", "message": "Redis not configured"}
    else:
        try:
            await redis.ping()
            services["redis"] = {"status": "ok"}
        except Exception as exc:
            overall_ok = False
            services["redis"] = {"status": "error", "message": str(exc)}
        finally:
            await redis.aclose()

    # Database health
    try:
        await session.execute(text("SELECT 1"))
        services["database"] = {"status": "ok"}
    except Exception as exc:
        overall_ok = False
        services["database"] = {"status": "error", "message": str(exc)}

    return {
        "status": "ok" if overall_ok else "degraded",
        "services": services,
    }
