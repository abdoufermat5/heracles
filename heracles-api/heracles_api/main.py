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
from heracles_api.services import init_ldap_service, close_ldap_service

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager."""
    # Startup
    setup_logging()
    logger.info("starting_heracles_api", version="0.1.0")
    
    # Initialize LDAP connection
    try:
        await init_ldap_service()
        logger.info("ldap_service_initialized")
    except Exception as e:
        logger.error("ldap_service_init_failed", error=str(e))
    
    yield
    
    # Shutdown
    logger.info("shutting_down_heracles_api")
    await close_ldap_service()


app = FastAPI(
    title="Heracles API",
    description="Modern LDAP Identity Management API",
    version="0.1.0",
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

# Include API routers
app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.1.0",
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Heracles API",
        "version": "0.1.0",
        "docs": "/api/docs" if settings.DEBUG else None,
    }
