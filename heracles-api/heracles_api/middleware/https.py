"""
HTTPS Enforcement Middleware
============================

Redirects HTTP requests to HTTPS when require_https is enabled.
"""

from datetime import datetime, timedelta

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse

logger = structlog.get_logger(__name__)

_cache_value: bool | None = None
_cache_time: datetime | None = None
_CACHE_TTL = 30


class HttpsRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect HTTP to HTTPS based on config."""

    async def _require_https(self) -> bool:
        global _cache_value, _cache_time
        if _cache_time and datetime.now() - _cache_time < timedelta(seconds=_CACHE_TTL):
            return _cache_value if _cache_value is not None else True

        try:
            from heracles_api.services.config import get_config_value

            value = await get_config_value("security", "require_https", True)
            if isinstance(value, str):
                value = value.lower() in ("true", "1", "yes")
            _cache_value = bool(value)
            _cache_time = datetime.now()
            return _cache_value
        except Exception as exc:
            logger.warning("https_config_error_using_default", error=str(exc))
            _cache_value = True
            _cache_time = datetime.now()
            return True

    # Paths that should never be redirected (internal health checks)
    _SKIP_PATHS = {"/api/health", "/api/v1/health"}

    async def dispatch(self, request: Request, call_next):
        if not await self._require_https():
            return await call_next(request)

        # Always allow health / readiness probes over plain HTTP
        if request.url.path in self._SKIP_PATHS:
            return await call_next(request)

        # If there is no X-Forwarded-Proto header the request did not
        # traverse the reverse-proxy, i.e. it is an internal / container
        # request → allow plain HTTP.
        forwarded_proto = request.headers.get("x-forwarded-proto")
        if forwarded_proto is None:
            return await call_next(request)

        if forwarded_proto == "https":
            return await call_next(request)

        host = request.headers.get("host", "")
        location = f"https://{host}{request.url.path}"
        if request.url.query:
            location = f"{location}?{request.url.query}"
        return RedirectResponse(url=location, status_code=301)
