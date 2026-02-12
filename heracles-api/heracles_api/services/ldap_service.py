"""
LDAP Service Layer
==================

Provides LDAP operations for the Heracles API.
This service uses heracles-core (Rust) for all LDAP operations.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import heracles_core
import structlog

from heracles_api.config import settings

logger = structlog.get_logger(__name__)


class LdapError(Exception):
    """Base exception for LDAP errors."""

    pass


class LdapConnectionError(LdapError):
    """Failed to connect to LDAP server."""

    pass


class LdapAuthenticationError(LdapError):
    """Failed to authenticate with LDAP."""

    pass


class LdapNotFoundError(LdapError):
    """Entry not found in LDAP."""

    pass


class LdapOperationError(LdapError):
    """LDAP operation failed."""

    pass


class SearchScope(StrEnum):
    """LDAP search scope."""

    BASE = "base"
    ONELEVEL = "onelevel"
    SUBTREE = "subtree"


@dataclass
class LdapEntry:
    """Represents an LDAP entry."""

    dn: str
    attributes: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Get attribute value."""
        return self.attributes.get(key, default)

    def get_first(self, key: str, default: Any = None) -> Any:
        """Get first value of multi-valued attribute."""
        values = self.attributes.get(key, [])
        if isinstance(values, list) and values:
            return values[0]
        return values if values else default

    @classmethod
    def from_core(cls, entry: heracles_core.LdapEntry) -> "LdapEntry":
        """Create from heracles_core.LdapEntry."""
        attrs = {}
        for key, values in entry.attributes.items():
            if len(values) == 1:
                attrs[key] = values[0]
            else:
                attrs[key] = list(values)
        return cls(dn=entry.dn, attributes=attrs)


class LdapService:
    """
    LDAP Service for Heracles API.

    Uses heracles-core (Rust) for all LDAP operations including:
    - Connection management with pooling
    - Search, add, modify, delete operations
    - Password hashing (Argon2, bcrypt, SSHA, etc.)
    - DN escaping and manipulation
    """

    def __init__(
        self,
        uri: str = None,
        base_dn: str = None,
        bind_dn: str = None,
        bind_password: str = None,
        use_tls: bool = False,
    ):
        self.uri = uri or settings.LDAP_URI
        self.base_dn = base_dn or settings.LDAP_BASE_DN
        self.bind_dn = bind_dn or settings.LDAP_BIND_DN
        self.bind_password = bind_password or settings.LDAP_BIND_PASSWORD
        self.use_tls = use_tls or settings.LDAP_USE_TLS

        self._connection: heracles_core.LdapConnection | None = None

    async def connect(self) -> None:
        """Initialize LDAP connection using heracles-core."""
        try:
            self._connection = heracles_core.LdapConnection(
                uri=self.uri,
                base_dn=self.base_dn,
                bind_dn=self.bind_dn,
                bind_password=self.bind_password,
                use_tls=self.use_tls,
            )
            await self._connection.connect()
            logger.info("ldap_service_connected", uri=self.uri, base_dn=self.base_dn)
        except Exception as e:
            logger.error("ldap_connection_failed", error=str(e))
            raise LdapConnectionError(f"Failed to connect to LDAP: {e}")

    async def disconnect(self) -> None:
        """Close LDAP connection."""
        if self._connection:
            try:
                await self._connection.disconnect()
            except Exception:
                pass
            self._connection = None
            logger.info("ldap_service_disconnected")

    def _ensure_connected(self) -> heracles_core.LdapConnection:
        """Ensure we have a connection."""
        if self._connection is None:
            raise LdapConnectionError("Not connected to LDAP server")
        return self._connection

    async def authenticate(self, username: str, password: str) -> LdapEntry | None:
        """
        Authenticate user with LDAP credentials.

        Args:
            username: User's uid or full DN
            password: User's password

        Returns:
            LdapEntry if authentication successful, None otherwise
        """
        conn = self._ensure_connected()

        # Determine user DN
        if "=" in username:
            user_dn = username
        else:
            # Search for user by uid
            try:
                filter_str = f"(uid={heracles_core.escape_filter_value(username)})"
                entries = await conn.search(
                    base=self.base_dn,
                    filter=filter_str,
                    scope="subtree",
                    attributes=["*"],
                )

                if not entries:
                    logger.warning("ldap_user_not_found", username=username)
                    return None

                user_dn = entries[0].dn
                user_entry = LdapEntry.from_core(entries[0])

            except Exception as e:
                logger.error("ldap_search_error", error=str(e))
                raise LdapOperationError(f"Failed to search for user: {e}")

        # Try to authenticate
        try:
            success = await conn.authenticate(user_dn, password)

            if success:
                # Get user entry if we don't have it
                if "=" in username:
                    user_entry = await self.get_by_dn(user_dn)

                logger.info("ldap_authentication_success", user_dn=user_dn)
                return user_entry
            else:
                logger.warning("ldap_authentication_failed", user_dn=user_dn)
                return None

        except Exception as e:
            logger.error("ldap_authentication_error", error=str(e))
            raise LdapAuthenticationError(f"Authentication error: {e}")

    async def search(
        self,
        search_base: str = None,
        search_filter: str = "(objectClass=*)",
        scope: SearchScope | str = SearchScope.SUBTREE,
        attributes: list[str] = None,
        size_limit: int = 0,
    ) -> list[LdapEntry]:
        """
        Search LDAP directory.

        Args:
            search_base: Base DN for search (defaults to configured base)
            search_filter: LDAP filter string
            scope: Search scope (SearchScope enum or string: 'base', 'onelevel', 'subtree')
            attributes: List of attributes to return (None = all)
            size_limit: Maximum entries to return (0 = unlimited)

        Returns:
            List of LdapEntry objects
        """
        conn = self._ensure_connected()

        try:
            base = search_base or self.base_dn
            # Handle both enum and string for scope
            scope_value = scope.value if isinstance(scope, SearchScope) else scope
            entries = await conn.search(
                base=base,
                filter=search_filter,
                scope=scope_value,
                attributes=attributes,
                size_limit=size_limit,
            )

            return [LdapEntry.from_core(e) for e in entries]

        except Exception as e:
            logger.error("ldap_search_error", error=str(e))
            raise LdapOperationError(f"Search failed: {e}")

    async def get_by_dn(self, dn: str, attributes: list[str] = None) -> LdapEntry | None:
        """Get entry by DN. Returns None if entry doesn't exist."""
        conn = self._ensure_connected()

        try:
            entry = await conn.get_by_dn(dn, attributes)
            return LdapEntry.from_core(entry) if entry else None
        except Exception as e:
            error_str = str(e)
            # LDAP error 32 (noSuchObject) means the entry doesn't exist
            # This is expected when checking if an entry exists before creating it
            if "rc=32" in error_str or "noSuchObject" in error_str:
                return None
            logger.error("ldap_get_by_dn_error", dn=dn, error=error_str)
            raise LdapOperationError(f"Failed to get entry: {e}")

    async def add(self, dn: str, object_classes: list[str], attributes: dict[str, Any]) -> bool:
        """
        Add new LDAP entry.

        Args:
            dn: Distinguished name for new entry
            object_classes: List of object classes
            attributes: Entry attributes

        Returns:
            True if successful
        """
        conn = self._ensure_connected()

        try:
            # Build attributes dict with objectClass
            attrs: dict[str, list[str]] = {"objectClass": object_classes}

            for key, value in attributes.items():
                if isinstance(value, list):
                    attrs[key] = [str(v) for v in value]
                else:
                    attrs[key] = [str(value)]

            result = await conn.add(dn, attrs)
            logger.info("ldap_entry_added", dn=dn)
            return result

        except Exception as e:
            logger.error("ldap_add_error", dn=dn, error=str(e))
            raise LdapOperationError(f"Failed to add entry: {e}")

    async def modify(self, dn: str, changes: dict[str, tuple[str, Any]]) -> bool:
        """
        Modify LDAP entry.

        Args:
            dn: Entry DN to modify
            changes: Dict of {attribute: (operation, value)}
                     operation can be: "replace", "add", "delete"

        Returns:
            True if successful
        """
        conn = self._ensure_connected()

        try:
            # Convert to list of tuples format
            modifications = []
            for attr, (op, values) in changes.items():
                if isinstance(values, list):
                    vals = [str(v) for v in values]
                elif values is None:
                    vals = []
                else:
                    vals = [str(values)]
                modifications.append((op, attr, vals))

            result = await conn.modify(dn, modifications)
            logger.info("ldap_entry_modified", dn=dn)
            return result

        except Exception as e:
            if "not found" in str(e).lower() or "no such object" in str(e).lower():
                raise LdapNotFoundError(f"Entry not found: {dn}")
            logger.error("ldap_modify_error", dn=dn, error=str(e))
            raise LdapOperationError(f"Failed to modify entry: {e}")

    async def delete(self, dn: str) -> bool:
        """Delete LDAP entry."""
        conn = self._ensure_connected()

        try:
            result = await conn.delete(dn)
            logger.info("ldap_entry_deleted", dn=dn)
            return result

        except Exception as e:
            if "not found" in str(e).lower() or "no such object" in str(e).lower():
                raise LdapNotFoundError(f"Entry not found: {dn}")
            logger.error("ldap_delete_error", dn=dn, error=str(e))
            raise LdapOperationError(f"Failed to delete entry: {e}")

    async def set_password(self, dn: str, password: str, method: str = "argon2") -> bool:
        """
        Set password for LDAP entry.

        Args:
            dn: Entry DN
            password: New password
            method: Hash method (ssha, argon2, bcrypt, sha256, sha512, md5, etc.)

        Returns:
            True if successful
        """
        hashed = self._hash_password(password, method)
        return await self.modify(dn, {"userPassword": ("replace", [hashed])})

    def _hash_password(self, password: str, method: str = "argon2") -> str:
        """Hash password for LDAP storage using heracles-core.

        Supported methods: argon2 (default), ssha512, ssha256
        """
        allowed = {"argon2", "ssha512", "ssha256"}
        method_normalized = method.lower()
        if method_normalized not in allowed:
            raise LdapOperationError(f"Unsupported password hash method: {method}")
        return heracles_core.hash_password(password, method_normalized)

    @staticmethod
    def _escape_filter(value: str) -> str:
        """Escape special characters for LDAP filter using heracles-core."""
        return heracles_core.escape_filter_value(value)

    @staticmethod
    def _escape_dn(value: str) -> str:
        """Escape special characters for DN value using heracles-core."""
        return heracles_core.escape_dn_value(value)


# Global LDAP service instance
ldap_service: LdapService | None = None


def get_ldap_service() -> LdapService:
    """Get the global LDAP service instance."""
    global ldap_service
    if ldap_service is None:
        ldap_service = LdapService()
    return ldap_service


async def init_ldap_service() -> LdapService:
    """Initialize the global LDAP service."""
    global ldap_service
    ldap_service = LdapService()
    await ldap_service.connect()
    return ldap_service


async def close_ldap_service() -> None:
    """Close the global LDAP service."""
    global ldap_service
    if ldap_service:
        await ldap_service.disconnect()
        ldap_service = None
