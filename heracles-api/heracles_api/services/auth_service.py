"""
JWT Authentication Service
==========================

Handles JWT token creation, validation, and session management.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Dict
from dataclasses import dataclass
import secrets

import jwt
import structlog
from redis.asyncio import Redis

from heracles_api.config import settings

logger = structlog.get_logger(__name__)

# JWT Configuration
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7


class AuthenticationError(Exception):
    """Authentication failed."""
    pass


class TokenError(Exception):
    """Token validation/creation failed."""
    pass


@dataclass
class TokenPayload:
    """JWT token payload."""
    sub: str  # Subject (user DN)
    uid: str  # User ID
    exp: datetime  # Expiration
    iat: datetime  # Issued at
    jti: str  # JWT ID (for revocation)
    type: str  # Token type (access/refresh)


@dataclass
class UserSession:
    """User session data stored in Redis."""
    user_dn: str
    uid: str
    display_name: str
    mail: Optional[str]
    groups: list[str]
    created_at: datetime
    last_activity: datetime
    token_jti: str


class AuthService:
    """
    Authentication service for Heracles.
    
    Handles JWT tokens and session management with Redis.
    """
    
    def __init__(self, redis: Optional[Redis] = None):
        self.secret_key = settings.SECRET_KEY
        self.redis = redis
        self.session_timeout = settings.SESSION_TIMEOUT
    
    def create_access_token(
        self,
        user_dn: str,
        uid: str,
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> tuple[str, str]:
        """
        Create JWT access token.
        
        Args:
            user_dn: User's LDAP DN
            uid: User's UID
            additional_claims: Optional extra claims to include
            
        Returns:
            Tuple of (token, jti)
        """
        now = datetime.now(timezone.utc)
        jti = secrets.token_urlsafe(32)
        
        payload = {
            "sub": user_dn,
            "uid": uid,
            "iat": now,
            "exp": now + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
            "jti": jti,
            "type": "access",
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        token = jwt.encode(payload, self.secret_key, algorithm=JWT_ALGORITHM)
        logger.debug("access_token_created", uid=uid, jti=jti)
        
        return token, jti
    
    def create_refresh_token(
        self,
        user_dn: str,
        uid: str,
    ) -> tuple[str, str]:
        """
        Create JWT refresh token.
        
        Args:
            user_dn: User's LDAP DN
            uid: User's UID
            
        Returns:
            Tuple of (token, jti)
        """
        now = datetime.now(timezone.utc)
        jti = secrets.token_urlsafe(32)
        
        payload = {
            "sub": user_dn,
            "uid": uid,
            "iat": now,
            "exp": now + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS),
            "jti": jti,
            "type": "refresh",
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=JWT_ALGORITHM)
        logger.debug("refresh_token_created", uid=uid, jti=jti)
        
        return token, jti
    
    def verify_token(self, token: str, token_type: str = "access") -> TokenPayload:
        """
        Verify and decode JWT token.
        
        Args:
            token: JWT token string
            token_type: Expected token type (access/refresh)
            
        Returns:
            TokenPayload with decoded data
            
        Raises:
            TokenError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[JWT_ALGORITHM],
            )
            
            if payload.get("type") != token_type:
                raise TokenError(f"Invalid token type: expected {token_type}")
            
            return TokenPayload(
                sub=payload["sub"],
                uid=payload["uid"],
                exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
                jti=payload["jti"],
                type=payload["type"],
            )
            
        except jwt.ExpiredSignatureError:
            logger.warning("token_expired")
            raise TokenError("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.warning("token_invalid", error=str(e))
            raise TokenError(f"Invalid token: {e}")
    
    async def create_session(
        self,
        user_dn: str,
        uid: str,
        display_name: str,
        mail: Optional[str],
        groups: list[str],
        token_jti: str,
    ) -> UserSession:
        """
        Create user session in Redis.
        
        Args:
            user_dn: User's LDAP DN
            uid: User's UID
            display_name: User's display name
            mail: User's email
            groups: List of group DNs
            token_jti: JWT token ID
            
        Returns:
            UserSession object
        """
        now = datetime.now(timezone.utc)
        session = UserSession(
            user_dn=user_dn,
            uid=uid,
            display_name=display_name,
            mail=mail,
            groups=groups,
            created_at=now,
            last_activity=now,
            token_jti=token_jti,
        )
        
        if self.redis:
            session_key = f"session:{token_jti}"
            session_data = {
                "user_dn": session.user_dn,
                "uid": session.uid,
                "display_name": session.display_name,
                "mail": session.mail or "",
                "groups": ",".join(session.groups),
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
            }
            
            await self.redis.hset(session_key, mapping=session_data)
            await self.redis.expire(session_key, self.session_timeout)
            
            # Also store a user -> session mapping for logout all
            user_sessions_key = f"user_sessions:{uid}"
            await self.redis.sadd(user_sessions_key, token_jti)
            await self.redis.expire(user_sessions_key, self.session_timeout)
            
            logger.info("session_created", uid=uid, jti=token_jti)
        
        return session
    
    async def get_session(self, token_jti: str) -> Optional[UserSession]:
        """
        Get session from Redis.
        
        Args:
            token_jti: JWT token ID
            
        Returns:
            UserSession if found, None otherwise
        """
        if not self.redis:
            return None
        
        session_key = f"session:{token_jti}"
        data = await self.redis.hgetall(session_key)
        
        if not data:
            return None
        
        # Decode bytes to strings if needed
        if isinstance(list(data.keys())[0], bytes):
            data = {k.decode(): v.decode() for k, v in data.items()}
        
        return UserSession(
            user_dn=data["user_dn"],
            uid=data["uid"],
            display_name=data["display_name"],
            mail=data["mail"] or None,
            groups=data["groups"].split(",") if data["groups"] else [],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_activity=datetime.fromisoformat(data["last_activity"]),
            token_jti=token_jti,
        )
    
    async def update_session_activity(self, token_jti: str) -> None:
        """Update session last activity timestamp."""
        if self.redis:
            session_key = f"session:{token_jti}"
            await self.redis.hset(
                session_key,
                "last_activity",
                datetime.now(timezone.utc).isoformat(),
            )
            await self.redis.expire(session_key, self.session_timeout)
    
    async def invalidate_session(self, token_jti: str) -> bool:
        """
        Invalidate a session (logout).
        
        Args:
            token_jti: JWT token ID
            
        Returns:
            True if session was found and invalidated
        """
        if not self.redis:
            return True
        
        session_key = f"session:{token_jti}"
        
        # Get session to find user
        data = await self.redis.hgetall(session_key)
        if data:
            uid = data.get(b"uid", data.get("uid", b"")).decode() if isinstance(data.get(b"uid", data.get("uid", "")), bytes) else data.get("uid", "")
            if uid:
                user_sessions_key = f"user_sessions:{uid}"
                await self.redis.srem(user_sessions_key, token_jti)
        
        result = await self.redis.delete(session_key)
        logger.info("session_invalidated", jti=token_jti)
        
        return result > 0
    
    async def invalidate_all_user_sessions(self, uid: str) -> int:
        """
        Invalidate all sessions for a user.
        
        Args:
            uid: User ID
            
        Returns:
            Number of sessions invalidated
        """
        if not self.redis:
            return 0
        
        user_sessions_key = f"user_sessions:{uid}"
        session_jtis = await self.redis.smembers(user_sessions_key)
        
        count = 0
        for jti in session_jtis:
            jti_str = jti.decode() if isinstance(jti, bytes) else jti
            session_key = f"session:{jti_str}"
            await self.redis.delete(session_key)
            count += 1
        
        await self.redis.delete(user_sessions_key)
        logger.info("all_sessions_invalidated", uid=uid, count=count)
        
        return count
    
    async def is_token_revoked(self, token_jti: str) -> bool:
        """
        Check if token has been revoked.
        
        A token is considered revoked if its session doesn't exist.
        """
        if not self.redis:
            return False
        
        session_key = f"session:{token_jti}"
        return not await self.redis.exists(session_key)


# Global auth service instance
auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get the global auth service instance."""
    global auth_service
    if auth_service is None:
        auth_service = AuthService()
    return auth_service


async def init_auth_service(redis: Redis) -> AuthService:
    """Initialize the global auth service with Redis."""
    global auth_service
    auth_service = AuthService(redis=redis)
    return auth_service
