"""
Heracles API - Main Application Entry Point
============================================

This is the main FastAPI application for Heracles identity management.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from heracles_api.config import settings
from heracles_api.api.v1 import router as api_v1_router
from heracles_api.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager."""
    # Startup
    setup_logging()
    # TODO: Initialize LDAP connection pool
    # TODO: Initialize database connection
    # TODO: Initialize Redis connection
    yield
    # Shutdown
    # TODO: Cleanup connections


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
