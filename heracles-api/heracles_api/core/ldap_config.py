"""
LDAP Configuration Helpers
==========================

Provides access to LDAP-related configuration from the database.
Falls back to environment/default values when config service is unavailable.

Note: LDAP base DN settings require restart to take effect for safety reasons,
as changing them mid-operation could cause data integrity issues.
"""

import structlog

from heracles_api.config import settings

logger = structlog.get_logger(__name__)

# Default values (fallback when config unavailable)
DEFAULT_USERS_RDN = "ou=people"
DEFAULT_GROUPS_RDN = "ou=groups"
DEFAULT_ROLES_RDN = "ou=roles"
DEFAULT_USER_OBJECTCLASSES = ["inetOrgPerson", "organizationalPerson", "person"]
DEFAULT_GROUP_OBJECTCLASSES = ["groupOfNames"]
DEFAULT_ROLE_OBJECTCLASSES = ["organizationalRole"]
DEFAULT_PAGE_SIZE = 100


async def get_users_rdn() -> str:
    """
    Get the RDN for user entries from config.

    Returns:
        Users RDN (e.g., 'ou=people')
    """
    from heracles_api.services.config import get_config_value

    value = await get_config_value("ldap", "user_rdn", DEFAULT_USERS_RDN)

    # Remove quotes if stored as JSON string
    if isinstance(value, str):
        return value.strip('"')
    return str(value)


async def get_groups_rdn() -> str:
    """
    Get the RDN for group entries from config.

    Returns:
        Groups RDN (e.g., 'ou=groups')
    """
    from heracles_api.services.config import get_config_value

    value = await get_config_value("ldap", "group_rdn", DEFAULT_GROUPS_RDN)

    # Remove quotes if stored as JSON string
    if isinstance(value, str):
        return value.strip('"')
    return str(value)


async def get_roles_rdn() -> str:
    """
    Get the RDN for role entries from config.

    Returns:
        Roles RDN (e.g., 'ou=roles')
    """
    from heracles_api.services.config import get_config_value

    value = await get_config_value("ldap", "roles_rdn", DEFAULT_ROLES_RDN)

    # Remove quotes if stored as JSON string
    if isinstance(value, str):
        return value.strip('"')
    return str(value)


async def get_default_user_objectclasses() -> list[str]:
    """
    Get the default object classes for new user entries.

    Returns:
        List of objectClass values
    """
    from heracles_api.services.config import get_config_value

    value = await get_config_value("ldap", "default_user_objectclasses", DEFAULT_USER_OBJECTCLASSES)

    if isinstance(value, list):
        return value

    # Handle JSON string
    if isinstance(value, str):
        import json

        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass

    return DEFAULT_USER_OBJECTCLASSES


async def get_default_group_objectclasses() -> list[str]:
    """
    Get the default object classes for new group entries.

    Returns:
        List of objectClass values
    """
    from heracles_api.services.config import get_config_value

    value = await get_config_value("ldap", "default_group_objectclasses", DEFAULT_GROUP_OBJECTCLASSES)

    if isinstance(value, list):
        return value

    # Handle JSON string
    if isinstance(value, str):
        import json

        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass

    return DEFAULT_GROUP_OBJECTCLASSES


async def get_default_role_objectclasses() -> list[str]:
    """
    Get the default object classes for new role entries.

    Returns:
        List of objectClass values
    """
    from heracles_api.services.config import get_config_value

    value = await get_config_value("ldap", "default_role_objectclasses", DEFAULT_ROLE_OBJECTCLASSES)

    if isinstance(value, list):
        return value

    # Handle JSON string
    if isinstance(value, str):
        import json

        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass

    return DEFAULT_ROLE_OBJECTCLASSES


async def get_ldap_page_size() -> int:
    """
    Get the LDAP page size for paginated queries.

    Returns:
        Page size (number of entries per page)
    """
    from heracles_api.services.config import get_config_value

    value = await get_config_value("ldap", "page_size", DEFAULT_PAGE_SIZE)
    return int(value)


def get_full_users_dn(base_dn: str | None = None, users_rdn: str = DEFAULT_USERS_RDN) -> str:
    """
    Build the full DN for the users container.

    Args:
        base_dn: Base DN (defaults to settings.LDAP_BASE_DN)
        users_rdn: Users RDN from config

    Returns:
        Full DN like 'ou=people,dc=heracles,dc=local'
    """
    base = base_dn or settings.LDAP_BASE_DN
    return f"{users_rdn},{base}"


def get_full_groups_dn(base_dn: str | None = None, groups_rdn: str = DEFAULT_GROUPS_RDN) -> str:
    """
    Build the full DN for the groups container.

    Args:
        base_dn: Base DN (defaults to settings.LDAP_BASE_DN)
        groups_rdn: Groups RDN from config

    Returns:
        Full DN like 'ou=groups,dc=heracles,dc=local'
    """
    base = base_dn or settings.LDAP_BASE_DN
    return f"{groups_rdn},{base}"


def get_full_roles_dn(base_dn: str | None = None, roles_rdn: str = DEFAULT_ROLES_RDN) -> str:
    """
    Build the full DN for the roles container.

    Args:
        base_dn: Base DN (defaults to settings.LDAP_BASE_DN)
        roles_rdn: Roles RDN from config

    Returns:
        Full DN like 'ou=roles,dc=heracles,dc=local'
    """
    base = base_dn or settings.LDAP_BASE_DN
    return f"{roles_rdn},{base}"
