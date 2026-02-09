"""
Password Policy Enforcement
============================

Validates passwords against configurable policy rules stored in the database.
Falls back to environment/default values when config service is unavailable.
"""

import re
from typing import List, Optional, Tuple
from dataclasses import dataclass

import structlog

from heracles_api.config import settings

logger = structlog.get_logger(__name__)

# Default password policy values (fallback when config unavailable)
DEFAULT_MIN_LENGTH = 8
DEFAULT_REQUIRE_UPPERCASE = True
DEFAULT_REQUIRE_LOWERCASE = True
DEFAULT_REQUIRE_NUMBERS = True
DEFAULT_REQUIRE_SPECIAL = False


@dataclass
class PasswordPolicy:
    """Password policy configuration."""
    min_length: int = DEFAULT_MIN_LENGTH
    require_uppercase: bool = DEFAULT_REQUIRE_UPPERCASE
    require_lowercase: bool = DEFAULT_REQUIRE_LOWERCASE
    require_numbers: bool = DEFAULT_REQUIRE_NUMBERS
    require_special: bool = DEFAULT_REQUIRE_SPECIAL


async def get_password_policy() -> PasswordPolicy:
    """
    Get the current password policy from database configuration.
    
    Falls back to defaults if config service is unavailable.
    
    Returns:
        PasswordPolicy dataclass with current settings
    """
    from heracles_api.services.config import get_config_value
    
    min_length = await get_config_value("password", "min_length", DEFAULT_MIN_LENGTH)
    require_uppercase = await get_config_value("password", "require_uppercase", DEFAULT_REQUIRE_UPPERCASE)
    require_lowercase = await get_config_value("password", "require_lowercase", DEFAULT_REQUIRE_LOWERCASE)
    require_numbers = await get_config_value("password", "require_numbers", DEFAULT_REQUIRE_NUMBERS)
    require_special = await get_config_value("password", "require_special", DEFAULT_REQUIRE_SPECIAL)
    
    return PasswordPolicy(
        min_length=int(min_length),
        require_uppercase=bool(require_uppercase),
        require_lowercase=bool(require_lowercase),
        require_numbers=bool(require_numbers),
        require_special=bool(require_special),
    )


async def validate_password_policy(password: str) -> Tuple[bool, List[str]]:
    """
    Validate a password against the current password policy.
    
    Args:
        password: The password to validate
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors: List[str] = []
    
    policy = await get_password_policy()
    
    # Length check
    if len(password) < policy.min_length:
        errors.append(f"Password must be at least {policy.min_length} characters long")
    
    # Uppercase check
    if policy.require_uppercase and not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")
    
    # Lowercase check
    if policy.require_lowercase and not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")
    
    # Numbers check
    if policy.require_numbers and not re.search(r"\d", password):
        errors.append("Password must contain at least one number")
    
    # Special characters check
    if policy.require_special and not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\;'/`~]", password):
        errors.append("Password must contain at least one special character")
    
    is_valid = len(errors) == 0
    
    if not is_valid:
        logger.debug(
            "password_policy_validation_failed",
            error_count=len(errors),
            min_length=policy.min_length,
            require_uppercase=policy.require_uppercase,
            require_lowercase=policy.require_lowercase,
            require_numbers=policy.require_numbers,
            require_special=policy.require_special,
        )
    
    return is_valid, errors


async def get_password_hash_algorithm() -> str:
    """
    Get the configured password hash algorithm.
    
    Falls back to environment variable or SSHA if config unavailable.
    
    Returns:
        Hash algorithm name (e.g., 'SSHA', 'SSHA256', 'ARGON2')
    """
    from heracles_api.services.config import get_config_value
    
    # Try database config first
    db_value = await get_config_value(
        "password",
        "default_hash_method",
        default=None,
    )
    
    allowed = {"ARGON2", "SSHA512", "SSHA256"}

    if db_value:
        # Remove quotes if stored as JSON string
        if isinstance(db_value, str):
            value = db_value.strip('"').upper()
        else:
            value = str(db_value).upper()
        if value in allowed:
            return value
    
    # Fall back to environment variable
    env_value = settings.PASSWORD_HASH_METHOD
    if env_value:
        logger.debug(
            "using_env_password_hash_algorithm",
            algorithm=env_value,
        )
        value = env_value.upper()
        if value in allowed:
            return value
    
    # Final fallback
    logger.warning(
        "password_hash_algorithm_fallback_to_default",
        default="ARGON2",
    )
    return "ARGON2"
