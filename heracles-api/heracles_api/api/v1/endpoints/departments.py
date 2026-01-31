"""
Departments Endpoints
=====================

Department management endpoints (CRUD operations).
"""

from typing import Optional
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, status, Query

from heracles_api.core.dependencies import CurrentUser, DeptRepoDep
from heracles_api.schemas import (
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse,
    DepartmentListResponse,
    DepartmentTreeResponse,
)
from heracles_api.services import LdapOperationError

import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()


def _entry_to_response(entry, children_count: int = 0) -> DepartmentResponse:
    """Convert LDAP entry to DepartmentResponse."""
    from heracles_api.repositories.department_repository import DepartmentRepository

    repo = DepartmentRepository.__new__(DepartmentRepository)
    repo.base_dn = entry.dn.split(",ou=")[0] if ",ou=" in entry.dn else ""
    return DepartmentResponse(
        dn=entry.dn,
        ou=entry.get_first("ou", ""),
        description=entry.get_first("description"),
        path=repo._dn_to_path(entry.dn) if hasattr(repo, "_dn_to_path") else "",
        parentDn=repo._get_parent_dn(entry.dn) if hasattr(repo, "_get_parent_dn") else None,
        childrenCount=children_count,
        hrcDepartmentCategory=entry.get_first("hrcDepartmentCategory"),
        hrcDepartmentManager=entry.get_first("hrcDepartmentManager"),
    )


@router.get("/tree", response_model=DepartmentTreeResponse)
async def get_department_tree(
    current_user: CurrentUser,
    dept_repo: DeptRepoDep,
):
    """
    Get full department hierarchy as a tree.
    """
    try:
        tree = await dept_repo.get_tree()
        return DepartmentTreeResponse(
            tree=tree,
            total=len(tree),
        )
    except LdapOperationError as e:
        logger.error("get_department_tree_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get department tree",
        )


@router.get("", response_model=DepartmentListResponse)
async def list_departments(
    current_user: CurrentUser,
    dept_repo: DeptRepoDep,
    parent: Optional[str] = Query(None, description="Parent DN (URL-encoded) to filter direct children"),
    search: Optional[str] = Query(None, description="Search in ou, description"),
):
    """
    List departments with optional filtering.
    """
    try:
        # Decode parent DN if provided
        parent_dn = unquote(parent) if parent else None

        result = await dept_repo.search(parent_dn=parent_dn, search_term=search)

        # Get children count for each department
        departments = []
        for entry in result.departments:
            children_count = await dept_repo.get_children_count(entry.dn)
            departments.append(dept_repo._entry_to_response(entry, children_count))

        return DepartmentListResponse(
            departments=departments,
            total=result.total,
        )

    except LdapOperationError as e:
        logger.error("list_departments_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list departments",
        )


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    department: DepartmentCreate,
    current_user: CurrentUser,
    dept_repo: DeptRepoDep,
):
    """
    Create a new department.

    Also creates container OUs (ou=people, ou=groups, etc.) inside the department.
    """
    try:
        entry = await dept_repo.create(department)

        if not entry:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create department",
            )

        logger.info(
            "department_created",
            ou=department.ou,
            parent_dn=department.parent_dn,
            by=current_user.uid,
        )

        return dept_repo._entry_to_response(entry, 0)

    except LdapOperationError as e:
        error_msg = str(e)
        logger.error("create_department_failed", ou=department.ou, error=error_msg)

        if "already exists" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Department '{department.ou}' already exists",
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create department: {e}",
        )


@router.get("/{dn:path}", response_model=DepartmentResponse)
async def get_department(
    dn: str,
    current_user: CurrentUser,
    dept_repo: DeptRepoDep,
):
    """
    Get department by DN.

    The DN should be URL-encoded.
    """
    try:
        # Decode DN
        decoded_dn = unquote(dn)

        entry = await dept_repo.find_by_dn(decoded_dn)

        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Department not found: {decoded_dn}",
            )

        children_count = await dept_repo.get_children_count(decoded_dn)
        return dept_repo._entry_to_response(entry, children_count)

    except LdapOperationError as e:
        logger.error("get_department_failed", dn=dn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get department",
        )


@router.patch("/{dn:path}", response_model=DepartmentResponse)
async def update_department(
    dn: str,
    updates: DepartmentUpdate,
    current_user: CurrentUser,
    dept_repo: DeptRepoDep,
):
    """
    Update department attributes.
    """
    try:
        decoded_dn = unquote(dn)

        entry = await dept_repo.update(decoded_dn, updates)

        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Department not found: {decoded_dn}",
            )

        logger.info("department_updated", dn=decoded_dn, by=current_user.uid)

        children_count = await dept_repo.get_children_count(decoded_dn)
        return dept_repo._entry_to_response(entry, children_count)

    except LdapOperationError as e:
        logger.error("update_department_failed", dn=dn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update department: {e}",
        )


@router.delete("/{dn:path}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    dn: str,
    current_user: CurrentUser,
    dept_repo: DeptRepoDep,
    recursive: bool = Query(False, description="Delete all children recursively"),
):
    """
    Delete a department.

    Use recursive=true to delete all children.
    """
    try:
        decoded_dn = unquote(dn)

        deleted = await dept_repo.delete(decoded_dn, recursive=recursive)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Department not found: {decoded_dn}",
            )

        logger.info("department_deleted", dn=decoded_dn, recursive=recursive, by=current_user.uid)

    except LdapOperationError as e:
        error_msg = str(e)
        logger.error("delete_department_failed", dn=dn, error=error_msg)

        if "has" in error_msg.lower() and "children" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_msg,
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete department: {e}",
        )
