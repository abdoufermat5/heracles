"""
Stats Endpoints
===============

Returns aggregate counts for core entities.
"""

from typing import Any

from fastapi import APIRouter, Depends

from heracles_api.core.dependencies import (
    get_department_repository,
    get_group_repository,
    get_role_repository,
    get_user_repository,
)
from heracles_api.repositories import (
    DepartmentRepository,
    GroupRepository,
    RoleRepository,
    UserRepository,
)

router = APIRouter()


@router.get("/stats")
async def get_stats(
    users: UserRepository = Depends(get_user_repository),
    groups: GroupRepository = Depends(get_group_repository),
    roles: RoleRepository = Depends(get_role_repository),
    departments: DepartmentRepository = Depends(get_department_repository),
) -> dict[str, Any]:
    users_result = await users.search()
    groups_result = await groups.search()
    roles_result = await roles.search()
    departments_result = await departments.search()

    return {
        "users": users_result.total,
        "groups": groups_result.total,
        "roles": roles_result.total,
        "departments": departments_result.total,
    }
