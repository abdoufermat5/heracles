"""
Plugin Access Middleware
========================

Middleware to block access to disabled plugins.
"""

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from heracles_api.models.config import PluginConfig

logger = structlog.get_logger(__name__)


# Mapping of URL prefixes to plugin names
PLUGIN_URL_MAPPING: dict[str, str] = {
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

    def __init__(self, app):
        super().__init__(app)

    def _get_plugin_for_path(self, path: str) -> str | None:
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

    async def _is_plugin_enabled(
        self,
        plugin_name: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> bool:
        """
        Check if a plugin is enabled in the database.

        Args:
            plugin_name: Name of the plugin to check
            session_factory: SQLAlchemy async session factory

        Returns:
            True if enabled, False if disabled or not found.
        """
        try:
            async with session_factory() as session:
                stmt = select(PluginConfig.enabled).where(PluginConfig.plugin_name == plugin_name)
                result = await session.execute(stmt)
                enabled = result.scalar_one_or_none()
                if enabled is None:
                    # Plugin not in database, default to enabled
                    return True
                return enabled
        except Exception as e:
            logger.warning(
                "plugin_enabled_check_failed",
                plugin=plugin_name,
                error=str(e),
            )
            # On error, allow request (graceful degradation)
            return True

    async def dispatch(self, request: Request, call_next):
        """Process request and block if plugin is disabled."""
        path = request.url.path

        # Check if this path belongs to a plugin
        plugin_name = self._get_plugin_for_path(path)

        if plugin_name:
            # Get session_factory from app state (set during lifespan)
            session_factory: async_sessionmaker | None = getattr(request.app.state, "session_factory", None)

            if session_factory is not None:
                enabled = await self._is_plugin_enabled(plugin_name, session_factory)

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
                            "detail": f"Plugin '{plugin_name}' is disabled. "
                            "Enable it in Settings to access this feature.",
                        },
                    )

        # Plugin enabled or not a plugin route, proceed
        response = await call_next(request)
        return response
