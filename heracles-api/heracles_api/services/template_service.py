"""
Template Service
=================

Business logic for user templates.
"""

import re
import uuid
from typing import Any, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from heracles_api.repositories.template_repository import TemplateRepository
from heracles_api.schemas.template import (
    TemplateCreate,
    TemplateListResponse,
    TemplatePreview,
    TemplateResponse,
    TemplateUpdate,
)

logger = structlog.get_logger(__name__)

# Regex for {{variable}} placeholders
_VAR_PATTERN = re.compile(r"\{\{(\w+)\}\}")


def _resolve_variables(
    defaults: dict[str, Any],
    values: dict[str, str],
) -> tuple[dict[str, Any], list[str]]:
    """
    Resolve ``{{variable}}`` placeholders in template defaults.

    Returns (resolved_defaults, missing_variable_names).
    """
    resolved: dict[str, Any] = {}
    missing: set[str] = set()

    for key, val in defaults.items():
        if isinstance(val, str):
            found_vars = _VAR_PATTERN.findall(val)
            new_val = val
            for var in found_vars:
                if var in values:
                    new_val = new_val.replace(f"{{{{{var}}}}}", values[var])
                else:
                    missing.add(var)
            resolved[key] = new_val
        elif isinstance(val, list):
            resolved[key] = [
                _resolve_str(item, values, missing) if isinstance(item, str) else item
                for item in val
            ]
        else:
            resolved[key] = val

    return resolved, sorted(missing)


def _resolve_str(s: str, values: dict[str, str], missing: set[str]) -> str:
    """Resolve variables inside a single string."""
    for var in _VAR_PATTERN.findall(s):
        if var in values:
            s = s.replace(f"{{{{{var}}}}}", values[var])
        else:
            missing.add(var)
    return s


class TemplateService:
    """Service for managing user templates."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def create_template(
        self,
        data: TemplateCreate,
        created_by: Optional[str] = None,
    ) -> TemplateResponse:
        """Create a new template."""
        async with self._session_factory() as session:
            repo = TemplateRepository(session)

            existing = await repo.get_by_name(data.name)
            if existing:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Template '{data.name}' already exists",
                )

            tmpl = await repo.create(
                name=data.name,
                description=data.description,
                defaults=data.defaults,
                variables=data.variables,
                plugin_activations=data.pluginActivations,
                department_dn=data.departmentDn,
                display_order=data.displayOrder or 0,
                created_by=created_by,
            )
            await session.commit()
            await session.refresh(tmpl)
            return TemplateResponse.model_validate(tmpl)

    async def get_template(self, template_id: uuid.UUID) -> Optional[TemplateResponse]:
        """Get a single template by ID."""
        async with self._session_factory() as session:
            repo = TemplateRepository(session)
            tmpl = await repo.get_by_id(template_id)
            if not tmpl:
                return None
            return TemplateResponse.model_validate(tmpl)

    async def list_templates(
        self,
        department_dn: Optional[str] = None,
    ) -> TemplateListResponse:
        """List all templates."""
        async with self._session_factory() as session:
            repo = TemplateRepository(session)
            templates, total = await repo.list_all(department_dn=department_dn)
            return TemplateListResponse(
                templates=[TemplateResponse.model_validate(t) for t in templates],
                total=total,
            )

    async def update_template(
        self,
        template_id: uuid.UUID,
        data: TemplateUpdate,
    ) -> Optional[TemplateResponse]:
        """Update an existing template."""
        async with self._session_factory() as session:
            repo = TemplateRepository(session)

            # Check name uniqueness if being changed
            if data.name:
                existing = await repo.get_by_name(data.name)
                if existing and existing.id != template_id:
                    from fastapi import HTTPException, status

                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Template '{data.name}' already exists",
                    )

            updates = data.model_dump(exclude_none=True, by_alias=False)
            # Map camelCase schema fields to snake_case model columns
            field_map = {
                "departmentDn": "department_dn",
                "displayOrder": "display_order",
                "pluginActivations": "plugin_activations",
            }
            mapped = {field_map.get(k, k): v for k, v in updates.items()}

            tmpl = await repo.update(template_id, **mapped)
            if not tmpl:
                return None
            await session.commit()
            await session.refresh(tmpl)
            return TemplateResponse.model_validate(tmpl)

    async def delete_template(self, template_id: uuid.UUID) -> bool:
        """Delete a template."""
        async with self._session_factory() as session:
            repo = TemplateRepository(session)
            deleted = await repo.delete(template_id)
            if deleted:
                await session.commit()
            return deleted

    async def preview_template(
        self,
        template_id: uuid.UUID,
        values: dict[str, str],
    ) -> Optional[TemplatePreview]:
        """
        Preview a template with given variable values.

        Returns resolved defaults and any missing variables.
        """
        async with self._session_factory() as session:
            repo = TemplateRepository(session)
            tmpl = await repo.get_by_id(template_id)
            if not tmpl:
                return None

            resolved, missing = _resolve_variables(tmpl.defaults, values)
            return TemplatePreview(
                template_id=tmpl.id,
                template_name=tmpl.name,
                resolved_defaults=resolved,
                missing_variables=missing,
            )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_template_service: Optional[TemplateService] = None


def init_template_service(
    session_factory: async_sessionmaker[AsyncSession],
) -> TemplateService:
    """Initialize the global template service."""
    global _template_service
    _template_service = TemplateService(session_factory)
    return _template_service


def get_template_service() -> TemplateService:
    """Get the global template service instance."""
    if _template_service is None:
        raise RuntimeError("Template service not initialized")
    return _template_service
