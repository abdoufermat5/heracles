"""
SSH Plugin Routes
=================

FastAPI routes for SSH key management.
"""

from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, Depends, Query, Path

import structlog

from .schemas import (
    SSHKeyCreate,
    SSHKeyRead,
    UserSSHStatus,
    UserSSHActivate,
    UserSSHKeysUpdate,
)
from .service import SSHService, SSHKeyValidationError


logger = structlog.get_logger(__name__)


# ============================================================================
# Router Setup
# ============================================================================

router = APIRouter(
    prefix="/ssh",
    tags=["ssh"],
    responses={
        404: {"description": "Not found"},
        401: {"description": "Unauthorized"},
    },
)


def get_ssh_service() -> SSHService:
    """Get SSH service instance from plugin registry."""
    from heracles_api.plugins.registry import plugin_registry
    
    service = plugin_registry.get_service("ssh")
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SSH plugin not loaded",
        )
    return service


# Import CurrentUser from core dependencies
from heracles_api.core.dependencies import CurrentUser


# ============================================================================
# User SSH Status Endpoints
# ============================================================================

@router.get(
    "/users/{uid}",
    response_model=UserSSHStatus,
    summary="Get user SSH status",
    description="Get SSH status and keys for a user",
)
async def get_user_ssh_status(
    uid: str,
    current_user: CurrentUser,
    service: SSHService = Depends(get_ssh_service),
) -> UserSSHStatus:
    """Get SSH status for a user."""
    try:
        return await service.get_user_ssh_status(uid)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {uid}",
            )
        logger.error("get_user_ssh_status_error", uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/users/{uid}/activate",
    response_model=UserSSHStatus,
    status_code=status.HTTP_200_OK,
    summary="Activate SSH for user",
    description="Add ldapPublicKey objectClass to enable SSH key storage",
)
async def activate_user_ssh(
    uid: str,
    current_user: CurrentUser,
    data: Optional[UserSSHActivate] = None,
    service: SSHService = Depends(get_ssh_service),
) -> UserSSHStatus:
    """Activate SSH for a user account."""
    try:
        return await service.activate_ssh(uid, data)
    except SSHKeyValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {uid}",
            )
        logger.error("activate_user_ssh_error", uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/users/{uid}/deactivate",
    response_model=UserSSHStatus,
    status_code=status.HTTP_200_OK,
    summary="Deactivate SSH for user",
    description="Remove ldapPublicKey objectClass and all SSH keys",
)
async def deactivate_user_ssh(
    uid: str,
    current_user: CurrentUser,
    service: SSHService = Depends(get_ssh_service),
) -> UserSSHStatus:
    """Deactivate SSH for a user account."""
    try:
        return await service.deactivate_ssh(uid)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {uid}",
            )
        logger.error("deactivate_user_ssh_error", uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# SSH Key Management Endpoints
# ============================================================================

@router.get(
    "/users/{uid}/keys",
    response_model=List[SSHKeyRead],
    summary="List user SSH keys",
    description="Get all SSH public keys for a user",
)
async def list_user_ssh_keys(
    uid: str,
    current_user: CurrentUser,
    service: SSHService = Depends(get_ssh_service),
) -> List[SSHKeyRead]:
    """List SSH keys for a user."""
    try:
        ssh_status = await service.get_user_ssh_status(uid)
        return ssh_status.keys
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {uid}",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/users/{uid}/keys",
    response_model=UserSSHStatus,
    status_code=status.HTTP_201_CREATED,
    summary="Add SSH key",
    description="Add a new SSH public key to a user account",
)
async def add_user_ssh_key(
    uid: str,
    data: SSHKeyCreate,
    current_user: CurrentUser,
    service: SSHService = Depends(get_ssh_service),
) -> UserSSHStatus:
    """Add an SSH key to a user."""
    try:
        return await service.add_key(uid, data)
    except SSHKeyValidationError as e:
        # Config-based validation failure (e.g., key type not allowed, RSA too small)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {uid}",
            )
        if "already exists" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            )
        logger.error("add_user_ssh_key_error", uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.put(
    "/users/{uid}/keys",
    response_model=UserSSHStatus,
    summary="Replace all SSH keys",
    description="Replace all SSH keys for a user (bulk update)",
)
async def update_user_ssh_keys(
    uid: str,
    data: UserSSHKeysUpdate,
    current_user: CurrentUser,
    service: SSHService = Depends(get_ssh_service),
) -> UserSSHStatus:
    """Replace all SSH keys for a user."""
    try:
        return await service.update_keys(uid, data)
    except SSHKeyValidationError as e:
        # Config-based validation failure (e.g., key type not allowed, RSA too small)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {uid}",
            )
        logger.error("update_user_ssh_keys_error", uid=uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/users/{uid}/keys/{fingerprint:path}",
    response_model=SSHKeyRead,
    summary="Get SSH key by fingerprint",
    description="Get a specific SSH key by its fingerprint",
)
async def get_user_ssh_key(
    uid: str,
    fingerprint: str,
    current_user: CurrentUser,
    service: SSHService = Depends(get_ssh_service),
) -> SSHKeyRead:
    """Get a specific SSH key."""
    # Decode fingerprint (replace URL-safe chars)
    fingerprint = fingerprint.replace("_", "/").replace("-", "+")
    if not fingerprint.startswith("SHA256:"):
        fingerprint = f"SHA256:{fingerprint}"
    
    try:
        return await service.get_key_by_fingerprint(uid, fingerprint)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SSH key not found: {fingerprint}",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete(
    "/users/{uid}/keys/{fingerprint:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove SSH key",
    description="Remove an SSH key by its fingerprint",
)
async def remove_user_ssh_key(
    uid: str,
    fingerprint: str,
    current_user: CurrentUser,
    service: SSHService = Depends(get_ssh_service),
) -> None:
    """Remove an SSH key from a user."""
    # Decode fingerprint
    fingerprint = fingerprint.replace("_", "/").replace("-", "+")
    if not fingerprint.startswith("SHA256:"):
        fingerprint = f"SHA256:{fingerprint}"
    
    try:
        await service.remove_key(uid, fingerprint)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SSH key not found: {fingerprint}",
            )
        logger.error("remove_user_ssh_key_error", uid=uid, fingerprint=fingerprint, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Key Lookup Endpoints
# ============================================================================

@router.get(
    "/lookup",
    response_model=Optional[str],
    summary="Find user by SSH key",
    description="Find which user owns a specific SSH key",
)
async def find_user_by_ssh_key(
    current_user: CurrentUser,
    key: Optional[str] = Query(None, description="Full SSH public key"),
    fingerprint: Optional[str] = Query(None, description="SHA256 fingerprint"),
    service: SSHService = Depends(get_ssh_service),
) -> Optional[str]:
    """Find a user by SSH key or fingerprint."""
    if not key and not fingerprint:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'key' or 'fingerprint' parameter is required",
        )
    
    search_value = key or fingerprint
    
    try:
        uid = await service.find_user_by_key(search_value)
        if not uid:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No user found with this SSH key",
            )
        return uid
    except HTTPException:
        raise
    except Exception as e:
        logger.error("find_user_by_ssh_key_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
