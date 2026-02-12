"""
ACL Middleware
==============

Loads the user's compiled ACL from Redis into request.state for
use by AclGuard in endpoints.
"""

import structlog
from typing import Callable, Optional, TYPE_CHECKING

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from heracles_core import UserAcl as PyUserAcl

logger = structlog.get_logger(__name__)


class AclMiddleware(BaseHTTPMiddleware):
    """
    Middleware that loads the user's ACL into request.state.
    
    For authenticated requests, loads the compiled UserAcl from Redis
    and makes it available as request.state.user_acl.
    
    If the user's ACL is not cached, it will be compiled on-demand
    by the AclService during the first ACL check.
    
    Usage:
        # In main.py
        app.add_middleware(AclMiddleware)
        
        # In endpoint (via AclGuardDep)
        user_acl = request.state.user_acl  # PyUserAcl or None
    """
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Load user ACL from Redis if authenticated."""
        # Initialize state
        request.state.user_acl = None
        request.state.acl_registry = None
        
        # Skip for non-authenticated endpoints
        # The actual ACL loading happens in the AclGuard dependency
        # which has access to the current user from the auth flow
        
        # Store registry reference if available on app state
        if hasattr(request.app.state, "acl_registry"):
            request.state.acl_registry = request.app.state.acl_registry
        
        return await call_next(request)


async def load_user_acl_from_redis(
    redis,
    user_dn: str,
) -> Optional["PyUserAcl"]:
    """
    Load a user's compiled ACL from Redis cache.
    
    Args:
        redis: Redis connection.
        user_dn: The user's DN.
        
    Returns:
        Deserialized PyUserAcl if cached, None if not found.
    """
    from heracles_api.acl.service import ACL_CACHE_PREFIX
    
    if redis is None:
        return None
    
    try:
        key = f"{ACL_CACHE_PREFIX}{user_dn}"
        data = await redis.get(key)
        
        if data is None:
            return None
        
        # Deserialize from cached format
        # The PyUserAcl is stored as serialized bytes by the Rust engine
        from heracles_core import deserialize_user_acl
        return deserialize_user_acl(data)
        
    except Exception as e:
        logger.warning(
            "acl_cache_load_failed",
            user_dn=user_dn,
            error=str(e),
        )
        return None
