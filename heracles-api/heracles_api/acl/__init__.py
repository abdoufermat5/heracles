"""
ACL Module
==========

High-performance Access Control List system for Heracles.

This module provides:
- PermissionRegistry: Load and sync ACL definitions from JSON to PostgreSQL
- AclService: Compile user ACLs, cache in Redis, invalidate on changes
- AclGuard: Thin wrapper for endpoint permission checks

Architecture:
    JSON files → PostgreSQL (definitions) → Rust compiler → UserAcl → Redis (cache)
    API Request → JWT verify → Load UserAcl from Redis → Rust check → Allow/Deny
"""

from heracles_api.acl.registry import PermissionRegistry
from heracles_api.acl.service import AclService
from heracles_api.acl.guard import AclGuard, AclGuardFactory

# Note: get_acl_guard and AclGuardDep are in core.dependencies to avoid circular imports
# Import them from there: from heracles_api.core.dependencies import AclGuardDep

__all__ = [
    "PermissionRegistry",
    "AclService",
    "AclGuard",
    "AclGuardFactory",
]
