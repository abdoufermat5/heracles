"""
Authentication Endpoints
========================

Handles user authentication (login, logout, password reset).
"""

from fastapi import APIRouter, HTTPException, status

from heracles_api.core.dependencies import (
    CurrentUser,
    LdapDep,
    AuthDep,
    UserRepoDep,
)
from heracles_api.schemas import (
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    UserInfoResponse,
    PasswordChangeRequest,
    PasswordResetRequest,
)
from heracles_api.services import (
    LdapAuthenticationError,
    LdapOperationError,
    TokenError,
)
from heracles_api.config import settings

import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    ldap: LdapDep,
    auth: AuthDep,
    user_repo: UserRepoDep,
):
    """
    Authenticate user with LDAP credentials.
    
    Returns JWT tokens for subsequent API calls.
    """
    try:
        # Authenticate with LDAP
        user = await user_repo.authenticate(request.username, request.password)
        
        if user is None:
            logger.warning("login_failed", username=request.username)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )
        
        # Extract user info
        uid = user.get_first("uid", request.username)
        display_name = user.get_first("cn", uid)
        mail = user.get_first("mail")
        
        # Get user's groups
        groups = await user_repo.get_groups(user.dn)
        group_dns = [f"cn={g},ou=groups,{settings.LDAP_BASE_DN}" for g in groups]
        
        # Create tokens
        access_token, access_jti = auth.create_access_token(
            user_dn=user.dn,
            uid=uid,
            additional_claims={"groups": groups},
        )
        
        refresh_token, _ = auth.create_refresh_token(
            user_dn=user.dn,
            uid=uid,
        )
        
        # Create session
        await auth.create_session(
            user_dn=user.dn,
            uid=uid,
            display_name=display_name,
            mail=mail,
            groups=group_dns,
            token_jti=access_jti,
        )
        
        logger.info("login_success", uid=uid, user_dn=user.dn)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=3600,
        )
        
    except LdapAuthenticationError as e:
        logger.error("login_ldap_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable",
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshRequest,
    auth: AuthDep,
    user_repo: UserRepoDep,
):
    """
    Refresh access token using refresh token.
    """
    try:
        # Verify refresh token
        payload = auth.verify_token(request.refresh_token, token_type="refresh")
        
        # Get fresh user data from LDAP
        user = await user_repo.find_by_dn(payload.sub)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User no longer exists",
            )
        
        uid = user.get_first("uid", payload.uid)
        display_name = user.get_first("cn", uid)
        mail = user.get_first("mail")
        
        # Get user's groups
        groups = await user_repo.get_groups(user.dn)
        group_dns = [f"cn={g},ou=groups,{settings.LDAP_BASE_DN}" for g in groups]
        
        # Create new tokens
        access_token, access_jti = auth.create_access_token(
            user_dn=user.dn,
            uid=uid,
            additional_claims={"groups": groups},
        )
        
        refresh_token, _ = auth.create_refresh_token(
            user_dn=user.dn,
            uid=uid,
        )
        
        # Create new session
        await auth.create_session(
            user_dn=user.dn,
            uid=uid,
            display_name=display_name,
            mail=mail,
            groups=group_dns,
            token_jti=access_jti,
        )
        
        logger.info("token_refreshed", uid=uid)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=3600,
        )
        
    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: CurrentUser,
    auth: AuthDep,
):
    """
    Logout current user.
    
    Invalidates the current session.
    """
    await auth.invalidate_session(current_user.token_jti)
    logger.info("logout_success", uid=current_user.uid)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all_sessions(
    current_user: CurrentUser,
    auth: AuthDep,
):
    """
    Logout from all sessions.
    
    Invalidates all sessions for the current user.
    """
    count = await auth.invalidate_all_user_sessions(current_user.uid)
    logger.info("logout_all_success", uid=current_user.uid, sessions_invalidated=count)


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(current_user: CurrentUser):
    """
    Get current authenticated user information.
    """
    return UserInfoResponse(
        dn=current_user.user_dn,
        uid=current_user.uid,
        display_name=current_user.display_name,
        mail=current_user.mail,
        groups=current_user.groups,
    )


@router.post("/password/change", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    request: PasswordChangeRequest,
    current_user: CurrentUser,
    auth: AuthDep,
    user_repo: UserRepoDep,
):
    """
    Change current user's password.
    
    Requires current password for verification.
    """
    # Verify current password
    user = await user_repo.authenticate(current_user.uid, request.current_password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )
    
    # Set new password
    try:
        await user_repo.set_password(current_user.uid, request.new_password)
        
        # Invalidate all other sessions
        await auth.invalidate_all_user_sessions(current_user.uid)
        
        logger.info("password_changed", uid=current_user.uid)
        
    except LdapOperationError as e:
        logger.error("password_change_failed", uid=current_user.uid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password",
        )


@router.post("/password/reset/request", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(
    request: PasswordResetRequest,
    user_repo: UserRepoDep,
):
    """
    Request a password reset.
    
    Sends a reset link to the user's email (if found).
    Always returns 202 to prevent email enumeration.
    """
    try:
        user = await user_repo.find_by_mail(request.email)
        
        if user:
            # TODO: Send reset email
            logger.info("password_reset_requested", uid=user.get_first("uid"), email=request.email)
        else:
            logger.info("password_reset_unknown_email", email=request.email)
            
    except LdapOperationError:
        pass
    
    # Always return success to prevent enumeration
    return {"message": "If the email exists, a reset link will be sent"}
