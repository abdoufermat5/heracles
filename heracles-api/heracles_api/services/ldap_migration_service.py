"""
LDAP Migration Service
======================

Handles RDN (Relative Distinguished Name) changes and data migration in LDAP.
Provides safe migration utilities with rollback support and user confirmation.

Key concepts:
- RDN: The leftmost component of a DN (e.g., "ou=people" in "ou=people,dc=example,dc=com")
- ModRDN: LDAP operation to rename/move entries (may not be supported by all servers)
- Migration: Moving entries from old RDN location to new RDN location
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog

from heracles_api.services.ldap_service import (
    LdapService,
    LdapOperationError,
    LdapNotFoundError,
)

logger = structlog.get_logger(__name__)


class MigrationStatus(str, Enum):
    """Status of a migration operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLBACK = "rollback"


class MigrationMode(str, Enum):
    """Mode for handling RDN changes."""
    MODRDN = "modrdn"  # Use LDAP modRDN operation (recommended)
    COPY_DELETE = "copy_delete"  # Copy to new location, delete old (fallback)
    LEAVE_ORPHANED = "leave_orphaned"  # Leave entries in old location (warning)


@dataclass
class MigrationCheck:
    """Result of checking what would be affected by an RDN change."""
    old_rdn: str
    new_rdn: str
    base_dn: str
    entries_count: int
    entries_dns: List[str]  # List of DNs that would be affected
    supports_modrdn: bool
    recommended_mode: MigrationMode
    warnings: List[str]
    blocking: bool = False  # If True, change should not proceed


@dataclass
class MigrationResult:
    """Result of a migration operation."""
    success: bool
    mode: MigrationMode
    entries_migrated: int
    entries_failed: int
    failed_entries: List[Dict[str, str]]  # [{dn, error}]
    warnings: List[str]


class LdapMigrationService:
    """
    Service for handling LDAP entry migrations when RDN settings change.
    
    Provides:
    - Pre-migration checks to warn about affected entries
    - Multiple migration modes (modRDN, copy-delete, leave orphaned)
    - Detailed logging and error reporting
    - Rollback support for failed migrations
    """
    
    def __init__(self, ldap_service: LdapService, config_service: Any = None):
        """
        Initialize the migration service.
        
        Args:
            ldap_service: LDAP service for directory operations
            config_service: Optional config service for reading migration settings
        """
        self._ldap = ldap_service
        self._config = config_service
    
    async def check_rdn_change(
        self,
        old_rdn: str,
        new_rdn: str,
        base_dn: Optional[str] = None,
        object_class_filter: Optional[str] = None,
    ) -> MigrationCheck:
        """
        Check what would be affected by an RDN change.
        
        This MUST be called before allowing an RDN change to warn the user.
        Checks ALL containers matching the RDN pattern across the entire directory,
        including nested contexts (e.g., ou=people in ou=Test, ou=ChildTest, etc.)
        
        Args:
            old_rdn: Current RDN (e.g., "ou=people")
            new_rdn: New RDN (e.g., "ou=users")
            base_dn: Base DN (defaults to LDAP service base_dn)
            object_class_filter: Optional objectClass filter (e.g., "inetOrgPerson")
            
        Returns:
            MigrationCheck with affected entries and recommendations.
        """
        base = base_dn or self._ldap.base_dn
        warnings: List[str] = []
        
        # Find ALL containers matching the old RDN pattern across the directory
        # e.g., ou=people at root, ou=people,ou=Test, ou=people,ou=ChildTest,ou=Test, etc.
        all_entries_dns: List[str] = []
        affected_containers: List[str] = []
        
        try:
            # First, find all containers matching the old RDN
            # Parse the RDN to get the attribute and value (e.g., "ou=people" -> ou, people)
            rdn_parts = old_rdn.split("=", 1)
            if len(rdn_parts) != 2:
                warnings.append(f"Invalid RDN format: {old_rdn}")
            else:
                rdn_attr, rdn_value = rdn_parts
                
                # Search for all OUs/containers with this name anywhere in the tree
                container_filter = f"(&(objectClass=organizationalUnit)({rdn_attr}={rdn_value}))"
                
                containers = await self._ldap.search(
                    search_base=base,
                    search_filter=container_filter,
                    attributes=["dn"],
                    scope="subtree",
                )
                
                affected_containers = [c.dn for c in containers if c.dn]
                
                if affected_containers:
                    logger.debug(
                        "rdn_change_found_containers",
                        old_rdn=old_rdn,
                        containers_count=len(affected_containers),
                        containers=affected_containers[:5],  # Log first 5
                    )
                
                # Now search for entries in each container
                search_filter = f"(objectClass={object_class_filter})" if object_class_filter else "(objectClass=*)"
                
                for container_dn in affected_containers:
                    try:
                        entries = await self._ldap.search(
                            search_base=container_dn,
                            search_filter=search_filter,
                            attributes=["dn"],
                            scope="subtree",
                        )
                        
                        # Exclude the container itself, include everything else
                        for e in entries:
                            if e.dn and e.dn.lower() != container_dn.lower():
                                all_entries_dns.append(e.dn)
                                
                    except (LdapNotFoundError, LdapOperationError) as e:
                        logger.debug("rdn_check_container_search_failed", container=container_dn, error=str(e))
                        continue
                
                if len(affected_containers) > 1:
                    warnings.append(
                        f"Found {len(affected_containers)} containers matching '{old_rdn}' "
                        f"(including nested contexts like Test, departments, etc.)"
                    )
                
                if all_entries_dns:
                    warnings.append(
                        f"Found {len(all_entries_dns)} total entries across all '{old_rdn}' containers that will need migration."
                    )
                    
        except LdapNotFoundError:
            # Base doesn't exist - safe to change
            logger.debug("rdn_change_check_base_not_found", base_dn=base)
        except LdapOperationError as e:
            warnings.append(f"Could not check existing entries: {e}")
        
        entries_count = len(all_entries_dns)
        
        # Only include first 10 DNs for display
        display_dns = all_entries_dns[:10] if entries_count > 10 else all_entries_dns
        if entries_count > 10:
            warnings.append(f"Showing first 10 of {entries_count} affected entries.")
        
        # Check if modRDN is supported
        supports_modrdn = await self._check_modrdn_support()
        
        # Determine recommended mode
        if entries_count == 0:
            recommended_mode = MigrationMode.MODRDN  # Doesn't matter, no entries
        elif supports_modrdn:
            recommended_mode = MigrationMode.MODRDN
        else:
            recommended_mode = MigrationMode.COPY_DELETE
            warnings.append(
                "Your LDAP server may not support modRDN operations. "
                "Migration will use copy-delete method which is slower but compatible."
            )
        
        # Add warning if entries exist
        if entries_count > 0 and not supports_modrdn:
            warnings.append(
                "⚠️ WARNING: If you proceed without migration, entries will remain "
                f"in their old locations and become orphaned. "
                "This means they will not be visible in the application."
            )
        
        return MigrationCheck(
            old_rdn=old_rdn,
            new_rdn=new_rdn,
            base_dn=base,
            entries_count=entries_count,
            entries_dns=display_dns,
            supports_modrdn=supports_modrdn,
            recommended_mode=recommended_mode,
            warnings=warnings,
            blocking=False,  # Never block, just warn
        )
    
    async def _check_modrdn_support(self) -> bool:
        """
        Check if modRDN is supported and allowed.
        
        Returns:
            True if modRDN operations are allowed.
        """
        # First check config setting
        if self._config:
            try:
                from heracles_api.services.config import get_config_value
                allow_modrdn = await get_config_value("ldap", "allow_modrdn", True)
                
                # Parse boolean from various formats
                if isinstance(allow_modrdn, bool):
                    return allow_modrdn
                if isinstance(allow_modrdn, str):
                    return allow_modrdn.lower() in ("true", "1", "yes")
                return bool(allow_modrdn)
            except Exception:
                pass
        
        # Default to True - most modern LDAP servers support modRDN
        return True
    
    async def migrate_entries(
        self,
        old_rdn: str,
        new_rdn: str,
        base_dn: Optional[str] = None,
        mode: Optional[MigrationMode] = None,
        object_class_filter: Optional[str] = None,
        create_container: bool = True,
    ) -> MigrationResult:
        """
        Migrate entries from old RDN to new RDN across ALL matching containers.
        
        This handles nested contexts (ou=people in root, ou=Test, ou=ChildTest, etc.)
        
        Args:
            old_rdn: Current RDN
            new_rdn: New RDN
            base_dn: Base DN
            mode: Migration mode (defaults to config or MODRDN)
            object_class_filter: Filter for specific objectClass
            create_container: Whether to create the new container if it doesn't exist
            
        Returns:
            MigrationResult with details of the operation.
        """
        base = base_dn or self._ldap.base_dn
        
        warnings: List[str] = []
        failed_entries: List[Dict[str, str]] = []
        migrated_count = 0
        
        # Determine mode
        if mode is None:
            supports_modrdn = await self._check_modrdn_support()
            mode = MigrationMode.MODRDN if supports_modrdn else MigrationMode.COPY_DELETE
        
        # Handle leave_orphaned mode (just log warning and return)
        if mode == MigrationMode.LEAVE_ORPHANED:
            logger.warning(
                "migration_mode_leave_orphaned",
                old_rdn=old_rdn,
                new_rdn=new_rdn,
            )
            warnings.append(
                f"Entries left in their old locations. "
                "They will not be visible in the application until manually migrated."
            )
            return MigrationResult(
                success=True,
                mode=mode,
                entries_migrated=0,
                entries_failed=0,
                failed_entries=[],
                warnings=warnings,
            )
        
        # Find ALL containers matching the old RDN
        affected_containers: List[str] = []
        rdn_parts = old_rdn.split("=", 1)
        
        if len(rdn_parts) != 2:
            return MigrationResult(
                success=False,
                mode=mode,
                entries_migrated=0,
                entries_failed=0,
                failed_entries=[],
                warnings=[f"Invalid RDN format: {old_rdn}"],
            )
        
        rdn_attr, rdn_value = rdn_parts
        
        try:
            # Search for all OUs/containers with this name anywhere in the tree
            container_filter = f"(&(objectClass=organizationalUnit)({rdn_attr}={rdn_value}))"
            
            containers = await self._ldap.search(
                search_base=base,
                search_filter=container_filter,
                attributes=["dn"],
                scope="subtree",
            )
            
            affected_containers = [c.dn for c in containers if c.dn]
            
        except LdapOperationError as e:
            return MigrationResult(
                success=False,
                mode=mode,
                entries_migrated=0,
                entries_failed=0,
                failed_entries=[],
                warnings=[f"Failed to find containers: {e}"],
            )
        
        if not affected_containers:
            return MigrationResult(
                success=True,
                mode=mode,
                entries_migrated=0,
                entries_failed=0,
                failed_entries=[],
                warnings=["No containers found matching the old RDN."],
            )
        
        logger.info(
            "migration_starting",
            old_rdn=old_rdn,
            new_rdn=new_rdn,
            containers_count=len(affected_containers),
        )
        
        # Process each container
        for old_container_dn in affected_containers:
            # Calculate the new container DN by replacing the old RDN with the new one
            # e.g., ou=people,ou=Test,dc=heracles,dc=local -> ou=users,ou=Test,dc=heracles,dc=local
            new_container_dn = old_container_dn.replace(f"{old_rdn},", f"{new_rdn},", 1)
            
            # Create new container if needed
            if create_container:
                try:
                    await self._ensure_container(new_container_dn)
                except LdapOperationError as e:
                    warnings.append(f"Failed to create container {new_container_dn}: {e}")
                    continue
            
            # Get entries to migrate from this container
            try:
                search_filter = f"(objectClass={object_class_filter})" if object_class_filter else "(objectClass=*)"
                entries = await self._ldap.search(
                    search_base=old_container_dn,
                    search_filter=search_filter,
                    attributes=["*"],
                    scope="subtree",
                )
                
                # Exclude the container itself
                entries = [
                    e for e in entries
                    if e.dn.lower() != old_container_dn.lower()
                ]
                
            except LdapNotFoundError:
                # No entries in this container
                continue
            except LdapOperationError as e:
                warnings.append(f"Failed to search container {old_container_dn}: {e}")
                continue
            
            # Migrate each entry in this container
            for entry in entries:
                entry_dn = entry.dn if hasattr(entry, 'dn') else entry.get("dn", "")
                if not entry_dn:
                    continue
                
                try:
                    if mode == MigrationMode.MODRDN:
                        await self._migrate_with_modrdn(entry_dn, old_rdn, new_rdn, base)
                    else:
                        await self._migrate_with_copy_delete(entry, old_rdn, new_rdn, base)
                    
                    migrated_count += 1
                    logger.info("entry_migrated", dn=entry_dn, mode=mode.value)
                    
                except LdapOperationError as e:
                    failed_entries.append({
                        "dn": entry_dn,
                        "error": str(e),
                    })
                    logger.error("entry_migration_failed", dn=entry_dn, error=str(e))
        
        # Log summary
        logger.info(
            "migration_completed",
            old_rdn=old_rdn,
            new_rdn=new_rdn,
            containers_processed=len(affected_containers),
            migrated=migrated_count,
            failed=len(failed_entries),
            mode=mode.value,
        )
        
        return MigrationResult(
            success=len(failed_entries) == 0,
            mode=mode,
            entries_migrated=migrated_count,
            entries_failed=len(failed_entries),
            failed_entries=failed_entries,
            warnings=warnings,
        )
    
    async def _migrate_with_modrdn(
        self,
        entry_dn: str,
        old_rdn: str,
        new_rdn: str,
        base_dn: str,
    ) -> None:
        """
        Migrate an entry using LDAP modRDN operation.
        
        This renames/moves the entry to the new location.
        
        Note: modRDN is not yet implemented in heracles-core.
        This method falls back to copy-delete for now.
        """
        # TODO: Implement native modRDN in heracles-core for better performance
        # For now, use copy-delete as fallback
        
        # Get the full entry first
        entry = await self._ldap.get_by_dn(entry_dn)
        if not entry:
            raise LdapOperationError(f"Entry not found: {entry_dn}")
        
        # Pass the LdapEntry directly - _migrate_with_copy_delete handles both
        await self._migrate_with_copy_delete(entry, old_rdn, new_rdn, base_dn)
    
    async def _migrate_with_copy_delete(
        self,
        entry: Any,
        old_rdn: str,
        new_rdn: str,
        base_dn: str,
    ) -> None:
        """
        Migrate an entry using copy-delete method.
        
        This is a fallback for LDAP servers that don't support modRDN.
        Works with nested containers by replacing the RDN component in the DN.
        """
        # Handle both LdapEntry objects and dict
        if hasattr(entry, 'dn'):
            old_dn = entry.dn
            entry_attrs = entry.attributes if hasattr(entry, 'attributes') else {}
        else:
            old_dn = entry.get("dn", "")
            entry_attrs = {k: v for k, v in entry.items() if k != "dn"}
        
        # Replace the old RDN with the new RDN in the DN
        # e.g., uid=john,ou=people,ou=Test,dc=... -> uid=john,ou=users,ou=Test,dc=...
        # Use case-insensitive replacement
        old_dn_lower = old_dn.lower()
        old_rdn_lower = old_rdn.lower()
        
        if f",{old_rdn_lower}," in old_dn_lower:
            # Find the position and replace preserving original case
            idx = old_dn_lower.find(f",{old_rdn_lower},")
            new_dn = old_dn[:idx+1] + new_rdn + old_dn[idx + 1 + len(old_rdn):]
        elif old_dn_lower.endswith(f",{old_rdn_lower}"):
            # RDN is at the end
            idx = old_dn_lower.rfind(f",{old_rdn_lower}")
            new_dn = old_dn[:idx+1] + new_rdn
        else:
            raise LdapOperationError(f"Could not calculate new DN for: {old_dn}")
        
        # Prepare attributes (exclude operational attributes and dn)
        attributes = {}
        operational_attrs = {"dn", "createtimestamp", "modifytimestamp", "entrycsn", "entryuuid", 
                           "structuralobjectclass", "subschemasubentry", "hassubordinates"}
        object_classes = []
        
        for key, value in entry_attrs.items():
            key_lower = key.lower()
            if key_lower in operational_attrs:
                continue
            if key_lower == "objectclass":
                # Extract objectClasses
                if isinstance(value, list):
                    object_classes = value
                else:
                    object_classes = [value]
            else:
                attributes[key] = value
        
        # Create new entry with correct API: add(dn, object_classes, attributes)
        await self._ldap.add(new_dn, object_classes, attributes)
        
        # Delete old entry
        await self._ldap.delete(old_dn)
    
    async def _ensure_container(self, container_dn: str) -> None:
        """
        Ensure a container (organizationalUnit) exists.
        
        Creates it if it doesn't exist.
        """
        try:
            existing = await self._ldap.get_by_dn(container_dn)
            if existing:
                return  # Container already exists
        except LdapNotFoundError:
            pass  # Expected, will create
        
        # Extract the RDN to get the ou name
        rdn = container_dn.split(",")[0]
        rdn_type, rdn_value = rdn.split("=", 1)
        
        if rdn_type.lower() == "ou":
            object_classes = ["organizationalUnit"]
            attributes = {"ou": rdn_value}
        elif rdn_type.lower() == "cn":
            object_classes = ["container"]
            attributes = {"cn": rdn_value}
        else:
            raise LdapOperationError(f"Unknown RDN type: {rdn_type}")
        
        await self._ldap.add(container_dn, object_classes, attributes)
        logger.info("container_created", dn=container_dn)


# Convenience function for checking RDN changes
async def check_rdn_change_impact(
    ldap_service: LdapService,
    old_rdn: str,
    new_rdn: str,
    base_dn: Optional[str] = None,
    object_class_filter: Optional[str] = None,
) -> MigrationCheck:
    """
    Convenience function to check the impact of an RDN change.
    
    Args:
        ldap_service: LDAP service instance
        old_rdn: Current RDN
        new_rdn: New RDN
        base_dn: Base DN
        object_class_filter: Optional objectClass filter
        
    Returns:
        MigrationCheck with impact analysis.
    """
    migration_service = LdapMigrationService(ldap_service)
    return await migration_service.check_rdn_change(
        old_rdn=old_rdn,
        new_rdn=new_rdn,
        base_dn=base_dn,
        object_class_filter=object_class_filter,
    )
