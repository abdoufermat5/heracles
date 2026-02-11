"""
User Repository
===============

Data access layer for user LDAP operations.
"""

from typing import Optional, List
from dataclasses import dataclass

from heracles_api.services.ldap_service import LdapService, LdapEntry, LdapOperationError
from heracles_api.schemas.user import UserCreate, UserUpdate, UserResponse
from heracles_api.config import settings
from heracles_api.core.password_policy import get_password_hash_algorithm
from heracles_api.core.ldap_config import (
    get_users_rdn,
    get_default_user_objectclasses,
    DEFAULT_USERS_RDN,
)

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
        # Personal
        "displayName", "labeledURI", "preferredLanguage", "jpegPhoto",
        # Contact
        "mobile", "facsimileTelephoneNumber",
        # Address
        "street", "postalAddress", "l", "st", "postalCode", "c", "roomNumber",
        # Organization
        "o", "ou", "departmentNumber", "employeeNumber", "employeeType", "manager",
        # Metadata
        "createTimestamp", "modifyTimestamp",
    ]
    # Include userPassword for lock status checks
    USER_ATTRIBUTES_WITH_PASSWORD = USER_ATTRIBUTES + ["userPassword"]
    LOCK_PREFIX = "{LOCKED}"  # Password prefix for locked accounts
    
    def __init__(self, ldap: LdapService):
        self.ldap = ldap
        self.base_dn = settings.LDAP_BASE_DN
    
    async def _get_users_container(self) -> str:
        """
        Get the users container OU from config.
        
        Returns:
            Users OU (e.g., 'ou=people')
        """
        rdn = await get_users_rdn()
        # Ensure proper format
        if not rdn.startswith("ou="):
            return f"ou={rdn}"
        return rdn
    
    async def _build_user_dn(self, uid: str, ou: Optional[str] = None, department_dn: Optional[str] = None) -> str:
        """
        Build user DN from UID.

        Args:
            uid: User UID
            ou: Container OU name (None = use config default)
            department_dn: Optional department DN to create user within

        Returns:
            User DN string
        """
        # Get users container from config if not specified
        if ou is None:
            users_container = await self._get_users_container()
        else:
            users_container = f"ou={ou}" if not ou.startswith("ou=") else ou
        
        if department_dn:
            # Create under users container within the department
            # e.g., uid=john,ou=people,ou=Engineering,dc=heracles,dc=local
            return f"uid={uid},{users_container},{department_dn}"
        return f"uid={uid},{users_container},{self.base_dn}"
    
    def _entry_to_dict(self, entry: LdapEntry) -> dict:
        """Convert LDAP entry to dictionary."""
        photo_raw = entry.get_first("jpegPhoto")
        if photo_raw:
            import base64
            if isinstance(photo_raw, bytes):
                photo_b64 = base64.b64encode(photo_raw).decode("ascii")
            else:
                photo_b64 = str(photo_raw)
        else:
            photo_b64 = None

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
            # Personal
            "displayName": entry.get_first("displayName"),
            "labeledURI": entry.get_first("labeledURI"),
            "preferredLanguage": entry.get_first("preferredLanguage"),
            "jpegPhoto": photo_b64,
            # Contact
            "mobile": entry.get_first("mobile"),
            "facsimileTelephoneNumber": entry.get_first("facsimileTelephoneNumber"),
            # Address
            "street": entry.get_first("street"),
            "postalAddress": entry.get_first("postalAddress"),
            "l": entry.get_first("l"),
            "st": entry.get_first("st"),
            "postalCode": entry.get_first("postalCode"),
            "c": entry.get_first("c"),
            "roomNumber": entry.get_first("roomNumber"),
            # Organization
            "o": entry.get_first("o"),
            "organizationalUnit": entry.get_first("ou"),
            "departmentNumber": entry.get_first("departmentNumber"),
            "employeeNumber": entry.get_first("employeeNumber"),
            "employeeType": entry.get_first("employeeType"),
            "manager": entry.get_first("manager"),
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
        base_dn: Optional[str] = None,
        limit: int = 0,
    ) -> UserSearchResult:
        """
        Search users with optional filtering.

        Args:
            search_term: Search in uid, cn, mail
            ou: Filter by organizational unit (None = use config default)
            base_dn: Base DN to search from (e.g., department DN for scoped search)
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
        # Get users container from config if not specified
        if ou:
            people_container = f"ou={ou}" if not ou.startswith("ou=") else ou
        else:
            people_container = await self._get_users_container()
        
        if base_dn:
            # Search within department's people container
            # e.g., ou=people,ou=Test,dc=heracles,dc=local
            search_base = f"{people_container},{base_dn}"
        else:
            # Search only in root-level people container
            # e.g., ou=people,dc=heracles,dc=local
            search_base = f"{people_container},{self.base_dn}"

        entries = await self.ldap.search(
            search_base=search_base,
            search_filter=search_filter,
            attributes=self.USER_ATTRIBUTES,
            size_limit=limit,
        )

        return UserSearchResult(users=entries, total=len(entries))
    
    async def create(self, user: UserCreate, department_dn: Optional[str] = None) -> LdapEntry:
        """
        Create a new user.

        Args:
            user: User creation data
            department_dn: Optional department DN (user will be created under ou=people within this dept)

        Returns:
            Created user entry

        Raises:
            LdapOperationError: If creation fails
        """
        # Use config-based OU if user.ou not specified
        user_dn = await self._build_user_dn(
            user.uid, 
            ou=user.ou if user.ou and user.ou != "people" else None, 
            department_dn=department_dn
        )
        
        # Get hash algorithm from config
        hash_algorithm = await get_password_hash_algorithm()
        
        # Get objectClasses from config
        object_classes = await get_default_user_objectclasses()
        
        # Build attributes
        attrs = {
            "cn": user.cn,
            "sn": user.sn,
            "userPassword": self.ldap._hash_password(user.password, hash_algorithm),
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
        # Personal
        if user.display_name:
            attrs["displayName"] = user.display_name
        if user.labeled_uri:
            attrs["labeledURI"] = user.labeled_uri
        if user.preferred_language:
            attrs["preferredLanguage"] = user.preferred_language
        # Contact
        if user.mobile:
            attrs["mobile"] = user.mobile
        if user.facsimile_telephone_number:
            attrs["facsimileTelephoneNumber"] = user.facsimile_telephone_number
        # Address
        if user.street:
            attrs["street"] = user.street
        if user.postal_address:
            attrs["postalAddress"] = user.postal_address
        if user.l:
            attrs["l"] = user.l
        if user.st:
            attrs["st"] = user.st
        if user.postal_code:
            attrs["postalCode"] = user.postal_code
        if user.c:
            attrs["c"] = user.c
        if user.room_number:
            attrs["roomNumber"] = user.room_number
        # Organization
        if user.o:
            attrs["o"] = user.o
        if user.ou_field:
            attrs["ou"] = user.ou_field
        if user.department_number:
            attrs["departmentNumber"] = user.department_number
        if user.employee_number:
            attrs["employeeNumber"] = user.employee_number
        if user.employee_type:
            attrs["employeeType"] = user.employee_type
        if user.manager:
            attrs["manager"] = user.manager
        
        await self.ldap.add(
            dn=user_dn,
            object_classes=object_classes,
            attributes=attrs,
        )
        
        logger.info("user_created", uid=user.uid, dn=user_dn, hash_algorithm=hash_algorithm)
        
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
            # Personal
            "displayName": "displayName",
            "labeledURI": "labeledURI",
            "preferredLanguage": "preferredLanguage",
            # Contact
            "mobile": "mobile",
            "facsimileTelephoneNumber": "facsimileTelephoneNumber",
            # Address
            "street": "street",
            "postalAddress": "postalAddress",
            "l": "l",
            "st": "st",
            "postalCode": "postalCode",
            "c": "c",
            "roomNumber": "roomNumber",
            # Organization
            "o": "o",
            "organizationalUnit": "ou",
            "departmentNumber": "departmentNumber",
            "employeeNumber": "employeeNumber",
            "employeeType": "employeeType",
            "manager": "manager",
        }
        
        for field, ldap_attr in attr_mapping.items():
            if field in update_data:
                value = update_data[field]
                # Treat empty strings as None (delete the attribute)
                if value is not None and value != "":
                    changes[ldap_attr] = ("replace", [value])
                else:
                    changes[ldap_attr] = ("delete", [])
        
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
        
        # Get hash algorithm from config
        hash_algorithm = await get_password_hash_algorithm()
        
        await self.ldap.set_password(
            entry.dn,
            password,
            method=hash_algorithm,
        )
        
        logger.info("user_password_set", uid=uid, hash_algorithm=hash_algorithm)
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
            "userPassword": ("replace", [locked_password])
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
            "userPassword": ("replace", [unlocked_password])
        }
        await self.ldap.modify(entry.dn, changes)
        logger.info("user_unlocked", uid=uid)
        return True
