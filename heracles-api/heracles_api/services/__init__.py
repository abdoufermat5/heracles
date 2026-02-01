"""
Heracles API Services
=====================

Service layer for business logic.
"""

from heracles_api.services.ldap_service import (
    LdapService,
    LdapEntry,
    LdapError,
    LdapConnectionError,
    LdapAuthenticationError,
    LdapNotFoundError,
    LdapOperationError,
    SearchScope,
    get_ldap_service,
    init_ldap_service,
    close_ldap_service,
)

from heracles_api.services.auth_service import (
    AuthService,
    AuthenticationError,
    TokenError,
    TokenPayload,
    UserSession,
    get_auth_service,
    init_auth_service,
)

from heracles_api.services.config import (
    ConfigService,
    get_config_service,
    init_config_service,
    is_config_service_available,
    get_config_value,
    get_plugin_config_value,
    invalidate_config_cache,
    invalidate_plugin_config_cache,
)

__all__ = [
    # LDAP
    "LdapService",
    "LdapEntry",
    "LdapError",
    "LdapConnectionError",
    "LdapAuthenticationError",
    "LdapNotFoundError",
    "LdapOperationError",
    "SearchScope",
    "get_ldap_service",
    "init_ldap_service",
    "close_ldap_service",
    # Auth
    "AuthService",
    "AuthenticationError",
    "TokenError",
    "TokenPayload",
    "UserSession",
    "get_auth_service",
    "init_auth_service",
    # Config
    "ConfigService",
    "get_config_service",
    "init_config_service",
    "is_config_service_available",
    "get_config_value",
    "get_plugin_config_value",
    "invalidate_config_cache",
    "invalidate_plugin_config_cache",
]
