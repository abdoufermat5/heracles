"""
Heracles API Repositories
=========================

Data access layer for LDAP and PostgreSQL operations.
Repositories abstract the data source and provide a clean interface
for business logic operations.
"""

from heracles_api.repositories.user_repository import UserRepository
from heracles_api.repositories.group_repository import GroupRepository
from heracles_api.repositories.role_repository import RoleRepository
from heracles_api.repositories.department_repository import DepartmentRepository
from heracles_api.repositories.acl_repository import AclRepository
from heracles_api.repositories.config_repository import ConfigRepository
from heracles_api.repositories.plugin_config_repository import PluginConfigRepository
from heracles_api.repositories.config_history_repository import ConfigHistoryRepository

__all__ = [
    "UserRepository",
    "GroupRepository",
    "RoleRepository",
    "DepartmentRepository",
    "AclRepository",
    "ConfigRepository",
    "PluginConfigRepository",
    "ConfigHistoryRepository",
]
