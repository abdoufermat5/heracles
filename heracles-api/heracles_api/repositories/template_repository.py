"""
Template Repository
====================

Database operations for the user_templates table.
"""

import uuid
from typing import Any, Optional

import structlog
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from heracles_api.models.template import UserTemplate

logger = structlog.get_logger(__name__)


class TemplateRepository:
    """Repository for user template CRUD operations."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        *,
        name: str,
        description: Optional[str] = None,
        defaults: dict[str, Any],
        variables: Optional[dict[str, Any]] = None,
        plugin_activations: Optional[dict[str, Any]] = None,
        department_dn: Optional[str] = None,
        display_order: int = 0,
        created_by: Optional[str] = None,
    ) -> UserTemplate:
        """Create a new template."""
        tmpl = UserTemplate(
            name=name,
            description=description,
            defaults=defaults,
            variables=variables,
            plugin_activations=plugin_activations,
            department_dn=department_dn,
            display_order=display_order,
            created_by=created_by,
        )
        self._session.add(tmpl)
        await self._session.flush()
        return tmpl

    async def get_by_id(self, template_id: uuid.UUID) -> Optional[UserTemplate]:
        """Fetch a template by its UUID."""
        result = await self._session.execute(
            select(UserTemplate).where(UserTemplate.id == template_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[UserTemplate]:
        """Fetch a template by name."""
        result = await self._session.execute(
            select(UserTemplate).where(UserTemplate.name == name)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        *,
        department_dn: Optional[str] = None,
    ) -> tuple[list[UserTemplate], int]:
        """List all templates, optionally filtered by department."""
        query = select(UserTemplate).order_by(
            UserTemplate.display_order, UserTemplate.name
        )
        count_query = select(func.count()).select_from(UserTemplate)

        if department_dn:
            query = query.where(UserTemplate.department_dn == department_dn)
            count_query = count_query.where(
                UserTemplate.department_dn == department_dn
            )

        total = (await self._session.execute(count_query)).scalar() or 0
        result = await self._session.execute(query)
        return list(result.scalars().all()), total

    async def update(
        self,
        template_id: uuid.UUID,
        **kwargs: Any,
    ) -> Optional[UserTemplate]:
        """Update a template. Returns the updated template or None."""
        # Filter out None values so only provided fields are updated
        updates = {k: v for k, v in kwargs.items() if v is not None}
        if not updates:
            return await self.get_by_id(template_id)

        await self._session.execute(
            update(UserTemplate)
            .where(UserTemplate.id == template_id)
            .values(**updates)
        )
        await self._session.flush()
        return await self.get_by_id(template_id)

    async def delete(self, template_id: uuid.UUID) -> bool:
        """Delete a template. Returns True if deleted."""
        result = await self._session.execute(
            delete(UserTemplate).where(UserTemplate.id == template_id)
        )
        return result.rowcount > 0
