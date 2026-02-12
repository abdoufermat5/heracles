"""
Rate Limiting Middleware
========================

Enforces API rate limits based on database configuration.
Uses Redis for distributed rate limit tracking across instances.

Configuration is read from the 'security' category:
- rate_limit_enabled: Whether rate limiting is active
- rate_limit_requests: Maximum requests per window
- rate_limit_window: Window duration in seconds
"""

import time
from typing import Callable, Optional, Dict, Any, Tuple, Iterable
from datetime import datetime, timedelta

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from redis.asyncio import Redis

import structlog

logger = structlog.get_logger(__name__)

# Default rate limit values (fallback when config unavailable)
DEFAULT_RATE_LIMIT_ENABLED = True
DEFAULT_RATE_LIMIT_REQUESTS = 100
DEFAULT_RATE_LIMIT_WINDOW = 60  # seconds

# In-memory cache for rate limit config (hot-reload friendly)
_rate_limit_cache: Dict[str, Any] = {}
_rate_limit_cache_time: Optional[datetime] = None
_CACHE_TTL = 30  # seconds - refresh config every 30 seconds


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using sliding window algorithm.
    
    Reads configuration from database and enforces rate limits
    per client IP address. Uses Redis for distributed tracking.
    
    Skips rate limiting for:
    - Health check endpoints (/health, /ready)
    - Documentation endpoints (/api/docs, /api/redoc, /api/openapi.json)
    - Websocket connections
    """
    
    # Endpoints exempt from rate limiting
    EXEMPT_PATHS = {
        "/health",
        "/ready",
        "/api/docs",
        "/api/redoc",
        "/api/openapi.json",
    }
    
    def __init__(
        self,
        app,
        redis_client: Optional[Redis] = None,
        trusted_proxies: Optional[Iterable[str]] = None,
    ):
        super().__init__(app)
        self.redis = redis_client
        self.trusted_proxies = set(trusted_proxies or [])
        # In-memory fallback for rate limiting when Redis unavailable
        self._local_counters: Dict[str, Dict[str, Any]] = {}
    
    async def _get_rate_limit_config(self) -> Tuple[bool, int, int]:
        """
        Get rate limit configuration from database with caching.
        
        Returns:
            Tuple of (enabled, max_requests, window_seconds)
        """
        global _rate_limit_cache, _rate_limit_cache_time
        
        # Check cache
        if _rate_limit_cache_time is not None:
            if datetime.now() - _rate_limit_cache_time < timedelta(seconds=_CACHE_TTL):
                return (
                    _rate_limit_cache.get("enabled", DEFAULT_RATE_LIMIT_ENABLED),
                    _rate_limit_cache.get("requests", DEFAULT_RATE_LIMIT_REQUESTS),
                    _rate_limit_cache.get("window", DEFAULT_RATE_LIMIT_WINDOW),
                )
        
        # Try to get from config service
        try:
            from heracles_api.services.config import get_config_value
            
            enabled = await get_config_value(
                "security",
                "rate_limit_enabled",
                DEFAULT_RATE_LIMIT_ENABLED,
            )
            requests = await get_config_value(
                "security",
                "rate_limit_requests",
                DEFAULT_RATE_LIMIT_REQUESTS,
            )
            window = await get_config_value(
                "security",
                "rate_limit_window",
                DEFAULT_RATE_LIMIT_WINDOW,
            )
            
            # Convert types and handle JSON strings
            if isinstance(enabled, str):
                enabled = enabled.lower() in ("true", "1", "yes")
            
            # Update cache
            _rate_limit_cache = {
                "enabled": bool(enabled),
                "requests": int(requests),
                "window": int(window),
            }
            _rate_limit_cache_time = datetime.now()
            
            return _rate_limit_cache["enabled"], _rate_limit_cache["requests"], _rate_limit_cache["window"]
            
        except Exception as e:
            logger.warning(
                "rate_limit_config_error_using_defaults",
                error=str(e),
            )
            return DEFAULT_RATE_LIMIT_ENABLED, DEFAULT_RATE_LIMIT_REQUESTS, DEFAULT_RATE_LIMIT_WINDOW
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, considering proxies."""
        # Trust X-Forwarded-For only when coming from known proxies
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for and request.client and request.client.host in self.trusted_proxies:
            return forwarded_for.split(",")[0].strip()
        
        # Fall back to direct connection IP
        if request.client:
            return request.client.host
        
        return "unknown"
    
    async def _check_rate_limit_redis(
        self,
        redis_client: Optional[Redis],
        client_ip: str,
        max_requests: int,
        window_seconds: int,
    ) -> Tuple[bool, int, int]:
        """
        Check rate limit using Redis (distributed).
        
        Returns:
            Tuple of (allowed, remaining_requests, reset_time)
        """
        if not redis_client:
            return self._check_rate_limit_local(client_ip, max_requests, window_seconds)
        
        try:
            key = f"rate_limit:{client_ip}"
            now = int(time.time())
            window_start = now - window_seconds
            
            # Use Redis sorted set with timestamp as score
            async with redis_client.pipeline(transaction=True) as pipe:
                # Remove old entries outside the window
                pipe.zremrangebyscore(key, "-inf", window_start)
                # Add current request
                pipe.zadd(key, {f"{now}:{id(self)}": now})
                # Count requests in window
                pipe.zcard(key)
                # Set expiry
                pipe.expire(key, window_seconds)
                
                results = await pipe.execute()
            
            request_count = results[2]
            remaining = max(0, max_requests - request_count)
            reset_time = now + window_seconds
            
            if request_count > max_requests:
                logger.warning(
                    "rate_limit_exceeded",
                    client_ip=client_ip,
                    request_count=request_count,
                    max_requests=max_requests,
                )
                return False, 0, reset_time
            
            return True, remaining, reset_time
            
        except Exception as e:
            logger.warning(
                "redis_rate_limit_error_falling_back_to_local",
                error=str(e),
            )
            return self._check_rate_limit_local(client_ip, max_requests, window_seconds)
    
    def _check_rate_limit_local(
        self,
        client_ip: str,
        max_requests: int,
        window_seconds: int,
    ) -> Tuple[bool, int, int]:
        """
        Check rate limit using local in-memory storage (single instance only).
        
        This is a fallback when Redis is unavailable.
        Note: This doesn't work correctly with multiple API instances.
        
        Returns:
            Tuple of (allowed, remaining_requests, reset_time)
        """
        now = time.time()
        
        if client_ip not in self._local_counters:
            self._local_counters[client_ip] = {
                "requests": [],
                "window_start": now,
            }
        
        counter = self._local_counters[client_ip]
        window_start = now - window_seconds
        
        # Remove old requests outside window
        counter["requests"] = [
            ts for ts in counter["requests"]
            if ts > window_start
        ]
        
        # Add current request
        counter["requests"].append(now)
        
        request_count = len(counter["requests"])
        remaining = max(0, max_requests - request_count)
        reset_time = int(now + window_seconds)
        
        if request_count > max_requests:
            logger.warning(
                "rate_limit_exceeded_local",
                client_ip=client_ip,
                request_count=request_count,
                max_requests=max_requests,
            )
            return False, 0, reset_time
        
        # Cleanup old clients periodically
        if len(self._local_counters) > 10000:
            self._cleanup_local_counters(window_seconds)
        
        return True, remaining, reset_time
    
    def _cleanup_local_counters(self, window_seconds: int) -> None:
        """Remove stale entries from local counter storage."""
        now = time.time()
        cutoff = now - (window_seconds * 2)
        
        stale_keys = [
            ip for ip, counter in self._local_counters.items()
            if not counter["requests"] or max(counter["requests"]) < cutoff
        ]
        
        for key in stale_keys:
            del self._local_counters[key]
        
        logger.debug("rate_limit_local_cleanup", removed=len(stale_keys))
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request with rate limiting."""
        # Skip rate limiting for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        
        # Skip for websocket upgrades
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)
        
        # Get rate limit configuration
        enabled, max_requests, window_seconds = await self._get_rate_limit_config()
        
        # Skip if rate limiting is disabled
        if not enabled:
            return await call_next(request)
        
        # Get client identifier
        client_ip = self._get_client_ip(request)
        
        # Check rate limit
        redis_client = self.redis or getattr(request.app.state, "redis", None)

        allowed, remaining, reset_time = await self._check_rate_limit_redis(
            redis_client,
            client_ip,
            max_requests,
            window_seconds,
        )
        
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please try again later.",
                    }
                },
                headers={
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time - int(time.time())),
                },
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        
        return response


def invalidate_rate_limit_cache() -> None:
    """
    Invalidate the rate limit config cache for hot-reload.
    
    Called when rate limit configuration is updated.
    """
    global _rate_limit_cache, _rate_limit_cache_time
    _rate_limit_cache = {}
    _rate_limit_cache_time = None
    logger.debug("rate_limit_cache_invalidated")
