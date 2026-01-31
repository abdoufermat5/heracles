"""
Heracles API Repositories
=========================

Data access layer for LDAP operations.
Repositories abstract the data source and provide a clean interface
for business logic operations.
"""

from heracles_api.repositories.user_repository import UserRepository
from heracles_api.repositories.group_repository import GroupRepository
from heracles_api.repositories.department_repository import DepartmentRepository

__all__ = [
    "UserRepository",
    "GroupRepository",
    "DepartmentRepository",
]
