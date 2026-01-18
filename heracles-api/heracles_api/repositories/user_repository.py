"""
User Repository
===============

Data access layer for user LDAP operations.
"""

from typing import Optional, List
from dataclasses import dataclass

from ldap3 import MODIFY_REPLACE, MODIFY_DELETE

from heracles_api.services.ldap_service import LdapService, LdapEntry, LdapOperationError
from heracles_api.schemas.user import UserCreate, UserUpdate, UserResponse
from heracles_api.config import settings

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class UserSearchResult:
    """User search result with pagination info."""
    users: List[LdapEntry]
    total: int


class UserRepository:
    """
    Repository for user LDAP operations.
    
    Provides a clean interface for CRUD operations on users.
    """
    
    OBJECT_CLASSES = ["inetOrgPerson", "organizationalPerson", "person"]
    USER_ATTRIBUTES = [
        "uid", "cn", "sn", "givenName", "mail", 
        "telephoneNumber", "title", "description",
        "createTimestamp", "modifyTimestamp",
    ]
    # Include userPassword for lock status checks
    USER_ATTRIBUTES_WITH_PASSWORD = USER_ATTRIBUTES + ["userPassword"]
    LOCK_PREFIX = "{LOCKED}"  # Password prefix for locked accounts
    
    def __init__(self, ldap: LdapService):
        self.ldap = ldap
        self.base_dn = settings.LDAP_BASE_DN
    
    def _build_user_dn(self, uid: str, ou: str = "people") -> str:
        """Build user DN from UID."""
        return f"uid={uid},ou={ou},{self.base_dn}"
    
    def _entry_to_dict(self, entry: LdapEntry) -> dict:
        """Convert LDAP entry to dictionary."""
        return {
            "dn": entry.dn,
            "uid": entry.get_first("uid", ""),
            "cn": entry.get_first("cn", ""),
            "sn": entry.get_first("sn", ""),
            "givenName": entry.get_first("givenName"),
            "mail": entry.get_first("mail"),
            "telephoneNumber": entry.get_first("telephoneNumber"),
            "title": entry.get_first("title"),
            "description": entry.get_first("description"),
        }
    
    async def find_by_uid(self, uid: str) -> Optional[LdapEntry]:
        """Find user by UID."""
        entries = await self.ldap.search(
            search_filter=f"(&(objectClass=inetOrgPerson)(uid={self.ldap._escape_filter(uid)}))",
            attributes=self.USER_ATTRIBUTES,
        )
        return entries[0] if entries else None
    
    async def find_by_uid_with_password(self, uid: str) -> Optional[LdapEntry]:
        """Find user by UID including password attribute (for lock checks)."""
        entries = await self.ldap.search(
            search_filter=f"(&(objectClass=inetOrgPerson)(uid={self.ldap._escape_filter(uid)}))",
            attributes=self.USER_ATTRIBUTES_WITH_PASSWORD,
        )
        return entries[0] if entries else None
    
    async def find_by_dn(self, dn: str) -> Optional[LdapEntry]:
        """Find user by DN."""
        return await self.ldap.get_by_dn(dn, attributes=self.USER_ATTRIBUTES)
    
    async def find_by_mail(self, mail: str) -> Optional[LdapEntry]:
        """Find user by email."""
        entries = await self.ldap.search(
            search_filter=f"(&(objectClass=inetOrgPerson)(mail={self.ldap._escape_filter(mail)}))",
            attributes=self.USER_ATTRIBUTES,
        )
        return entries[0] if entries else None
    
    async def exists(self, uid: str) -> bool:
        """Check if user exists."""
        entries = await self.ldap.search(
            search_filter=f"(uid={self.ldap._escape_filter(uid)})",
            attributes=["uid"],
        )
        return len(entries) > 0
    
    async def search(
        self,
        search_term: Optional[str] = None,
        ou: Optional[str] = None,
        limit: int = 0,
    ) -> UserSearchResult:
        """
        Search users with optional filtering.
        
        Args:
            search_term: Search in uid, cn, mail
            ou: Filter by organizational unit
            limit: Maximum results (0 = unlimited)
        """
        # Build filter
        base_filter = "(objectClass=inetOrgPerson)"
        
        if search_term:
            escaped = self.ldap._escape_filter(search_term)
            search_filter = f"(&{base_filter}(|(uid=*{escaped}*)(cn=*{escaped}*)(mail=*{escaped}*)))"
        else:
            search_filter = base_filter
        
        # Determine search base
        if ou:
            search_base = f"ou={ou},{self.base_dn}"
        else:
            search_base = self.base_dn
        
        entries = await self.ldap.search(
            search_base=search_base,
            search_filter=search_filter,
            attributes=self.USER_ATTRIBUTES,
            size_limit=limit,
        )
        
        return UserSearchResult(users=entries, total=len(entries))
    
    async def create(self, user: UserCreate) -> LdapEntry:
        """
        Create a new user.
        
        Args:
            user: User creation data
            
        Returns:
            Created user entry
            
        Raises:
            LdapOperationError: If creation fails
        """
        user_dn = self._build_user_dn(user.uid, user.ou)
        
        # Build attributes
        attrs = {
            "cn": user.cn,
            "sn": user.sn,
            "userPassword": self.ldap._hash_password(user.password, settings.PASSWORD_HASH_METHOD),
        }
        
        if user.given_name:
            attrs["givenName"] = user.given_name
        if user.mail:
            attrs["mail"] = user.mail
        if user.telephone_number:
            attrs["telephoneNumber"] = user.telephone_number
        if user.title:
            attrs["title"] = user.title
        if user.description:
            attrs["description"] = user.description
        
        await self.ldap.add(
            dn=user_dn,
            object_classes=self.OBJECT_CLASSES,
            attributes=attrs,
        )
        
        logger.info("user_created", uid=user.uid, dn=user_dn)
        
        # Return the created entry
        return await self.find_by_dn(user_dn)
    
    async def update(self, uid: str, updates: UserUpdate) -> Optional[LdapEntry]:
        """
        Update user attributes.
        
        Args:
            uid: User UID
            updates: Fields to update
            
        Returns:
            Updated user entry or None if not found
        """
        entry = await self.find_by_uid(uid)
        if not entry:
            return None
        
        # Build changes
        changes = {}
        update_data = updates.model_dump(exclude_unset=True, by_alias=True)
        
        attr_mapping = {
            "cn": "cn",
            "sn": "sn",
            "givenName": "givenName",
            "mail": "mail",
            "telephoneNumber": "telephoneNumber",
            "title": "title",
            "description": "description",
        }
        
        for field, ldap_attr in attr_mapping.items():
            if field in update_data:
                value = update_data[field]
                if value is not None:
                    changes[ldap_attr] = [(MODIFY_REPLACE, [value])]
                else:
                    changes[ldap_attr] = [(MODIFY_DELETE, [])]
        
        if changes:
            await self.ldap.modify(entry.dn, changes)
            logger.info("user_updated", uid=uid, changes=list(changes.keys()))
        
        return await self.find_by_uid(uid)
    
    async def delete(self, uid: str) -> bool:
        """
        Delete a user.
        
        Args:
            uid: User UID
            
        Returns:
            True if deleted, False if not found
        """
        entry = await self.find_by_uid(uid)
        if not entry:
            return False
        
        await self.ldap.delete(entry.dn)
        logger.info("user_deleted", uid=uid)
        
        return True
    
    async def set_password(self, uid: str, password: str) -> bool:
        """
        Set user password.
        
        Args:
            uid: User UID
            password: New password
            
        Returns:
            True if successful, False if user not found
        """
        entry = await self.find_by_uid(uid)
        if not entry:
            return False
        
        await self.ldap.set_password(
            entry.dn,
            password,
            method=settings.PASSWORD_HASH_METHOD,
        )
        
        logger.info("user_password_set", uid=uid)
        return True
    
    async def authenticate(self, username: str, password: str) -> Optional[LdapEntry]:
        """
        Authenticate user.
        
        Args:
            username: User UID or DN
            password: User password
            
        Returns:
            User entry if authentication successful, None otherwise
        """
        return await self.ldap.authenticate(username, password)
    
    async def get_groups(self, user_dn: str) -> List[str]:
        """
        Get groups a user belongs to.
        
        Args:
            user_dn: User DN
            
        Returns:
            List of group CNs
        """
        try:
            group_entries = await self.ldap.search(
                search_filter=f"(&(objectClass=groupOfNames)(member={user_dn}))",
                attributes=["cn"],
            )
            return [g.get_first("cn") for g in group_entries if g.get_first("cn")]
        except LdapOperationError:
            return []

    async def is_locked(self, uid: str) -> Optional[bool]:
        """
        Check if user account is locked.
        
        Args:
            uid: User UID
            
        Returns:
            True if locked, False if not, None if user not found
        """
        entry = await self.find_by_uid_with_password(uid)
        if not entry:
            return None
        
        # Check password prefix (simplest method, works everywhere)
        password = entry.get_first("userPassword")
        if password:
            # Handle both str and bytes
            password_str = password.decode() if isinstance(password, bytes) else str(password)
            if password_str.startswith(self.LOCK_PREFIX):
                return True
        
        return False

    async def lock(self, uid: str) -> bool:
        """
        Lock a user account by prefixing the password hash.
        
        Args:
            uid: User UID
            
        Returns:
            True if successful, False if user not found or already locked
        """
        entry = await self.find_by_uid_with_password(uid)
        if not entry:
            return False
        
        # Check if already locked
        password = entry.get_first("userPassword")
        if not password:
            logger.warning("user_has_no_password", uid=uid)
            return False
        
        # Handle both str and bytes
        password_str = password.decode() if isinstance(password, bytes) else str(password)
        if password_str.startswith(self.LOCK_PREFIX):
            return True  # Already locked
        
        # Prefix password with {LOCKED}
        locked_password = f"{self.LOCK_PREFIX}{password_str}"
        changes = {
            "userPassword": [(MODIFY_REPLACE, [locked_password])]
        }
        await self.ldap.modify(entry.dn, changes)
        logger.info("user_locked", uid=uid)
        return True

    async def unlock(self, uid: str) -> bool:
        """
        Unlock a user account by removing the password prefix.
        
        Args:
            uid: User UID
            
        Returns:
            True if successful, False if user not found or not locked
        """
        entry = await self.find_by_uid_with_password(uid)
        if not entry:
            return False
        
        # Check if locked
        password = entry.get_first("userPassword")
        if not password:
            return True  # No password = not locked
        
        # Handle both str and bytes
        password_str = password.decode() if isinstance(password, bytes) else str(password)
        if not password_str.startswith(self.LOCK_PREFIX):
            return True  # Already unlocked
        
        # Remove {LOCKED} prefix
        unlocked_password = password_str[len(self.LOCK_PREFIX):]
        changes = {
            "userPassword": [(MODIFY_REPLACE, [unlocked_password])]
        }
        await self.ldap.modify(entry.dn, changes)
        logger.info("user_unlocked", uid=uid)
        return True
