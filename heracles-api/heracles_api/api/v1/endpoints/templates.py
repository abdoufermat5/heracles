"""
Templates API Endpoint
=======================

CRUD operations for user creation templates.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from heracles_api.schemas.template import (
    TemplateCreate,
    TemplateListResponse,
    TemplatePreview,
    TemplateResponse,
    TemplateUpdate,
)
from heracles_api.services.template_service import get_template_service

router = APIRouter(prefix="/templates", tags=["Templates"])


@router.get("/plugin-fields")
async def get_plugin_fields(
    object_type: str = Query("user", description="Object type to get plugin fields for"),
) -> dict:
    """
    Return template-configurable plugin fields grouped by plugin name.

    Used by the template editor UI to render plugin activation toggles
    and their configurable defaults.
    """
    from heracles_api.plugins.registry import plugin_registry

    return plugin_registry.get_template_fields_for_type(object_type)


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    department_dn: Optional[str] = Query(
        None, alias="departmentDn", description="Filter by department DN"
    ),
) -> TemplateListResponse:
    """List all user templates."""
    svc = get_template_service()
    return await svc.list_templates(department_dn=department_dn)


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(body: TemplateCreate) -> TemplateResponse:
    """Create a new user template."""
    svc = get_template_service()
    return await svc.create_template(body)


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: uuid.UUID) -> TemplateResponse:
    """Get a single template by ID."""
    svc = get_template_service()
    result = await svc.get_template(template_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return result


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: uuid.UUID,
    body: TemplateUpdate,
) -> TemplateResponse:
    """Update an existing template."""
    svc = get_template_service()
    result = await svc.update_template(template_id, body)
    if result is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return result


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(template_id: uuid.UUID) -> None:
    """Delete a template."""
    svc = get_template_service()
    deleted = await svc.delete_template(template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Template not found")


@router.post("/{template_id}/preview", response_model=TemplatePreview)
async def preview_template(
    template_id: uuid.UUID,
    values: dict[str, str],
) -> TemplatePreview:
    """
    Preview a template with given variable values.

    Returns the resolved defaults with placeholders replaced.
    """
    svc = get_template_service()
    result = await svc.preview_template(template_id, values)
    if result is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return result
