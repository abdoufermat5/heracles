"""
Heracles API v1 Router
======================

Main router for API v1 endpoints.
"""

from fastapi import APIRouter

from heracles_api.api.v1.endpoints import auth, users, groups, plugins

router = APIRouter()

# Include endpoint routers
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(users.router, prefix="/users", tags=["Users"])
router.include_router(groups.router, prefix="/groups", tags=["Groups"])
router.include_router(plugins.router, tags=["Plugins"])

# Include POSIX plugin routes (loaded dynamically if plugin is enabled)
try:
    from heracles_plugins.posix.routes import router as posix_router
    router.include_router(posix_router, tags=["POSIX"])
except ImportError:
    pass  # POSIX plugin not installed

# Include Systems plugin routes
try:
    from heracles_plugins.systems.routes import router as systems_router
    router.include_router(systems_router, tags=["Systems"])
except ImportError:
    pass  # Systems plugin not installed
