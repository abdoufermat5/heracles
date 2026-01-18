"""
POSIX Plugin Schemas
====================

Pydantic models for POSIX account data validation.
Compatible with FusionDirectory POSIX implementation.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, model_validator
import re


# ============================================================================
# POSIX Account (User) Schemas
# ============================================================================

class PosixAccountBase(BaseModel):
    """Base attributes for POSIX accounts."""
    
    gid_number: int = Field(
        ...,
        ge=1000,
        le=65534,
        alias="gidNumber",
        description="Primary group GID number",
    )
    home_directory: str = Field(
        ...,
        min_length=1,
        max_length=255,
        alias="homeDirectory",
        description="Home directory path (e.g., /home/jdoe)",
    )
    login_shell: str = Field(
        default="/bin/bash",
        alias="loginShell",
        description="Login shell (e.g., /bin/bash)",
    )
    gecos: Optional[str] = Field(
        default=None,
        max_length=255,
        description="GECOS field (typically full name)",
    )
    
    @field_validator("home_directory")
    @classmethod
    def validate_home_directory(cls, v: str) -> str:
        """Validate home directory path format."""
        if not v.startswith("/"):
            raise ValueError("Home directory must be an absolute path")
        # Allow alphanumeric, dots, dashes, underscores, and slashes
        if not re.match(r"^/[\w./-]+$", v):
            raise ValueError("Home directory contains invalid characters")
        return v
    
    @field_validator("login_shell")
    @classmethod
    def validate_login_shell(cls, v: str) -> str:
        """Validate login shell path."""
        valid_shells = [
            "/bin/bash",
            "/bin/sh",
            "/bin/zsh",
            "/bin/tcsh",
            "/bin/csh",
            "/bin/ksh",
            "/bin/fish",
            "/usr/bin/bash",
            "/usr/bin/sh",
            "/usr/bin/zsh",
            "/usr/bin/fish",
            "/usr/sbin/nologin",
            "/bin/false",
            "/sbin/nologin",
        ]
        if v and v not in valid_shells:
            # Allow custom shells that look like paths
            if not re.match(r"^/[\w./-]+$", v):
                raise ValueError(f"Invalid shell path: {v}")
        return v
    
    class Config:
        populate_by_name = True


class PosixAccountCreate(BaseModel):
    """Schema for activating POSIX on a user."""
    
    uid_number: Optional[int] = Field(
        default=None,
        ge=1000,
        le=65534,
        alias="uidNumber",
        description="UID number (auto-allocated if not provided)",
    )
    gid_number: int = Field(
        ...,
        ge=1000,
        le=65534,
        alias="gidNumber",
        description="Primary group GID number",
    )
    home_directory: Optional[str] = Field(
        default=None,
        alias="homeDirectory",
        description="Home directory path (auto-generated from uid if not provided)",
    )
    login_shell: str = Field(
        default="/bin/bash",
        alias="loginShell",
        description="Login shell",
    )
    gecos: Optional[str] = Field(
        default=None,
        description="GECOS field",
    )
    
    @field_validator("home_directory")
    @classmethod
    def validate_home_directory(cls, v: Optional[str]) -> Optional[str]:
        """Validate home directory if provided."""
        if v is None:
            return v
        if not v.startswith("/"):
            raise ValueError("Home directory must be an absolute path")
        if not re.match(r"^/[\w./-]+$", v):
            raise ValueError("Home directory contains invalid characters")
        return v
    
    class Config:
        populate_by_name = True


class PosixAccountRead(BaseModel):
    """Schema for reading POSIX account data."""
    
    uid_number: int = Field(..., alias="uidNumber")
    gid_number: int = Field(..., alias="gidNumber")
    home_directory: str = Field(..., alias="homeDirectory")
    login_shell: str = Field(default="/bin/bash", alias="loginShell")
    gecos: Optional[str] = None
    
    # Shadow account attributes
    shadow_last_change: Optional[int] = Field(None, alias="shadowLastChange")
    shadow_min: Optional[int] = Field(None, alias="shadowMin")
    shadow_max: Optional[int] = Field(None, alias="shadowMax")
    shadow_warning: Optional[int] = Field(None, alias="shadowWarning")
    shadow_inactive: Optional[int] = Field(None, alias="shadowInactive")
    shadow_expire: Optional[int] = Field(None, alias="shadowExpire")
    
    # Computed status
    is_active: bool = True
    
    class Config:
        populate_by_name = True


class PosixAccountUpdate(BaseModel):
    """Schema for updating POSIX account attributes."""
    
    gid_number: Optional[int] = Field(
        None,
        ge=1000,
        le=65534,
        alias="gidNumber",
    )
    home_directory: Optional[str] = Field(None, alias="homeDirectory")
    login_shell: Optional[str] = Field(None, alias="loginShell")
    gecos: Optional[str] = None
    
    # Shadow account updates
    shadow_min: Optional[int] = Field(
        None, 
        ge=0,
        alias="shadowMin",
        description="Minimum days between password changes",
    )
    shadow_max: Optional[int] = Field(
        None,
        ge=0, 
        alias="shadowMax",
        description="Maximum days password is valid",
    )
    shadow_warning: Optional[int] = Field(
        None,
        ge=0,
        alias="shadowWarning", 
        description="Days before expiry to warn user",
    )
    shadow_inactive: Optional[int] = Field(
        None,
        ge=-1,
        alias="shadowInactive",
        description="Days after expiry until account disabled (-1 = never)",
    )
    shadow_expire: Optional[int] = Field(
        None,
        ge=-1,
        alias="shadowExpire",
        description="Days since epoch when account expires (-1 = never)",
    )
    
    @field_validator("home_directory")
    @classmethod
    def validate_home_directory(cls, v: Optional[str]) -> Optional[str]:
        """Validate home directory if provided."""
        if v is None:
            return v
        if not v.startswith("/"):
            raise ValueError("Home directory must be an absolute path")
        if not re.match(r"^/[\w./-]+$", v):
            raise ValueError("Home directory contains invalid characters")
        return v
    
    @model_validator(mode="after")
    def validate_shadow_settings(self) -> "PosixAccountUpdate":
        """Validate shadow settings consistency."""
        if self.shadow_warning is not None and self.shadow_max is None:
            # Warning without max doesn't make sense but we'll allow it
            pass
        if self.shadow_min is not None and self.shadow_max is not None:
            if self.shadow_min > self.shadow_max:
                raise ValueError("shadowMin cannot be greater than shadowMax")
        return self
    
    class Config:
        populate_by_name = True


# ============================================================================
# POSIX Group Schemas  
# ============================================================================

class PosixGroupCreate(BaseModel):
    """Schema for activating POSIX on an existing group (deprecated approach)."""
    
    gid_number: Optional[int] = Field(
        default=None,
        ge=1000,
        le=65534,
        alias="gidNumber",
        description="GID number (auto-allocated if not provided)",
    )
    
    class Config:
        populate_by_name = True


class PosixGroupFullCreate(BaseModel):
    """Schema for creating a standalone POSIX group."""
    
    cn: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Group name (cn)",
    )
    gid_number: Optional[int] = Field(
        default=None,
        ge=1000,
        le=65534,
        alias="gidNumber",
        description="GID number (auto-allocated if not provided)",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Group description",
    )
    member_uid: Optional[List[str]] = Field(
        default=None,
        alias="memberUid",
        description="Initial list of member UIDs",
    )
    
    @field_validator("cn")
    @classmethod
    def validate_cn(cls, v: str) -> str:
        """Validate group name."""
        if not re.match(r"^[a-z][a-z0-9_-]*$", v, re.IGNORECASE):
            raise ValueError("Group name must start with a letter and contain only letters, numbers, underscores, and hyphens")
        return v
    
    class Config:
        populate_by_name = True


class PosixGroupRead(BaseModel):
    """Schema for reading POSIX group data."""
    
    cn: str = Field(..., description="Group name")
    gid_number: int = Field(..., alias="gidNumber")
    description: Optional[str] = None
    member_uid: List[str] = Field(default_factory=list, alias="memberUid")
    is_active: bool = True
    
    class Config:
        populate_by_name = True


class PosixGroupUpdate(BaseModel):
    """Schema for updating POSIX group attributes."""
    
    description: Optional[str] = Field(
        None,
        max_length=255,
        description="Group description",
    )
    member_uid: Optional[List[str]] = Field(
        None,
        alias="memberUid",
        description="List of member UIDs",
    )
    
    class Config:
        populate_by_name = True


class PosixGroupListItem(BaseModel):
    """Summary item for POSIX group listing."""
    
    cn: str
    gid_number: int = Field(..., alias="gidNumber")
    description: Optional[str] = None
    member_count: int = Field(default=0, alias="memberCount")
    
    class Config:
        populate_by_name = True


class PosixGroupListResponse(BaseModel):
    """Response for listing POSIX groups."""
    
    groups: List[PosixGroupListItem]
    total: int


# ============================================================================
# API Response Schemas
# ============================================================================

class PosixStatusResponse(BaseModel):
    """Response for checking POSIX status."""
    
    active: bool
    data: Optional[PosixAccountRead] = None


class PosixGroupStatusResponse(BaseModel):
    """Response for checking POSIX group status."""
    
    active: bool
    data: Optional[PosixGroupRead] = None


class AvailableShellsResponse(BaseModel):
    """Response for available login shells."""
    
    shells: List[dict]
    default: str


class IdAllocationResponse(BaseModel):
    """Response for ID allocation info."""
    
    next_uid: int
    next_gid: int
    uid_range: dict
    gid_range: dict
