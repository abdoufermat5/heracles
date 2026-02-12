"""
JWT Authentication Service
==========================

Handles JWT token creation, validation, and session management.
"""

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import structlog
from redis.asyncio import Redis

from heracles_api.config import settings

logger = structlog.get_logger(__name__)

# JWT Configuration - Defaults (can be overridden by DB config)
JWT_ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60
DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS = 7
DEFAULT_MAX_CONCURRENT_SESSIONS = 5


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
    mail: str | None
    groups: list[str]
    roles: list[str]
    created_at: datetime
    last_activity: datetime
    token_jti: str
    refresh_jti: str | None = None


class AuthService:
    """
    Authentication service for Heracles.

    Handles JWT tokens and session management with Redis.
    Token expiry and session settings are read from database configuration
    with fallback to environment/default values.
    """

    def __init__(self, redis: Redis | None = None):
        secrets_list = [s.strip() for s in settings.JWT_SECRETS.split(",") if s.strip()]
        if not secrets_list:
            secrets_list = [settings.SECRET_KEY]
        self._jwt_secrets = secrets_list
        self._jwt_active_secret = secrets_list[0]
        self._jwt_issuer = settings.JWT_ISSUER
        self._jwt_audience = settings.JWT_AUDIENCE
        self.redis = redis
        self.session_timeout = settings.SESSION_TIMEOUT
        # Cache for config values (updated via get_config methods)
        self._access_token_expire: int | None = None
        self._refresh_token_expire: int | None = None
        self._max_concurrent_sessions: int | None = None

    async def get_access_token_expire_minutes(self) -> int:
        """Get access token expiry in minutes from config with fallback."""
        from heracles_api.services.config import get_config_value

        value = await get_config_value(
            "session",
            "access_token_expire_minutes",
            default=DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES,
        )
        return int(value)

    async def get_refresh_token_expire_days(self) -> int:
        """Get refresh token expiry in days from config with fallback."""
        from heracles_api.services.config import get_config_value

        value = await get_config_value(
            "session",
            "refresh_token_expire_days",
            default=DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS,
        )
        return int(value)

    async def get_max_concurrent_sessions(self) -> int:
        """Get max concurrent sessions from config with fallback."""
        from heracles_api.services.config import get_config_value

        value = await get_config_value(
            "session",
            "max_concurrent_sessions",
            default=DEFAULT_MAX_CONCURRENT_SESSIONS,
        )
        return int(value)

    async def create_access_token(
        self,
        user_dn: str,
        uid: str,
        additional_claims: dict[str, Any] | None = None,
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
        now = datetime.now(UTC)
        jti = secrets.token_urlsafe(32)

        # Get expiry from config
        expire_minutes = await self.get_access_token_expire_minutes()

        payload = {
            "sub": user_dn,
            "uid": uid,
            "iat": now,
            "exp": now + timedelta(minutes=expire_minutes),
            "jti": jti,
            "type": "access",
            "iss": self._jwt_issuer,
            "aud": self._jwt_audience,
        }

        if additional_claims:
            payload.update(additional_claims)

        token = jwt.encode(payload, self._jwt_active_secret, algorithm=JWT_ALGORITHM)
        logger.debug("access_token_created", uid=uid, jti=jti, expires_in_minutes=expire_minutes)

        return token, jti

    async def create_refresh_token(
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
        now = datetime.now(UTC)
        jti = secrets.token_urlsafe(32)

        # Get expiry from config
        expire_days = await self.get_refresh_token_expire_days()

        payload = {
            "sub": user_dn,
            "uid": uid,
            "iat": now,
            "exp": now + timedelta(days=expire_days),
            "jti": jti,
            "type": "refresh",
            "iss": self._jwt_issuer,
            "aud": self._jwt_audience,
        }

        token = jwt.encode(payload, self._jwt_active_secret, algorithm=JWT_ALGORITHM)
        logger.debug("refresh_token_created", uid=uid, jti=jti, expires_in_days=expire_days)

        return token, jti

    async def get_cookie_settings(self, token_type: str = "access") -> dict[str, Any]:
        """
        Get cookie settings for a token type.

        Args:
            token_type: access or refresh

        Returns:
            Dict of cookie settings (httponly, secure, etc.)
        """
        is_access = token_type == "access"

        if is_access:
            expire_minutes = await self.get_access_token_expire_minutes()
            max_age = expire_minutes * 60
        else:
            expire_days = await self.get_refresh_token_expire_days()
            max_age = expire_days * 24 * 60 * 60

        return {
            "key": "access_token" if is_access else "refresh_token",
            "httponly": True,
            "secure": settings.COOKIE_SECURE,
            "samesite": settings.COOKIE_SAMESITE,
            "domain": settings.COOKIE_DOMAIN,
            "max_age": max_age,
            "path": "/" if is_access else "/api/v1/auth/refresh",
        }

    async def get_csrf_cookie_settings(self) -> dict[str, Any]:
        """Get CSRF cookie settings."""
        expire_minutes = await self.get_access_token_expire_minutes()
        return {
            "key": "csrf_token",
            "httponly": False,
            "secure": settings.COOKIE_SECURE,
            "samesite": settings.COOKIE_SAMESITE,
            "domain": settings.COOKIE_DOMAIN,
            "max_age": expire_minutes * 60,
            "path": "/",
        }

    def create_csrf_token(self) -> str:
        """Create a CSRF token for double-submit protection."""
        return secrets.token_urlsafe(32)

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
            payload = None
            for secret in self._jwt_secrets:
                try:
                    payload = jwt.decode(
                        token,
                        secret,
                        algorithms=[JWT_ALGORITHM],
                        issuer=self._jwt_issuer,
                        audience=self._jwt_audience,
                    )
                    break
                except jwt.InvalidSignatureError:
                    continue
            if payload is None:
                raise jwt.InvalidTokenError("Signature verification failed")

            if payload.get("type") != token_type:
                raise TokenError(f"Invalid token type: expected {token_type}")

            return TokenPayload(
                sub=payload["sub"],
                uid=payload["uid"],
                exp=datetime.fromtimestamp(payload["exp"], tz=UTC),
                iat=datetime.fromtimestamp(payload["iat"], tz=UTC),
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
        mail: str | None,
        groups: list[str],
        roles: list[str],
        token_jti: str,
        refresh_jti: str | None,
        refresh_ttl_seconds: int,
    ) -> UserSession:
        """
        Create user session in Redis.

        Args:
            user_dn: User's LDAP DN
            uid: User's UID
            display_name: User's display name
            mail: User's email
            groups: List of group DNs
            roles: List of role DNs
            token_jti: JWT token ID

        Returns:
            UserSession object
        """
        now = datetime.now(UTC)
        session = UserSession(
            user_dn=user_dn,
            uid=uid,
            display_name=display_name,
            mail=mail,
            groups=groups,
            roles=roles,
            created_at=now,
            last_activity=now,
            token_jti=token_jti,
            refresh_jti=refresh_jti,
        )

        if self.redis:
            session_key = f"session:{token_jti}"
            session_data = {
                "user_dn": session.user_dn,
                "uid": session.uid,
                "display_name": session.display_name,
                "mail": session.mail or "",
                # Use pipe separator since DNs contain commas
                "groups": "|".join(session.groups),
                "roles": "|".join(session.roles),
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "refresh_jti": session.refresh_jti or "",
            }

            await self.redis.hset(session_key, mapping=session_data)
            await self.redis.expire(session_key, self.session_timeout)

            # Store refresh token jti mapping for single-use rotation
            if refresh_jti:
                refresh_key = f"refresh:{refresh_jti}"
                await self.redis.set(refresh_key, token_jti, ex=refresh_ttl_seconds)

            # Also store a user -> session mapping for logout all and limits
            user_sessions_key = f"user_sessions:{uid}"
            created_ts = int(now.timestamp())
            await self.redis.zadd(user_sessions_key, {token_jti: created_ts})
            await self.redis.expire(user_sessions_key, self.session_timeout)

            max_sessions = await self.get_max_concurrent_sessions()
            if max_sessions > 0:
                current_count = await self.redis.zcard(user_sessions_key)
                if current_count > max_sessions:
                    oldest = await self.redis.zrange(user_sessions_key, 0, 0)
                    if oldest:
                        oldest_jti = oldest[0].decode() if isinstance(oldest[0], bytes) else oldest[0]
                        await self.invalidate_session(oldest_jti)

            logger.info("session_created", uid=uid, jti=token_jti)

        return session

    async def get_session(self, token_jti: str) -> UserSession | None:
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
            # Use pipe separator since DNs contain commas
            groups=data["groups"].split("|") if data.get("groups") else [],
            roles=data["roles"].split("|") if data.get("roles") else [],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_activity=datetime.fromisoformat(data["last_activity"]),
            token_jti=token_jti,
            refresh_jti=data.get("refresh_jti") or None,
        )

    async def update_session_activity(self, token_jti: str) -> None:
        """Update session last activity timestamp."""
        if self.redis:
            session_key = f"session:{token_jti}"
            await self.redis.hset(
                session_key,
                "last_activity",
                datetime.now(UTC).isoformat(),
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
            uid = (
                data.get(b"uid", data.get("uid", b"")).decode()
                if isinstance(data.get(b"uid", data.get("uid", "")), bytes)
                else data.get("uid", "")
            )
            if uid:
                user_sessions_key = f"user_sessions:{uid}"
                await self.redis.zrem(user_sessions_key, token_jti)
            refresh_jti = data.get(b"refresh_jti", data.get("refresh_jti", b""))
            refresh_jti = refresh_jti.decode() if isinstance(refresh_jti, bytes) else refresh_jti
            if refresh_jti:
                await self.redis.delete(f"refresh:{refresh_jti}")

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
        session_jtis = await self.redis.zrange(user_sessions_key, 0, -1)

        count = 0
        for jti in session_jtis:
            jti_str = jti.decode() if isinstance(jti, bytes) else jti
            session_key = f"session:{jti_str}"
            data = await self.redis.hgetall(session_key)
            if data:
                refresh_jti = data.get(b"refresh_jti", data.get("refresh_jti", b""))
                refresh_jti = refresh_jti.decode() if isinstance(refresh_jti, bytes) else refresh_jti
                if refresh_jti:
                    await self.redis.delete(f"refresh:{refresh_jti}")
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

    async def use_refresh_token(self, refresh_jti: str) -> str | None:
        """Consume a refresh token jti for rotation; returns access jti if valid."""
        if not self.redis:
            return None
        refresh_key = f"refresh:{refresh_jti}"
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.get(refresh_key)
            pipe.delete(refresh_key)
            result = await pipe.execute()
        access_jti = result[0]
        if isinstance(access_jti, bytes):
            access_jti = access_jti.decode()
        return access_jti


# Global auth service instance
auth_service: AuthService | None = None


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
