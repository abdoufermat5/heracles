"""
Heracles API v1 Router
======================

Main router for API v1 endpoints.
"""

from fastapi import APIRouter

from heracles_api.api.v1.endpoints import auth, users, groups

router = APIRouter()

# Include endpoint routers
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(users.router, prefix="/users", tags=["Users"])
router.include_router(groups.router, prefix="/groups", tags=["Groups"])
