"""
Mail Plugin Routes
==================

FastAPI routes for mail account management.
"""


from fastapi import APIRouter, HTTPException, status, Depends

import structlog

from heracles_api.core.dependencies import CurrentUser, AclGuardDep

from .schemas import (
    MailAccountCreate,
    MailAccountUpdate,
    UserMailStatus,
    MailGroupCreate,
    MailGroupUpdate,
    GroupMailStatus,
)
from .service import (
    MailUserService,
    MailGroupService,
    MailValidationError,
    MailAlreadyExistsError,
)


logger = structlog.get_logger(__name__)


# ============================================================================
# Router Setup
# ============================================================================

router = APIRouter(
    prefix="/mail",
    tags=["mail"],
    responses={
        404: {"description": "Not found"},
        401: {"description": "Unauthorized"},
    },
)


def get_mail_user_service() -> MailUserService:
    """Get mail user service from plugin registry."""
    from heracles_api.plugins.registry import plugin_registry

    service = plugin_registry.get_service("mail")
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mail plugin not loaded",
        )
    return service


def get_mail_group_service() -> MailGroupService:
    """Get mail group service from plugin registry."""
    from heracles_api.plugins.registry import plugin_registry

    service = plugin_registry.get_service("mail-group")
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mail plugin not loaded",
        )
    return service


# ============================================================================
# User Mail Endpoints
# ============================================================================


@router.get(
    "/users/{uid}",
    response_model=UserMailStatus,
    summary="Get user mail status",
    description="Get mail account status and data for a user",
)
async def get_user_mail_status(
    uid: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    service: MailUserService = Depends(get_mail_user_service),
) -> UserMailStatus:
    """Get mail status for a user."""
    guard.require(service.get_base_dn(), "mail:read")
    try:
        return await service.get_user_mail_status(uid)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {uid}",
            )
        logger.error("get_user_mail_status_error", uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/users/{uid}/activate",
    response_model=UserMailStatus,
    status_code=status.HTTP_201_CREATED,
    summary="Activate mail for user",
    description="Add hrcMailAccount objectClass to enable mail account",
)
async def activate_user_mail(
    uid: str,
    data: MailAccountCreate,
    current_user: CurrentUser,
    guard: AclGuardDep,
    service: MailUserService = Depends(get_mail_user_service),
) -> UserMailStatus:
    """Activate mail account for a user."""
    guard.require(service.get_base_dn(), "mail:create")
    try:
        return await service.activate_mail(uid, data)
    except MailAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except MailValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {uid}",
            )
        logger.error("activate_user_mail_error", uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.patch(
    "/users/{uid}",
    response_model=UserMailStatus,
    summary="Update user mail account",
    description="Update mail account attributes",
)
async def update_user_mail(
    uid: str,
    data: MailAccountUpdate,
    current_user: CurrentUser,
    guard: AclGuardDep,
    service: MailUserService = Depends(get_mail_user_service),
) -> UserMailStatus:
    """Update mail account for a user."""
    guard.require(service.get_base_dn(), "mail:write")
    try:
        return await service.update_mail(uid, data)
    except MailAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except MailValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {uid}",
            )
        logger.error("update_user_mail_error", uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/users/{uid}/deactivate",
    response_model=UserMailStatus,
    summary="Deactivate mail for user",
    description="Remove hrcMailAccount objectClass and all mail attributes",
)
async def deactivate_user_mail(
    uid: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    service: MailUserService = Depends(get_mail_user_service),
) -> UserMailStatus:
    """Deactivate mail account for a user."""
    guard.require(service.get_base_dn(), "mail:delete")
    try:
        return await service.deactivate_mail(uid)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {uid}",
            )
        logger.error("deactivate_user_mail_error", uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Group Mail Endpoints
# ============================================================================


@router.get(
    "/groups/{cn}",
    response_model=GroupMailStatus,
    summary="Get group mail status",
    description="Get mailing list status and data for a group",
)
async def get_group_mail_status(
    cn: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    service: MailGroupService = Depends(get_mail_group_service),
) -> GroupMailStatus:
    """Get mail status for a group."""
    guard.require(service.get_base_dn(), "mail:read")
    try:
        return await service.get_group_mail_status(cn)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group not found: {cn}",
            )
        logger.error("get_group_mail_status_error", cn=cn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/groups/{cn}/activate",
    response_model=GroupMailStatus,
    status_code=status.HTTP_201_CREATED,
    summary="Activate mailing list for group",
    description="Add hrcGroupMail objectClass to enable mailing list",
)
async def activate_group_mail(
    cn: str,
    data: MailGroupCreate,
    current_user: CurrentUser,
    guard: AclGuardDep,
    service: MailGroupService = Depends(get_mail_group_service),
) -> GroupMailStatus:
    """Activate mailing list for a group."""
    guard.require(service.get_base_dn(), "mail:create")
    try:
        return await service.activate_mail(cn, data)
    except MailAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except MailValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group not found: {cn}",
            )
        logger.error("activate_group_mail_error", cn=cn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.patch(
    "/groups/{cn}",
    response_model=GroupMailStatus,
    summary="Update group mailing list",
    description="Update mailing list attributes",
)
async def update_group_mail(
    cn: str,
    data: MailGroupUpdate,
    current_user: CurrentUser,
    guard: AclGuardDep,
    service: MailGroupService = Depends(get_mail_group_service),
) -> GroupMailStatus:
    """Update mailing list for a group."""
    guard.require(service.get_base_dn(), "mail:write")
    try:
        return await service.update_mail(cn, data)
    except MailAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except MailValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group not found: {cn}",
            )
        logger.error("update_group_mail_error", cn=cn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/groups/{cn}/deactivate",
    response_model=GroupMailStatus,
    summary="Deactivate mailing list for group",
    description="Remove hrcGroupMail objectClass and all mail attributes",
)
async def deactivate_group_mail(
    cn: str,
    current_user: CurrentUser,
    guard: AclGuardDep,
    service: MailGroupService = Depends(get_mail_group_service),
) -> GroupMailStatus:
    """Deactivate mailing list for a group."""
    guard.require(service.get_base_dn(), "mail:delete")
    try:
        return await service.deactivate_mail(cn)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group not found: {cn}",
            )
        logger.error("deactivate_group_mail_error", cn=cn, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
