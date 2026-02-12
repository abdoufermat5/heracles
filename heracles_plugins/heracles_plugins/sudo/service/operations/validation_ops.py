"""
Sudo Validation Operations Mixin
================================

Config-based validation for sudo roles.
"""

from typing import Any, Dict, List

import structlog

from ...schemas import SudoRoleCreate

logger = structlog.get_logger(__name__)


class ValidationOperationsMixin:
    """Mixin providing sudo validation operations."""

    async def _get_validation_config(self) -> Dict[str, Any]:
        """
        Get sudo validation config with hot-reload support.
        
        Reads from database config with fallback to init-time config.
        """
        try:
            from heracles_api.services.config import get_plugin_config_value
            
            validate_users = await get_plugin_config_value(
                "sudo",
                "validate_users",
                self._config.get("validate_users", False)
            )
            validate_commands = await get_plugin_config_value(
                "sudo",
                "validate_commands",
                self._config.get("validate_commands", False)
            )
            
            return {
                "validate_users": validate_users,
                "validate_commands": validate_commands,
            }
            
        except Exception as e:
            logger.warning("sudo_config_load_error", error=str(e))
            return {
                "validate_users": self._config.get("validate_users", False),
                "validate_commands": self._config.get("validate_commands", False),
            }

    async def _validate_sudo_users(self, sudo_users: List[str]) -> List[str]:
        """
        Validate sudoUser entries if config enables it.
        
        Checks that user references point to existing LDAP entries.
        Skips validation for special patterns (ALL, %group, +netgroup, etc.)
        
        Returns:
            List of validation errors (empty if all valid)
        """
        config = await self._get_validation_config()
        
        if not config.get("validate_users", False):
            return []
        
        errors = []
        
        for user in sudo_users:
            # Skip special patterns
            if user in ("ALL", "!ALL"):
                continue
            if user.startswith("%") or user.startswith("+") or user.startswith("!"):
                continue
            if "=" in user:  # User alias or DN reference
                continue
            
            # Try to find user in LDAP
            try:
                search_filter = f"(&(objectClass=inetOrgPerson)(uid={self._ldap._escape_filter(user)}))"
                entries = await self._ldap.search(
                    search_filter=search_filter,
                    attributes=["uid"],
                    size_limit=1,
                )
                if not entries:
                    errors.append(f"User '{user}' not found in LDAP")
            except Exception as e:
                logger.warning("sudo_user_validation_error", user=user, error=str(e))
        
        return errors

    async def _validate_sudo_commands(self, commands: List[str]) -> List[str]:
        """
        Validate sudoCommand entries if config enables it.
        
        Checks that command paths are absolute paths or special keywords.
        
        Returns:
            List of validation errors (empty if all valid)
        """
        config = await self._get_validation_config()
        
        if not config.get("validate_commands", False):
            return []
        
        errors = []
        
        for cmd in commands:
            # Skip special keywords
            if cmd in ("ALL", "!ALL", "sudoedit"):
                continue
            if cmd.startswith("!"):  # Negation
                cmd = cmd[1:]
            
            # Extract command path (before any arguments)
            cmd_path = cmd.split()[0] if cmd else ""
            
            # Command should be an absolute path
            if cmd_path and not cmd_path.startswith("/"):
                errors.append(
                    f"Command '{cmd_path}' must be an absolute path (starting with /)"
                )
        
        return errors

    async def validate_sudo_role(self, data: SudoRoleCreate) -> List[str]:
        """
        Validate a sudo role against config-based rules.
        
        Args:
            data: Sudo role creation data
            
        Returns:
            List of validation errors (empty if all valid)
        """
        errors = []
        
        # Validate sudo users
        if data.sudo_user:
            user_errors = await self._validate_sudo_users(data.sudo_user)
            errors.extend(user_errors)
        
        # Validate commands
        if data.sudo_command:
            cmd_errors = await self._validate_sudo_commands(data.sudo_command)
            errors.extend(cmd_errors)
        
        return errors
