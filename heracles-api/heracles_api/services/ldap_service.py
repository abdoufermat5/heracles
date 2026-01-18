"""
LDAP Service Layer
==================

Provides LDAP operations for the Heracles API.
This service wraps ldap3 operations and provides a clean interface.
"""

import asyncio
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import os
import base64
import secrets

import structlog
from ldap3 import Server, Connection, ALL, SUBTREE, MODIFY_REPLACE, MODIFY_ADD, MODIFY_DELETE
from ldap3.core.exceptions import LDAPException, LDAPBindError, LDAPInvalidCredentialsResult

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


class SearchScope(str, Enum):
    """LDAP search scope."""
    BASE = "base"
    ONELEVEL = "onelevel" 
    SUBTREE = "subtree"


@dataclass
class LdapEntry:
    """Represents an LDAP entry."""
    dn: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get attribute value."""
        return self.attributes.get(key, default)
    
    def get_first(self, key: str, default: Any = None) -> Any:
        """Get first value of multi-valued attribute."""
        values = self.attributes.get(key, [])
        if isinstance(values, list) and values:
            return values[0]
        return values if values else default


class LdapService:
    """
    LDAP Service for Heracles API.
    
    Provides a clean interface for LDAP operations.
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
        
        self._server: Optional[Server] = None
        self._admin_conn: Optional[Connection] = None
        
    def _get_server(self) -> Server:
        """Get or create LDAP server instance."""
        if self._server is None:
            self._server = Server(self.uri, get_info=ALL)
        return self._server
    
    def _get_admin_connection(self) -> Connection:
        """Get admin connection (creates new if needed)."""
        if self._admin_conn is None or not self._admin_conn.bound:
            try:
                self._admin_conn = Connection(
                    self._get_server(),
                    user=self.bind_dn,
                    password=self.bind_password,
                    auto_bind=True,
                )
                logger.info("ldap_admin_connected", bind_dn=self.bind_dn)
            except LDAPException as e:
                logger.error("ldap_admin_connection_failed", error=str(e))
                raise LdapConnectionError(f"Failed to connect as admin: {e}")
        return self._admin_conn
    
    async def connect(self) -> None:
        """Initialize LDAP connection."""
        # Run in thread pool since ldap3 is synchronous
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._get_admin_connection)
        logger.info("ldap_service_connected", uri=self.uri, base_dn=self.base_dn)
    
    async def disconnect(self) -> None:
        """Close LDAP connection."""
        if self._admin_conn:
            self._admin_conn.unbind()
            self._admin_conn = None
            logger.info("ldap_service_disconnected")
    
    async def authenticate(self, username: str, password: str) -> Optional[LdapEntry]:
        """
        Authenticate user with LDAP credentials.
        
        Args:
            username: User's uid or full DN
            password: User's password
            
        Returns:
            LdapEntry if authentication successful, None otherwise
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self._authenticate_sync, 
            username, 
            password
        )
    
    def _authenticate_sync(self, username: str, password: str) -> Optional[LdapEntry]:
        """Synchronous authentication."""
        # First, find the user's DN
        user_dn = None
        user_entry = None
        
        # Check if username is already a DN
        if "=" in username:
            user_dn = username
        else:
            # Search for user by uid
            try:
                conn = self._get_admin_connection()
                search_filter = f"(uid={self._escape_filter(username)})"
                conn.search(
                    search_base=self.base_dn,
                    search_filter=search_filter,
                    search_scope=SUBTREE,
                    attributes=["*"],
                )
                
                if conn.entries:
                    user_dn = conn.entries[0].entry_dn
                    user_entry = self._entry_to_ldap_entry(conn.entries[0])
                else:
                    logger.warning("ldap_user_not_found", username=username)
                    return None
                    
            except LDAPException as e:
                logger.error("ldap_search_error", error=str(e))
                raise LdapOperationError(f"Failed to search for user: {e}")
        
        # Now try to bind as the user
        try:
            user_conn = Connection(
                self._get_server(),
                user=user_dn,
                password=password,
                auto_bind=True,
            )
            user_conn.unbind()
            
            # If we didn't fetch attributes yet, do it now
            if user_entry is None:
                user_entry = self._search_by_dn_sync(user_dn)
            
            logger.info("ldap_authentication_success", user_dn=user_dn)
            return user_entry
            
        except (LDAPBindError, LDAPInvalidCredentialsResult):
            logger.warning("ldap_authentication_failed", user_dn=user_dn)
            return None
        except LDAPException as e:
            logger.error("ldap_authentication_error", error=str(e))
            raise LdapAuthenticationError(f"Authentication error: {e}")
    
    async def search(
        self,
        search_base: str = None,
        search_filter: str = "(objectClass=*)",
        scope: SearchScope = SearchScope.SUBTREE,
        attributes: List[str] = None,
        size_limit: int = 0,
    ) -> List[LdapEntry]:
        """
        Search LDAP directory.
        
        Args:
            search_base: Base DN for search (defaults to configured base)
            search_filter: LDAP filter string
            scope: Search scope
            attributes: List of attributes to return (None = all)
            size_limit: Maximum entries to return (0 = unlimited)
            
        Returns:
            List of LdapEntry objects
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._search_sync,
            search_base or self.base_dn,
            search_filter,
            scope,
            attributes or ["*"],
            size_limit,
        )
    
    def _search_sync(
        self,
        search_base: str,
        search_filter: str,
        scope: SearchScope,
        attributes: List[str],
        size_limit: int,
    ) -> List[LdapEntry]:
        """Synchronous search."""
        try:
            conn = self._get_admin_connection()
            
            ldap_scope = SUBTREE
            if scope == SearchScope.BASE:
                from ldap3 import BASE
                ldap_scope = BASE
            elif scope == SearchScope.ONELEVEL:
                from ldap3 import LEVEL
                ldap_scope = LEVEL
            
            conn.search(
                search_base=search_base,
                search_filter=search_filter,
                search_scope=ldap_scope,
                attributes=attributes,
                size_limit=size_limit,
            )
            
            return [self._entry_to_ldap_entry(entry) for entry in conn.entries]
            
        except LDAPException as e:
            logger.error("ldap_search_error", error=str(e))
            raise LdapOperationError(f"Search failed: {e}")
    
    async def get_by_dn(self, dn: str, attributes: List[str] = None) -> Optional[LdapEntry]:
        """Get entry by DN."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._search_by_dn_sync, dn, attributes)
    
    def _search_by_dn_sync(self, dn: str, attributes: List[str] = None) -> Optional[LdapEntry]:
        """Synchronous DN lookup."""
        try:
            conn = self._get_admin_connection()
            from ldap3 import BASE
            conn.search(
                search_base=dn,
                search_filter="(objectClass=*)",
                search_scope=BASE,
                attributes=attributes or ["*"],
            )
            
            if conn.entries:
                return self._entry_to_ldap_entry(conn.entries[0])
            return None
            
        except LDAPException as e:
            logger.error("ldap_get_by_dn_error", dn=dn, error=str(e))
            raise LdapOperationError(f"Failed to get entry: {e}")
    
    async def add(self, dn: str, object_classes: List[str], attributes: Dict[str, Any]) -> bool:
        """
        Add new LDAP entry.
        
        Args:
            dn: Distinguished name for new entry
            object_classes: List of object classes
            attributes: Entry attributes
            
        Returns:
            True if successful
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._add_sync,
            dn,
            object_classes,
            attributes,
        )
    
    def _add_sync(self, dn: str, object_classes: List[str], attributes: Dict[str, Any]) -> bool:
        """Synchronous add."""
        try:
            conn = self._get_admin_connection()
            result = conn.add(dn, object_classes, attributes)
            
            if result:
                logger.info("ldap_entry_added", dn=dn)
            else:
                logger.error("ldap_add_failed", dn=dn, result=conn.result)
                raise LdapOperationError(f"Failed to add entry: {conn.result}")
            
            return result
            
        except LDAPException as e:
            logger.error("ldap_add_error", dn=dn, error=str(e))
            raise LdapOperationError(f"Failed to add entry: {e}")
    
    async def modify(self, dn: str, changes: Dict[str, Tuple[str, Any]]) -> bool:
        """
        Modify LDAP entry.
        
        Args:
            dn: Entry DN to modify
            changes: Dict of {attribute: (operation, value)}
                     operation can be: MODIFY_REPLACE, MODIFY_ADD, MODIFY_DELETE
            
        Returns:
            True if successful
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._modify_sync, dn, changes)
    
    def _modify_sync(self, dn: str, changes: Dict[str, Tuple[str, Any]]) -> bool:
        """Synchronous modify."""
        try:
            conn = self._get_admin_connection()
            result = conn.modify(dn, changes)
            
            if result:
                logger.info("ldap_entry_modified", dn=dn)
            else:
                logger.error("ldap_modify_failed", dn=dn, result=conn.result)
                raise LdapOperationError(f"Failed to modify entry: {conn.result}")
            
            return result
            
        except LDAPException as e:
            logger.error("ldap_modify_error", dn=dn, error=str(e))
            raise LdapOperationError(f"Failed to modify entry: {e}")
    
    async def delete(self, dn: str) -> bool:
        """Delete LDAP entry."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._delete_sync, dn)
    
    def _delete_sync(self, dn: str) -> bool:
        """Synchronous delete."""
        try:
            conn = self._get_admin_connection()
            result = conn.delete(dn)
            
            if result:
                logger.info("ldap_entry_deleted", dn=dn)
            else:
                logger.error("ldap_delete_failed", dn=dn, result=conn.result)
                raise LdapOperationError(f"Failed to delete entry: {conn.result}")
            
            return result
            
        except LDAPException as e:
            logger.error("ldap_delete_error", dn=dn, error=str(e))
            raise LdapOperationError(f"Failed to delete entry: {e}")
    
    async def set_password(self, dn: str, password: str, method: str = "ssha") -> bool:
        """
        Set password for LDAP entry.
        
        Args:
            dn: Entry DN
            password: New password
            method: Hash method (ssha, sha, md5, plain)
            
        Returns:
            True if successful
        """
        hashed = self._hash_password(password, method)
        return await self.modify(dn, {"userPassword": [(MODIFY_REPLACE, [hashed])]})
    
    def _hash_password(self, password: str, method: str = "ssha") -> str:
        """Hash password for LDAP storage."""
        if method == "ssha":
            salt = secrets.token_bytes(16)
            h = hashlib.sha1(password.encode() + salt).digest()
            return "{SSHA}" + base64.b64encode(h + salt).decode()
        elif method == "sha":
            h = hashlib.sha1(password.encode()).digest()
            return "{SHA}" + base64.b64encode(h).decode()
        elif method == "md5":
            h = hashlib.md5(password.encode()).digest()
            return "{MD5}" + base64.b64encode(h).decode()
        else:
            return password
    
    @staticmethod
    def _escape_filter(value: str) -> str:
        """Escape special characters for LDAP filter."""
        escaped = value
        escaped = escaped.replace("\\", "\\5c")
        escaped = escaped.replace("*", "\\2a")
        escaped = escaped.replace("(", "\\28")
        escaped = escaped.replace(")", "\\29")
        escaped = escaped.replace("\x00", "\\00")
        return escaped
    
    @staticmethod
    def _entry_to_ldap_entry(entry) -> LdapEntry:
        """Convert ldap3 entry to LdapEntry."""
        attrs = {}
        for attr_name in entry.entry_attributes:
            values = entry[attr_name].values
            if len(values) == 1:
                attrs[attr_name] = values[0]
            else:
                attrs[attr_name] = list(values)
        
        return LdapEntry(
            dn=entry.entry_dn,
            attributes=attrs,
        )


# Global LDAP service instance
ldap_service: Optional[LdapService] = None


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
