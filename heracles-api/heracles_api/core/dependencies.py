"""
FastAPI Dependencies
====================

Common dependencies for API endpoints.
"""

from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status, Request, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from redis.asyncio import Redis

from heracles_api.services import (
    get_ldap_service,
    get_auth_service,
    LdapService,
    AuthService,
    TokenError,
    UserSession,
)
from heracles_api.repositories import UserRepository, GroupRepository, RoleRepository, DepartmentRepository
from heracles_api.config import settings

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


async def get_redis() -> Optional[Redis]:
    """Get Redis connection."""
    # TODO: Use connection pool
    try:
        redis = Redis.from_url(
            settings.REDIS_URL,
            password=settings.REDIS_PASSWORD,
            decode_responses=False,
        )
        return redis
    except Exception:
        return None


async def get_ldap() -> LdapService:
    """Get LDAP service dependency."""
    return get_ldap_service()


async def get_auth(redis: Annotated[Optional[Redis], Depends(get_redis)]) -> AuthService:
    """Get Auth service dependency with Redis."""
    service = get_auth_service()
    service.redis = redis
    return service


async def get_user_repository(ldap: Annotated[LdapService, Depends(get_ldap)]) -> UserRepository:
    """Get User repository dependency."""
    return UserRepository(ldap)


async def get_group_repository(ldap: Annotated[LdapService, Depends(get_ldap)]) -> GroupRepository:
    """Get Group repository dependency."""
    return GroupRepository(ldap)


async def get_role_repository(ldap: Annotated[LdapService, Depends(get_ldap)]) -> RoleRepository:
    """Get Role repository dependency."""
    return RoleRepository(ldap)


async def get_department_repository(ldap: Annotated[LdapService, Depends(get_ldap)]) -> DepartmentRepository:
    """Get Department repository dependency."""
    return DepartmentRepository(ldap)


async def get_current_user(
    request: Request,
    auth: Annotated[AuthService, Depends(get_auth)],
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)] = None,
) -> UserSession:
    """
    Get current authenticated user from JWT token (Cookie or Bearer).
    
    Raises HTTPException 401 if not authenticated.
    """
    token = request.cookies.get("access_token")
    
    if not token and credentials:
        token = credentials.credentials
        
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Verify token
        payload = auth.verify_token(token, token_type="access")
        
        # Check if token is revoked
        if await auth.is_token_revoked(payload.jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get session
        session = await auth.get_session(payload.jti)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Update activity
        await auth.update_session_activity(payload.jti)
        
        return session
        
    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    request: Request,
    auth: Annotated[AuthService, Depends(get_auth)],
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)] = None,
) -> Optional[UserSession]:
    """
    Get current user if authenticated, None otherwise.
    
    Does not raise exception if not authenticated.
    """
    token = request.cookies.get("access_token")
    
    if not token and credentials:
        token = credentials.credentials
        
    if not token:
        return None
    
    try:
        payload = auth.verify_token(token, token_type="access")
        
        if await auth.is_token_revoked(payload.jti):
            return None
        
        session = await auth.get_session(payload.jti)
        if session:
            await auth.update_session_activity(payload.jti)
        
        return session
        
    except TokenError:
        return None


# Type aliases for cleaner endpoint signatures
CurrentUser = Annotated[UserSession, Depends(get_current_user)]
OptionalUser = Annotated[Optional[UserSession], Depends(get_optional_user)]
LdapDep = Annotated[LdapService, Depends(get_ldap)]
AuthDep = Annotated[AuthService, Depends(get_auth)]
RedisDep = Annotated[Optional[Redis], Depends(get_redis)]
UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]
GroupRepoDep = Annotated[GroupRepository, Depends(get_group_repository)]
RoleRepoDep = Annotated[RoleRepository, Depends(get_role_repository)]
DeptRepoDep = Annotated[DepartmentRepository, Depends(get_department_repository)]
