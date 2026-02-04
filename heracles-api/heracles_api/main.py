"""
Heracles API - Main Application Entry Point
============================================

This is the main FastAPI application for Heracles identity management.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from heracles_api.config import settings
from heracles_api.api.v1 import router as api_v1_router
from heracles_api.core.logging import setup_logging
from heracles_api.core.database import init_database, close_database, get_database
from heracles_api.services import init_ldap_service, close_ldap_service, get_ldap_service
from heracles_api.services.config import init_config_service
from heracles_api.plugins.loader import load_enabled_plugins, unload_all_plugins
from heracles_api.middleware.rate_limit import RateLimitMiddleware
from heracles_api.middleware.plugin_access import PluginAccessMiddleware
from heracles_api import __version__

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager."""
    # Startup
    setup_logging()
    logger.info("starting_heracles_api", version=__version__)

    # Skip initialization in test mode
    if settings.TESTING:
        logger.info("testing_mode_enabled", message="Skipping LDAP and plugins initialization")
        yield
        logger.info("shutting_down_heracles_api")
        return

    # Initialize PostgreSQL connection pool
    db_pool = None
    try:
        db_pool = await init_database()
        logger.info("database_initialized")
    except Exception as e:
        logger.error("database_init_failed", error=str(e))
    
    # Initialize configuration service (requires database)
    if db_pool is not None:
        try:
            init_config_service(db_pool)
            logger.info("config_service_initialized")
            
            # Inject database pool into plugin access middleware
            for middleware in app.middleware_stack.app.__dict__.get('middleware', []):
                if hasattr(middleware, 'set_db_pool'):
                    middleware.set_db_pool(db_pool)
            # Alternative: store on app state for middleware access
            app.state.db_pool = db_pool
        except Exception as e:
            logger.warning("config_service_init_failed", error=str(e))
    else:
        logger.warning("config_service_skipped", reason="database not available")

    # Initialize LDAP connection
    try:
        await init_ldap_service()
        logger.info("ldap_service_initialized")
    except Exception as e:
        logger.error("ldap_service_init_failed", error=str(e))

    # Load plugins
    try:
        ldap_service = get_ldap_service()
        plugins_config = {
            "plugins": {
                "enabled": settings.PLUGINS_AVAILABLE,
                "config": {
                    "posix": {
                        "uid_min": settings.POSIX_UID_MIN,
                        "uid_max": settings.POSIX_UID_MAX,
                        "gid_min": settings.POSIX_GID_MIN,
                        "gid_max": settings.POSIX_GID_MAX,
                        "default_shell": settings.POSIX_DEFAULT_SHELL,
                        "default_home_base": settings.POSIX_DEFAULT_HOME_BASE,
                    }
                },
            },
        }
        loaded_plugins = load_enabled_plugins(plugins_config, ldap_service)
        logger.info("plugins_loaded", count=len(loaded_plugins))

        # Register plugin routes
        from heracles_api.plugins.registry import plugin_registry
        from heracles_api.services.config import get_config_service
        
        # Get config service if available
        try:
            config_service = get_config_service()
        except RuntimeError:
            config_service = None
        
        for plugin in loaded_plugins:
            # Register plugin with config service (in-memory and database)
            if config_service:
                config_service.register_plugin(plugin)
                # Also register in database for persistence
                try:
                    await config_service.register_plugin_config(plugin)
                except Exception as e:
                    logger.warning(
                        "plugin_db_registration_failed",
                        plugin=plugin.info().name,
                        error=str(e),
                    )
            
            for route in plugin.routes():
                app.include_router(route, prefix="/api/v1")

    except Exception as e:
        logger.warning("plugins_load_failed", error=str(e))

    yield

    # Shutdown
    logger.info("shutting_down_heracles_api")
    unload_all_plugins()
    await close_ldap_service()
    await close_database()


app = FastAPI(
    title="Heracles API",
    description="Modern LDAP Identity Management API",
    version=__version__,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware (reads config from database)
# Note: Redis client is injected dynamically when available
app.add_middleware(RateLimitMiddleware)

# Plugin access middleware (blocks requests to disabled plugins)
# Note: Database pool is injected in lifespan after init
_plugin_access_middleware = PluginAccessMiddleware(app)
app.add_middleware(PluginAccessMiddleware)

# Include API routers
app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": __version__,
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Heracles API",
        "version": __version__,
        "docs": "/api/docs" if settings.DEBUG else None,
    }
