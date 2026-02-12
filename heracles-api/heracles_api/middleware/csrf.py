"""
CSRF Protection Middleware
==========================

Implements double-submit cookie protection for unsafe methods.
"""

from datetime import datetime, timedelta

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = structlog.get_logger(__name__)

_cache_value: bool | None = None
_cache_time: datetime | None = None
_CACHE_TTL = 30

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Auth endpoints are excluded from CSRF: login is credential-based,
# refresh uses a single-use token on a restricted cookie path.
_CSRF_EXEMPT_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
}


class CsrfMiddleware(BaseHTTPMiddleware):
    """Require X-CSRF-Token header for unsafe methods when auth cookies present."""

    async def _csrf_enabled(self) -> bool:
        global _cache_value, _cache_time
        if _cache_time and datetime.now() - _cache_time < timedelta(seconds=_CACHE_TTL):
            return _cache_value if _cache_value is not None else True

        try:
            from heracles_api.services.config import get_config_value

            value = await get_config_value("security", "csrf_protection", True)
            if isinstance(value, str):
                value = value.lower() in ("true", "1", "yes")
            _cache_value = bool(value)
            _cache_time = datetime.now()
            return _cache_value
        except Exception as exc:
            logger.warning("csrf_config_error_using_default", error=str(exc))
            _cache_value = True
            _cache_time = datetime.now()
            return True

    async def dispatch(self, request: Request, call_next):
        if request.method not in UNSAFE_METHODS:
            return await call_next(request)

        if not await self._csrf_enabled():
            return await call_next(request)

        # Auth endpoints are exempt (they issue the CSRF cookie)
        if request.url.path in _CSRF_EXEMPT_PATHS:
            return await call_next(request)

        access_cookie = request.cookies.get("access_token")
        refresh_cookie = request.cookies.get("refresh_token")
        if not access_cookie and not refresh_cookie:
            return await call_next(request)

        csrf_cookie = request.cookies.get("csrf_token")
        csrf_header = request.headers.get("x-csrf-token")

        if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "CSRF_INVALID",
                        "message": "CSRF token missing or invalid",
                    }
                },
            )

        return await call_next(request)
