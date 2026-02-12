"""
FastAPI Dependencies
====================

Common dependencies for API endpoints.
"""

from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from heracles_api.services import (
    get_ldap_service,
    get_auth_service,
    LdapService,
    AuthService,
    TokenError,
    UserSession,
)
from heracles_api.repositories import (
    UserRepository,
    GroupRepository,
    RoleRepository,
    DepartmentRepository,
    AclRepository,
    ConfigRepository,
    PluginConfigRepository,
    ConfigHistoryRepository,
)
from heracles_api.acl.guard import AclGuard
from heracles_api.core.database import get_db_session

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


async def get_redis(request: Request) -> Optional[Redis]:
    """Get shared Redis connection from app state."""
    return getattr(request.app.state, "redis", None)


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


# --- PostgreSQL repositories ---


async def get_acl_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AclRepository:
    """Get ACL repository dependency."""
    return AclRepository(session)


async def get_config_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ConfigRepository:
    """Get Config repository dependency."""
    return ConfigRepository(session)


async def get_plugin_config_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PluginConfigRepository:
    """Get PluginConfig repository dependency."""
    return PluginConfigRepository(session)


async def get_config_history_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ConfigHistoryRepository:
    """Get ConfigHistory repository dependency."""
    return ConfigHistoryRepository(session)


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

# PostgreSQL repository type aliases
DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
AclRepoDep = Annotated[AclRepository, Depends(get_acl_repository)]
ConfigRepoDep = Annotated[ConfigRepository, Depends(get_config_repository)]
PluginConfigRepoDep = Annotated[PluginConfigRepository, Depends(get_plugin_config_repository)]
ConfigHistoryRepoDep = Annotated[ConfigHistoryRepository, Depends(get_config_history_repository)]


async def get_acl_guard(
    request: Request,
    current_user: CurrentUser,
    redis: RedisDep,
) -> AclGuard:
    """
    Build AclGuard for the current user.
    
    Loads or compiles the user's ACL and returns a guard
    for permission checks in endpoints.
    
    Args:
        request: The current request (for app state access).
        current_user: The authenticated user.
        redis: Redis connection for ACL cache.
        
    Returns:
        AclGuard for permission checking.
        
    Raises:
        HTTPException: 500 if ACL system not initialized.
    """
    # Get registry from app state
    registry = getattr(request.app.state, "acl_registry", None)
    if registry is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ACL system not initialized",
        )
    
    # Try to load from request state (set by middleware) or cache
    user_acl = getattr(request.state, "user_acl", None)

    if user_acl is None:
        # Compile or fetch from cache via AclService
        from heracles_api.acl.service import AclService
        from heracles_api.core.database import get_session_factory

        acl_service = AclService(get_session_factory(), redis, registry)

        # Get user's group and role memberships for ACL compilation
        group_dns = getattr(current_user, "groups", [])
        role_dns = getattr(current_user, "roles", [])

        user_acl = await acl_service.get_or_compile(
            current_user.user_dn,
            group_dns,
            role_dns,
        )

        # Cache on request state for subsequent calls
        request.state.user_acl = user_acl
    
    return AclGuard(user_acl, registry, current_user.user_dn)


AclGuardDep = Annotated[AclGuard, Depends(get_acl_guard)]
