"""
Systems Service
===============

Main service class for system management.
Composes all operation mixins into a unified service.
"""

from typing import Any, Dict

from heracles_api.services.ldap_service import LdapService

from .base import SystemServiceBase
from .operations import (
    ConfigOperationsMixin,
    ValidationOperationsMixin,
    OUOperationsMixin,
    CRUDOperationsMixin,
    HostOperationsMixin,
    HelperOperationsMixin,
    TabOperationsMixin,
)


class SystemService(
    ConfigOperationsMixin,
    ValidationOperationsMixin,
    OUOperationsMixin,
    CRUDOperationsMixin,
    HostOperationsMixin,
    HelperOperationsMixin,
    TabOperationsMixin,
    SystemServiceBase,
):
    """
    Service for managing systems in LDAP.

    Handles all system types:
    - Server (hrcServer)
    - Workstation (hrcWorkstation)
    - Terminal (hrcTerminal)
    - Printer (hrcPrinter)
    - Component (device)
    - Phone (hrcPhone)
    - Mobile Phone (hrcMobilePhone)

    All types support ipHost and ieee802Device for IP/MAC addressing.
    
    This class composes multiple operation mixins:
    - ConfigOperationsMixin: Validation config and DN management
    - ValidationOperationsMixin: Uniqueness checks and validation
    - OUOperationsMixin: OU management
    - CRUDOperationsMixin: Create, read, update, delete operations
    - HostOperationsMixin: Host validation for other plugins
    - HelperOperationsMixin: Entry conversion and attribute building
    - TabOperationsMixin: TabService abstract method implementations
    """

    def __init__(self, ldap_service: LdapService, config: Dict[str, Any]):
        """Initialize the systems service.
        
        Args:
            ldap_service: LDAP service for directory operations
            config: Plugin configuration dictionary
        """
        super().__init__(ldap_service, config)
