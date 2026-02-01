"""
Plugin Access Middleware
========================

Middleware to block access to disabled plugins.
"""

import re
from typing import Dict, Optional, Set

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import structlog

logger = structlog.get_logger(__name__)


# Mapping of URL prefixes to plugin names
PLUGIN_URL_MAPPING: Dict[str, str] = {
    "/api/v1/posix": "posix",
    "/api/v1/sudo": "sudo",
    "/api/v1/ssh": "ssh",
    "/api/v1/systems": "systems",
    "/api/v1/dns": "dns",
    "/api/v1/dhcp": "dhcp",
    "/api/v1/mail": "mail",
}


class PluginAccessMiddleware(BaseHTTPMiddleware):
    """
    Middleware that blocks access to disabled plugins.
    
    Checks the request path against known plugin prefixes and verifies
    the plugin is enabled in the database before allowing the request.
    """
    
    def __init__(self, app, db_pool=None):
        super().__init__(app)
        self._db_pool = db_pool
        # Cache of disabled plugins (refreshed on each request for simplicity)
        self._disabled_plugins: Set[str] = set()
    
    def set_db_pool(self, db_pool):
        """Set the database pool after initialization."""
        self._db_pool = db_pool
    
    def _get_plugin_for_path(self, path: str) -> Optional[str]:
        """
        Get the plugin name for a given request path.
        
        Args:
            path: The request URL path
            
        Returns:
            Plugin name if path matches a plugin route, None otherwise.
        """
        for prefix, plugin_name in PLUGIN_URL_MAPPING.items():
            if path.startswith(prefix):
                return plugin_name
        return None
    
    async def _is_plugin_enabled(self, plugin_name: str) -> bool:
        """
        Check if a plugin is enabled in the database.
        
        Args:
            plugin_name: Name of the plugin to check
            
        Returns:
            True if enabled, False if disabled or not found.
        """
        if self._db_pool is None:
            # No database connection, allow by default (graceful degradation)
            return True
        
        try:
            async with self._db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT enabled FROM plugin_configs WHERE plugin_name = $1",
                    plugin_name
                )
                if row is None:
                    # Plugin not in database, default to enabled
                    return True
                return row['enabled']
        except Exception as e:
            logger.warning(
                "plugin_enabled_check_failed",
                plugin=plugin_name,
                error=str(e)
            )
            # On error, allow request (graceful degradation)
            return True
    
    async def dispatch(self, request: Request, call_next):
        """Process request and block if plugin is disabled."""
        path = request.url.path
        
        # Check if this path belongs to a plugin
        plugin_name = self._get_plugin_for_path(path)
        
        if plugin_name:
            # Try to get db_pool from app state if not set directly
            db_pool = self._db_pool
            if db_pool is None and hasattr(request.app.state, 'db_pool'):
                db_pool = request.app.state.db_pool
            
            if db_pool is not None:
                # Check if plugin is enabled
                enabled = await self._is_plugin_enabled_with_pool(plugin_name, db_pool)
                
                if not enabled:
                    logger.info(
                        "plugin_access_blocked",
                        plugin=plugin_name,
                        path=path,
                        method=request.method,
                    )
                    return JSONResponse(
                        status_code=403,
                        content={
                            "detail": f"Plugin '{plugin_name}' is disabled. Enable it in Settings to access this feature."
                        }
                    )
        
        # Plugin enabled or not a plugin route, proceed
        response = await call_next(request)
        return response
    
    async def _is_plugin_enabled_with_pool(self, plugin_name: str, db_pool) -> bool:
        """
        Check if a plugin is enabled in the database using provided pool.
        
        Args:
            plugin_name: Name of the plugin to check
            db_pool: Database connection pool
            
        Returns:
            True if enabled, False if disabled or not found.
        """
        try:
            async with db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT enabled FROM plugin_configs WHERE plugin_name = $1",
                    plugin_name
                )
                if row is None:
                    # Plugin not in database, default to enabled
                    return True
                return row['enabled']
        except Exception as e:
            logger.warning(
                "plugin_enabled_check_failed",
                plugin=plugin_name,
                error=str(e)
            )
            # On error, allow request (graceful degradation)
            return True
