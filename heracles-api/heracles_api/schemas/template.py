# ruff: noqa: N815
"""
Template Pydantic Schemas
==========================

Request/response models for user templates.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------


class TemplateCreate(BaseModel):
    """Create a new user template."""

    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = None
    defaults: dict[str, Any] = Field(default_factory=dict)
    variables: dict[str, Any] | None = None
    pluginActivations: dict[str, Any] | None = Field(None, alias="plugin_activations")
    departmentDn: str | None = Field(None, alias="department_dn")
    displayOrder: int = Field(0, alias="display_order")

    class Config:
        populate_by_name = True


class TemplateUpdate(BaseModel):
    """Update an existing template."""

    name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = None
    defaults: dict[str, Any] | None = None
    variables: dict[str, Any] | None = None
    pluginActivations: dict[str, Any] | None = Field(None, alias="plugin_activations")
    departmentDn: str | None = Field(None, alias="department_dn")
    displayOrder: int | None = Field(None, alias="display_order")

    class Config:
        populate_by_name = True


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------


class TemplateResponse(BaseModel):
    """Single template response."""

    id: uuid.UUID
    name: str
    description: str | None = None
    defaults: dict[str, Any]
    variables: dict[str, Any] | None = None
    pluginActivations: dict[str, Any] | None = Field(None, alias="plugin_activations")
    departmentDn: str | None = Field(None, alias="department_dn")
    displayOrder: int = Field(0, alias="display_order")
    createdBy: str | None = Field(None, alias="created_by")
    createdAt: datetime = Field(alias="created_at")
    updatedAt: datetime = Field(alias="updated_at")

    class Config:
        from_attributes = True
        populate_by_name = True


class TemplateListResponse(BaseModel):
    """List of templates."""

    templates: list[TemplateResponse]
    total: int


class TemplatePreview(BaseModel):
    """Preview of a template applied with specific values."""

    templateId: uuid.UUID = Field(alias="template_id")
    templateName: str = Field(alias="template_name")
    resolvedDefaults: dict[str, Any] = Field(alias="resolved_defaults")
    missingVariables: list[str] = Field(default_factory=list, alias="missing_variables")

    class Config:
        populate_by_name = True
