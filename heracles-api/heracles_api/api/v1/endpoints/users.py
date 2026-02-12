"""
Users Endpoints
===============

User management endpoints (CRUD operations).
"""

import structlog
from fastapi import APIRouter, HTTPException, Query, status

from heracles_api.config import settings
from heracles_api.core.dependencies import AclGuardDep, AclRepoDep, CurrentUser, GroupRepoDep, UserRepoDep
from heracles_api.core.password_policy import validate_password_policy
from heracles_api.schemas import (
    SetPasswordRequest,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)
from heracles_api.services import LdapOperationError

logger = structlog.get_logger(__name__)
router = APIRouter()


def _entry_to_response(entry, groups: list[str] = None) -> UserResponse:
    """Convert LDAP entry to UserResponse."""
    # Handle jpegPhoto binary → base64
    photo_raw = entry.get_first("jpegPhoto")
    if photo_raw:
        import base64

        if isinstance(photo_raw, bytes):
            photo_b64 = base64.b64encode(photo_raw).decode("ascii")
        else:
            photo_b64 = str(photo_raw)
    else:
        photo_b64 = None

    return UserResponse(
        dn=entry.dn,
        uid=entry.get_first("uid", ""),
        cn=entry.get_first("cn", ""),
        sn=entry.get_first("sn", ""),
        givenName=entry.get_first("givenName"),
        mail=entry.get_first("mail"),
        telephoneNumber=entry.get_first("telephoneNumber"),
        title=entry.get_first("title"),
        description=entry.get_first("description"),
        # Personal
        displayName=entry.get_first("displayName"),
        labeledURI=entry.get_first("labeledURI"),
        preferredLanguage=entry.get_first("preferredLanguage"),
        jpegPhoto=photo_b64,
        # Contact
        mobile=entry.get_first("mobile"),
        facsimileTelephoneNumber=entry.get_first("facsimileTelephoneNumber"),
        # Address
        street=entry.get_first("street"),
        postalAddress=entry.get_first("postalAddress"),
        l=entry.get_first("l"),
        st=entry.get_first("st"),
        postalCode=entry.get_first("postalCode"),
        c=entry.get_first("c"),
        roomNumber=entry.get_first("roomNumber"),
        # Organization
        o=entry.get_first("o"),
        organizationalUnit=entry.get_first("ou"),
        departmentNumber=entry.get_first("departmentNumber"),
        employeeNumber=entry.get_first("employeeNumber"),
        employeeType=entry.get_first("employeeType"),
        manager=entry.get_first("manager"),
        # Membership
        memberOf=groups or [],
    )


@router.get("", response_model=UserListResponse)
async def list_users(
    current_user: CurrentUser,
    guard: AclGuardDep,
    user_repo: UserRepoDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: str | None = Query(None, description="Search in uid, cn, mail"),
    ou: str | None = Query(None, description="Filter by organizational unit"),
    base: str | None = Query(None, description="Base DN (e.g., department DN) for scoped search"),
):
    """
    List all users with pagination.

    Requires: user:read
    """
    # ACL check - user:read on the base DN or global
    target_dn = base or f"ou=people,{settings.LDAP_BASE_DN}"
    guard.require(target_dn, "user:read")

    try:
        result = await user_repo.search(search_term=search, ou=ou, base_dn=base)

        total = result.total

        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size
        page_entries = result.users[start:end]

        # Get group memberships for each user
        users = []
        for entry in page_entries:
            groups = await user_repo.get_groups(entry.dn)
            users.append(_entry_to_response(entry, groups))

        return UserListResponse(
            users=users,
            total=total,
            page=page,
            page_size=page_size,
            has_more=end < total,
        )

    except LdapOperationError as e:
        logger.error("list_users_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users",
        )


@router.get("/{uid}", response_model=UserResponse)
async def get_user(
    uid: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    user_repo: UserRepoDep,
):
    """
    Get user by UID.

    Requires: user:read
    """
    try:
        entry = await user_repo.find_by_uid(uid)

        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{uid}' not found",
            )

        # ACL check - user:read on the specific user
        guard.require(entry.dn, "user:read")

        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{uid}' not found",
            )

        groups = await user_repo.get_groups(entry.dn)
        return _entry_to_response(entry, groups)

    except LdapOperationError as e:
        logger.error("get_user_failed", uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user",
        )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate,
    current_user: CurrentUser,
    guard: AclGuardDep,
    user_repo: UserRepoDep,
    acl_repo: AclRepoDep,
):
    """
    Create a new user.

    Requires: user:create
    """
    # ACL check - user:create on the target container
    target_dn = user.department_dn or f"ou=people,{settings.LDAP_BASE_DN}"
    guard.require(target_dn, "user:create")

    # Check if user already exists
    if await user_repo.exists(user.uid):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User '{user.uid}' already exists",
        )

    # Validate password against policy
    is_valid, errors = await validate_password_policy(user.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Password does not meet policy requirements",
                "errors": errors,
            },
        )

    try:
        entry = await user_repo.create(user, department_dn=user.department_dn)

        logger.info("user_created", uid=user.uid, department_dn=user.department_dn, by=current_user.uid)

        # Auto-assign Self Service ACL policy to every new user
        try:
            self_service_policy = await acl_repo.get_policy_by_name("Self Service")
            if self_service_policy:
                already = await acl_repo.assignment_exists(
                    policy_id=self_service_policy.id,
                    subject_type="user",
                    subject_dn=entry.dn,
                    scope_dn=entry.dn,
                    self_only=True,
                )
                if not already:
                    await acl_repo.create_assignment(
                        policy_id=self_service_policy.id,
                        subject_type="user",
                        subject_dn=entry.dn,
                        scope_dn=entry.dn,
                        scope_type="base",
                        self_only=True,
                        deny=False,
                        priority=0,
                    )
                    logger.info("self_service_assigned", uid=user.uid, dn=entry.dn)
            else:
                logger.warning("self_service_policy_not_found", uid=user.uid)
        except Exception as e:
            logger.warning("self_service_assignment_failed", uid=user.uid, error=str(e))

        # Apply template plugin activations if a template was specified
        if user.template_id:
            try:
                import uuid as _uuid

                from heracles_api.plugins.registry import plugin_registry
                from heracles_api.services.template_service import get_template_service

                tmpl_service = get_template_service()
                tmpl = await tmpl_service.get_template(_uuid.UUID(user.template_id))
                if tmpl and tmpl.pluginActivations:
                    for plugin_name, plugin_config in tmpl.pluginActivations.items():
                        tab_service = plugin_registry.get_service_for_plugin(plugin_name, "user")
                        if not tab_service:
                            logger.warning(
                                "template_plugin_not_available",
                                plugin=plugin_name,
                                uid=user.uid,
                            )
                            continue
                        try:
                            attrs = plugin_config if isinstance(plugin_config, dict) else {}
                            await tab_service.activate(entry.dn, attrs)
                            logger.info(
                                "template_plugin_activated",
                                plugin=plugin_name,
                                uid=user.uid,
                            )
                        except Exception as e:
                            logger.warning(
                                "template_plugin_activation_failed",
                                plugin=plugin_name,
                                uid=user.uid,
                                error=str(e),
                            )
            except Exception as e:
                logger.warning(
                    "template_apply_failed",
                    template_id=user.template_id,
                    uid=user.uid,
                    error=str(e),
                )

        return _entry_to_response(entry, [])

    except LdapOperationError as e:
        logger.error("create_user_failed", uid=user.uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {e}",
        )


@router.patch("/{uid}", response_model=UserResponse)
async def update_user(
    uid: str,
    updates: UserUpdate,
    current_user: CurrentUser,
    guard: AclGuardDep,
    user_repo: UserRepoDep,
):
    """
    Update user attributes.

    Requires: user:write
    """
    # Find user first to get DN
    entry = await user_repo.find_by_uid(uid)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{uid}' not found",
        )

    # ACL check - user:write on the specific user
    guard.require(entry.dn, "user:write")

    try:
        entry = await user_repo.update(uid, updates)

        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{uid}' not found",
            )

        logger.info("user_updated", uid=uid, by=current_user.uid)

        groups = await user_repo.get_groups(entry.dn)
        return _entry_to_response(entry, groups)

    except LdapOperationError as e:
        logger.error("update_user_failed", uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {e}",
        )


@router.delete("/{uid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    uid: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    user_repo: UserRepoDep,
    group_repo: GroupRepoDep,
):
    """
    Delete a user.

    Requires: user:delete
    """
    # Prevent self-deletion
    if uid == current_user.uid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    # Find user
    entry = await user_repo.find_by_uid(uid)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{uid}' not found",
        )

    # ACL check - user:delete on the specific user
    guard.require(entry.dn, "user:delete")

    try:
        # Remove user from all groups first
        await group_repo.remove_user_from_all_groups(entry.dn)

        # Delete user
        await user_repo.delete(uid)

        logger.info("user_deleted", uid=uid, by=current_user.uid)

    except LdapOperationError as e:
        logger.error("delete_user_failed", uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {e}",
        )


@router.post("/{uid}/password", status_code=status.HTTP_204_NO_CONTENT)
async def set_user_password(
    uid: str,
    request: SetPasswordRequest,
    current_user: CurrentUser,
    guard: AclGuardDep,
    user_repo: UserRepoDep,
):
    """
    Set user password (admin operation).

    Requires: user:manage
    """
    entry = await user_repo.find_by_uid(uid)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{uid}' not found",
        )

    # ACL check - user:manage on the specific user
    guard.require(entry.dn, "user:manage")

    # Validate password against policy
    is_valid, errors = await validate_password_policy(request.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Password does not meet policy requirements",
                "errors": errors,
            },
        )

    try:
        await user_repo.set_password(uid, request.password)

        logger.info("user_password_set", uid=uid, by=current_user.uid)

    except LdapOperationError as e:
        logger.error("set_password_failed", uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set password: {e}",
        )


@router.post("/{uid}/lock", status_code=status.HTTP_204_NO_CONTENT)
async def lock_user(
    uid: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    user_repo: UserRepoDep,
):
    """
    Lock a user account (prevent login).

    Requires: user:manage
    """
    # Prevent self-locking
    if uid == current_user.uid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot lock your own account",
        )

    entry = await user_repo.find_by_uid(uid)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{uid}' not found",
        )

    # ACL check - user:manage on the specific user
    guard.require(entry.dn, "user:manage")

    try:
        await user_repo.lock(uid)
        logger.info("user_locked", uid=uid, by=current_user.uid)

    except LdapOperationError as e:
        logger.error("lock_user_failed", uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to lock user: {e}",
        )


@router.post("/{uid}/unlock", status_code=status.HTTP_204_NO_CONTENT)
async def unlock_user(
    uid: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    user_repo: UserRepoDep,
):
    """
    Unlock a user account.

    Requires: user:manage
    """
    entry = await user_repo.find_by_uid(uid)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{uid}' not found",
        )

    # ACL check - user:manage on the specific user
    guard.require(entry.dn, "user:manage")

    try:
        await user_repo.unlock(uid)
        logger.info("user_unlocked", uid=uid, by=current_user.uid)

    except LdapOperationError as e:
        logger.error("unlock_user_failed", uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unlock user: {e}",
        )


@router.get("/{uid}/locked")
async def get_user_lock_status(
    uid: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    user_repo: UserRepoDep,
):
    """
    Get user lock status.

    Requires: user:read
    """
    entry = await user_repo.find_by_uid(uid)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{uid}' not found",
        )

    # ACL check - user:read on the specific user
    guard.require(entry.dn, "user:read")

    is_locked = await user_repo.is_locked(uid)

    return {"uid": uid, "locked": is_locked}


# ---------------------------------------------------------------------------
# Photo endpoints
# ---------------------------------------------------------------------------


@router.put("/{uid}/photo", status_code=status.HTTP_204_NO_CONTENT)
async def upload_user_photo(
    uid: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    user_repo: UserRepoDep,
    photo: str = None,
):
    """
    Upload or update user photo (jpegPhoto attribute).

    Accepts a JSON body with base64-encoded JPEG data.
    Max size: 512 KB after decoding.

    Requires: user:write
    """
    import base64

    entry = await user_repo.find_by_uid(uid)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{uid}' not found",
        )

    guard.require(entry.dn, "user:write")

    if not photo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Photo data is required",
        )

    try:
        raw = base64.b64decode(photo)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base64 data",
        )

    if len(raw) > 512 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Photo exceeds 512 KB size limit",
        )

    try:
        from heracles_api.services import get_ldap_service

        ldap = get_ldap_service()
        await ldap.modify(entry.dn, {"jpegPhoto": ("replace", [raw])})
        logger.info("user_photo_updated", uid=uid, by=current_user.uid)
    except LdapOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update photo: {e}",
        )


@router.delete("/{uid}/photo", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_photo(
    uid: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    user_repo: UserRepoDep,
):
    """
    Delete user photo.

    Requires: user:write
    """
    entry = await user_repo.find_by_uid(uid)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{uid}' not found",
        )

    guard.require(entry.dn, "user:write")

    try:
        from heracles_api.services import get_ldap_service

        ldap = get_ldap_service()
        await ldap.modify(entry.dn, {"jpegPhoto": ("delete", [])})
        logger.info("user_photo_deleted", uid=uid, by=current_user.uid)
    except LdapOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete photo: {e}",
        )
