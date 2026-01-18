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
]
