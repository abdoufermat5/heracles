"""
Sudo Plugin Schemas
===================

Pydantic models for sudo role data validation.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import re


# ============================================================================
# Sudo Role Schemas
# ============================================================================

class SudoRoleBase(BaseModel):
    """Base attributes for sudo roles."""
    
    description: Optional[str] = Field(
        default=None,
        max_length=1024,
        description="Description of this sudo role",
    )
    sudo_user: List[str] = Field(
        default_factory=list,
        alias="sudoUser",
        description="Users who may run sudo (uid, %group, #uid, ALL)",
    )
    sudo_host: List[str] = Field(
        default=["ALL"],
        alias="sudoHost",
        description="Hosts where sudo is allowed (hostname, IP, ALL)",
    )
    sudo_command: List[str] = Field(
        default_factory=list,
        alias="sudoCommand",
        description="Commands allowed (path with args, ALL)",
    )
    sudo_run_as_user: List[str] = Field(
        default=["ALL"],
        alias="sudoRunAsUser",
        description="Users that commands may be run as",
    )
    sudo_run_as_group: List[str] = Field(
        default_factory=list,
        alias="sudoRunAsGroup",
        description="Groups that commands may be run as",
    )
    sudo_option: List[str] = Field(
        default_factory=list,
        alias="sudoOption",
        description="Sudo options (NOPASSWD, PASSWD, NOEXEC, etc.)",
    )
    sudo_order: Optional[int] = Field(
        default=0,
        ge=0,
        alias="sudoOrder",
        description="Priority order (lower = higher priority)",
    )
    sudo_not_before: Optional[datetime] = Field(
        default=None,
        alias="sudoNotBefore",
        description="Start of validity period",
    )
    sudo_not_after: Optional[datetime] = Field(
        default=None,
        alias="sudoNotAfter",
        description="End of validity period",
    )
    
    @field_validator("sudo_user", mode="before")
    @classmethod
    def validate_sudo_user(cls, v):
        """Validate and normalize sudo user entries."""
        if v is None:
            return []
        if isinstance(v, str):
            v = [v]
        validated = []
        for entry in v:
            entry = entry.strip()
            if not entry:
                continue
            # Valid formats: username, %groupname, #uid, +netgroup, ALL
            if entry == "ALL":
                validated.append(entry)
            elif entry.startswith("%"):
                # Group reference
                if len(entry) < 2:
                    raise ValueError(f"Invalid group reference: {entry}")
                validated.append(entry)
            elif entry.startswith("#"):
                # UID reference
                try:
                    int(entry[1:])
                except ValueError:
                    raise ValueError(f"Invalid UID reference: {entry}")
                validated.append(entry)
            elif entry.startswith("+"):
                # Netgroup reference
                if len(entry) < 2:
                    raise ValueError(f"Invalid netgroup reference: {entry}")
                validated.append(entry)
            else:
                # Username (alphanumeric with some special chars)
                if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_.-]*$", entry):
                    raise ValueError(f"Invalid username format: {entry}")
                validated.append(entry)
        return validated
    
    @field_validator("sudo_host", mode="before")
    @classmethod
    def validate_sudo_host(cls, v):
        """Validate and normalize sudo host entries."""
        if v is None:
            return ["ALL"]
        if isinstance(v, str):
            v = [v]
        validated = []
        for entry in v:
            entry = entry.strip()
            if not entry:
                continue
            # Valid formats: hostname, IP, IP/mask, ALL, +netgroup
            if entry == "ALL":
                validated.append(entry)
            elif entry.startswith("+"):
                # Netgroup
                validated.append(entry)
            elif entry.startswith("!"):
                # Negation
                validated.append(entry)
            else:
                # Hostname or IP - basic validation
                validated.append(entry)
        return validated if validated else ["ALL"]
    
    @field_validator("sudo_command", mode="before")
    @classmethod
    def validate_sudo_command(cls, v):
        """Validate and normalize sudo command entries."""
        if v is None:
            return []
        if isinstance(v, str):
            v = [v]
        validated = []
        for entry in v:
            entry = entry.strip()
            if not entry:
                continue
            # Valid formats: /path/to/command, /path/to/command args, ALL, !command
            if entry == "ALL":
                validated.append(entry)
            elif entry.startswith("!"):
                # Negation
                validated.append(entry)
            elif entry.startswith("/") or entry.startswith("sudoedit"):
                # Command path
                validated.append(entry)
            else:
                raise ValueError(f"Invalid command format (must start with / or be ALL): {entry}")
        return validated
    
    @field_validator("sudo_option", mode="before")
    @classmethod
    def validate_sudo_option(cls, v):
        """Validate sudo options."""
        if v is None:
            return []
        if isinstance(v, str):
            v = [v]
        # Common sudo options
        valid_options = {
            "NOPASSWD", "PASSWD", "NOEXEC", "EXEC", 
            "SETENV", "NOSETENV", "LOG_INPUT", "NOLOG_INPUT",
            "LOG_OUTPUT", "NOLOG_OUTPUT", "MAIL", "NOMAIL",
            "FOLLOW", "NOFOLLOW",
        }
        validated = []
        for entry in v:
            entry = entry.strip()
            if not entry:
                continue
            # Check if it's a simple option or option=value
            option_name = entry.split("=")[0].strip("!")
            # Allow known options or custom options with =
            if option_name.upper() in valid_options or "=" in entry:
                validated.append(entry)
            else:
                # Allow any option for flexibility
                validated.append(entry)
        return validated

    model_config = {"populate_by_name": True}


class SudoRoleCreate(SudoRoleBase):
    """Schema for creating a new sudo role."""
    
    cn: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Common name (role identifier)",
    )
    
    @field_validator("cn")
    @classmethod
    def validate_cn(cls, v: str) -> str:
        """Validate CN format."""
        v = v.strip()
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", v):
            raise ValueError(
                "CN must start with a letter and contain only alphanumeric, underscore, or hyphen"
            )
        return v


class SudoRoleRead(SudoRoleBase):
    """Schema for reading a sudo role."""
    
    dn: str = Field(..., description="Distinguished Name")
    cn: str = Field(..., description="Common name")
    is_default: bool = Field(
        default=False,
        alias="isDefault",
        description="Whether this is the defaults entry",
    )
    is_valid: bool = Field(
        default=True,
        alias="isValid",
        description="Whether the rule is currently valid (based on time constraints)",
    )


class SudoRoleUpdate(BaseModel):
    """Schema for updating a sudo role."""
    
    description: Optional[str] = Field(default=None)
    sudo_user: Optional[List[str]] = Field(default=None, alias="sudoUser")
    sudo_host: Optional[List[str]] = Field(default=None, alias="sudoHost")
    sudo_command: Optional[List[str]] = Field(default=None, alias="sudoCommand")
    sudo_run_as_user: Optional[List[str]] = Field(default=None, alias="sudoRunAsUser")
    sudo_run_as_group: Optional[List[str]] = Field(default=None, alias="sudoRunAsGroup")
    sudo_option: Optional[List[str]] = Field(default=None, alias="sudoOption")
    sudo_order: Optional[int] = Field(default=None, alias="sudoOrder")
    sudo_not_before: Optional[datetime] = Field(default=None, alias="sudoNotBefore")
    sudo_not_after: Optional[datetime] = Field(default=None, alias="sudoNotAfter")
    
    model_config = {"populate_by_name": True}


# ============================================================================
# List Response Schemas
# ============================================================================

class SudoRoleListResponse(BaseModel):
    """Response for listing sudo roles."""
    
    roles: List[SudoRoleRead]
    total: int
    page: int = 1
    page_size: int = 50
    has_more: bool = False


# ============================================================================
# Helper Schemas
# ============================================================================

class SudoUserEntry(BaseModel):
    """A single sudo user entry with type information."""
    
    value: str
    type: str = Field(description="user, group, uid, netgroup, or all")
    
    @classmethod
    def from_string(cls, entry: str) -> "SudoUserEntry":
        """Parse a sudo user string into typed entry."""
        if entry == "ALL":
            return cls(value=entry, type="all")
        elif entry.startswith("%"):
            return cls(value=entry[1:], type="group")
        elif entry.startswith("#"):
            return cls(value=entry[1:], type="uid")
        elif entry.startswith("+"):
            return cls(value=entry[1:], type="netgroup")
        else:
            return cls(value=entry, type="user")


class SudoCommandEntry(BaseModel):
    """A single sudo command entry."""
    
    command: str
    negated: bool = False
    args: Optional[str] = None
    
    @classmethod
    def from_string(cls, entry: str) -> "SudoCommandEntry":
        """Parse a sudo command string."""
        negated = entry.startswith("!")
        if negated:
            entry = entry[1:]
        
        if entry == "ALL":
            return cls(command="ALL", negated=negated)
        
        # Split command and args
        parts = entry.split(None, 1)
        command = parts[0]
        args = parts[1] if len(parts) > 1 else None
        
        return cls(command=command, negated=negated, args=args)
