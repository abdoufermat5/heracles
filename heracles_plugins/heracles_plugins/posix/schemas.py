"""
POSIX Plugin Schemas
====================

Pydantic models for POSIX account data validation.
"""

from enum import Enum
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
import re


# ============================================================================
# Enums
# ============================================================================

class TrustMode(str, Enum):
    """System trust mode for host-based access control."""
    FULL_ACCESS = "fullaccess"  # Allow access to all systems
    BY_HOST = "byhost"  # Restrict access to specific hosts


class AccountStatus(str, Enum):
    """Computed account status based on shadow attributes."""
    ACTIVE = "active"
    EXPIRED = "expired"
    PASSWORD_EXPIRED = "password_expired"
    GRACE_TIME = "grace_time"
    LOCKED = "locked"


class PrimaryGroupMode(str, Enum):
    """How to handle primary group when activating POSIX."""
    SELECT_EXISTING = "select_existing"  # Use an existing group
    CREATE_PERSONAL = "create_personal"  # Create a personal group with same name as user


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
    
    # ID allocation
    uid_number: Optional[int] = Field(
        default=None,
        ge=1000,
        le=65534,
        alias="uidNumber",
        description="UID number (auto-allocated if not provided)",
    )
    force_uid: bool = Field(
        default=False,
        alias="forceUid",
        description="Force use of specific UID even if normally auto-allocated",
    )
    
    # Primary group configuration
    primary_group_mode: PrimaryGroupMode = Field(
        default=PrimaryGroupMode.SELECT_EXISTING,
        alias="primaryGroupMode",
        description="How to handle the primary group",
    )
    gid_number: Optional[int] = Field(
        default=None,
        ge=1000,
        le=65534,
        alias="gidNumber",
        description="Primary group GID number (required if mode is select_existing)",
    )
    force_gid: bool = Field(
        default=False,
        alias="forceGid",
        description="Force use of specific GID even if normally auto-allocated",
    )
    
    # Basic attributes
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
    
    # System trust (hostObject)
    trust_mode: Optional[TrustMode] = Field(
        default=None,
        alias="trustMode",
        description="System trust mode for access control",
    )
    host: Optional[List[str]] = Field(
        default=None,
        description="List of hosts the user can access (when trustMode is byhost)",
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
    def validate_group_config(self) -> "PosixAccountCreate":
        """Validate primary group configuration."""
        if self.primary_group_mode == PrimaryGroupMode.SELECT_EXISTING and self.gid_number is None:
            raise ValueError("gidNumber is required when primaryGroupMode is select_existing")
        if self.trust_mode == TrustMode.BY_HOST and not self.host:
            raise ValueError("host list is required when trustMode is byhost")
        return self
    
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
    
    # System trust (hostObject)
    trust_mode: Optional[TrustMode] = Field(None, alias="trustMode")
    host: Optional[List[str]] = Field(None, description="List of hosts for byhost trust mode")
    
    # Primary group info
    primary_group_cn: Optional[str] = Field(None, alias="primaryGroupCn")
    
    # Group memberships (groups this user belongs to via memberUid)
    group_memberships: Optional[List[str]] = Field(
        None, 
        alias="groupMemberships",
        description="List of group CNs this user belongs to",
    )
    
    # Computed status
    is_active: bool = True
    account_status: AccountStatus = Field(
        default=AccountStatus.ACTIVE,
        alias="accountStatus",
        description="Computed account status based on shadow attributes",
    )
    
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
    
    # System trust (hostObject) updates
    trust_mode: Optional[TrustMode] = Field(
        None,
        alias="trustMode",
        description="System trust mode for access control",
    )
    host: Optional[List[str]] = Field(
        None,
        description="List of hosts the user can access (when trustMode is byhost)",
    )
    
    # Force password change on next login
    must_change_password: Optional[bool] = Field(
        None,
        alias="mustChangePassword",
        description="Force user to change password on next login",
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
# MixedGroup Schemas (groupOfNames + posixGroup hybrid)
# ============================================================================

class MixedGroupCreate(BaseModel):
    """
    Schema for creating a MixedGroup.
    
    MixedGroup combines groupOfNames (LDAP organizational group)
    with posixGroup (UNIX group) in a single entry.
    """
    
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
    # groupOfNames members (DNs)
    member: Optional[List[str]] = Field(
        default=None,
        description="Initial list of member DNs (groupOfNames)",
    )
    # posixGroup members (UIDs)
    member_uid: Optional[List[str]] = Field(
        default=None,
        alias="memberUid",
        description="Initial list of member UIDs (posixGroup)",
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


class MixedGroupRead(BaseModel):
    """Schema for reading MixedGroup data."""
    
    cn: str = Field(..., description="Group name")
    gid_number: int = Field(..., alias="gidNumber")
    description: Optional[str] = None
    # groupOfNames members
    member: List[str] = Field(default_factory=list, description="List of member DNs")
    # posixGroup members  
    member_uid: List[str] = Field(default_factory=list, alias="memberUid")
    # Computed fields
    is_mixed_group: bool = Field(default=True, alias="isMixedGroup")
    
    class Config:
        populate_by_name = True


class MixedGroupUpdate(BaseModel):
    """Schema for updating MixedGroup attributes."""
    
    description: Optional[str] = Field(
        None,
        max_length=255,
        description="Group description",
    )
    member: Optional[List[str]] = Field(
        None,
        description="List of member DNs",
    )
    member_uid: Optional[List[str]] = Field(
        None,
        alias="memberUid",
        description="List of member UIDs",
    )
    
    class Config:
        populate_by_name = True


class MixedGroupListItem(BaseModel):
    """Summary item for MixedGroup listing."""
    
    cn: str
    gid_number: int = Field(..., alias="gidNumber")
    description: Optional[str] = None
    member_count: int = Field(default=0, alias="memberCount")
    member_uid_count: int = Field(default=0, alias="memberUidCount")
    
    class Config:
        populate_by_name = True


class MixedGroupListResponse(BaseModel):
    """Response for listing MixedGroups."""
    
    groups: List[MixedGroupListItem]
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
