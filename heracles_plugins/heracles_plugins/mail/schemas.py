"""
Mail Plugin Schemas
===================

Pydantic models for mail account management.
"""

import re
from typing import Optional, List, Annotated
from enum import Enum
from datetime import date
from pydantic import BaseModel, Field, field_validator, model_validator, BeforeValidator


def _validate_email_with_test_domains(v: str) -> str:
    """Validate email, allowing test domains in debug mode."""
    if v is None:
        return v

    v = str(v).strip().lower()

    # Basic email format check
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
        raise ValueError("Invalid email address format")

    # Check if it's a test domain
    domain = v.split("@")[1] if "@" in v else ""

    # Import settings lazily to avoid circular imports
    try:
        from heracles_api.config import settings
        if settings.DEBUG and settings.ALLOW_TEST_EMAIL_DOMAINS:
            # Allow test domains in debug mode
            test_domains = settings.TEST_EMAIL_DOMAINS
            if any(domain == td or domain.endswith("." + td) for td in test_domains):
                return v
    except ImportError:
        # Running without full API context (e.g., in tests)
        # Allow common test domains
        test_domains = ["local", "test", "localhost", "heracles.local", "test.local"]
        if any(domain == td or domain.endswith("." + td) for td in test_domains):
            return v

    # For non-test domains, use strict validation
    try:
        # Validate with EmailStr for proper email validation
        from pydantic import validate_email
        validate_email(v)
    except Exception:
        raise ValueError("Invalid email address")

    return v


# Custom email type that allows test domains in dev mode
FlexibleEmail = Annotated[str, BeforeValidator(_validate_email_with_test_domains)]


# ============================================================================
# Enums
# ============================================================================


class DeliveryMode(str, Enum):
    """Mail delivery mode options."""

    NORMAL = "normal"  # Normal delivery to mailbox
    FORWARD_ONLY = "forward_only"  # Forward without keeping local copy
    LOCAL_ONLY = "local_only"  # Accept only from local domain


# ============================================================================
# User Mail Account Schemas
# ============================================================================


class MailAccountCreate(BaseModel):
    """Schema for activating mail on a user."""

    mail: FlexibleEmail = Field(..., description="Primary email address")
    mail_server: Optional[str] = Field(
        None,
        alias="mailServer",
        max_length=255,
        description="Mail server hostname",
    )
    quota_mb: Optional[int] = Field(
        None,
        alias="quotaMb",
        ge=0,
        le=1048576,  # 1 PB max
        description="Mailbox quota in MiB",
    )
    alternate_addresses: List[FlexibleEmail] = Field(
        default_factory=list,
        alias="alternateAddresses",
        description="Alternative email addresses (aliases)",
    )
    forwarding_addresses: List[FlexibleEmail] = Field(
        default_factory=list,
        alias="forwardingAddresses",
        description="Mail forwarding destinations",
    )

    model_config = {"populate_by_name": True}

    @field_validator("mail_server", mode="before")
    @classmethod
    def validate_mail_server(cls, v: Optional[str]) -> Optional[str]:
        """Validate mail server hostname."""
        if v is None or v == "":
            return None
        v = v.strip().lower()
        # Basic hostname validation
        if not re.match(r"^[a-z0-9]([a-z0-9\-\.]*[a-z0-9])?$", v):
            raise ValueError("Invalid mail server hostname")
        return v


class MailAccountRead(BaseModel):
    """Schema for reading mail account data."""

    mail: str = Field(..., description="Primary email address")
    mail_server: Optional[str] = Field(None, alias="mailServer")
    quota_mb: Optional[int] = Field(None, alias="quotaMb")
    quota_used_mb: Optional[int] = Field(None, alias="quotaUsedMb")
    alternate_addresses: List[str] = Field(
        default_factory=list,
        alias="alternateAddresses",
    )
    forwarding_addresses: List[str] = Field(
        default_factory=list,
        alias="forwardingAddresses",
    )
    delivery_mode: DeliveryMode = Field(
        DeliveryMode.NORMAL,
        alias="deliveryMode",
    )
    vacation_enabled: bool = Field(False, alias="vacationEnabled")
    vacation_message: Optional[str] = Field(None, alias="vacationMessage")
    vacation_start: Optional[str] = Field(None, alias="vacationStart")
    vacation_end: Optional[str] = Field(None, alias="vacationEnd")

    model_config = {"populate_by_name": True}


class MailAccountUpdate(BaseModel):
    """Schema for updating mail account."""

    mail: Optional[FlexibleEmail] = None
    mail_server: Optional[str] = Field(None, alias="mailServer")
    quota_mb: Optional[int] = Field(None, alias="quotaMb", ge=0)
    alternate_addresses: Optional[List[FlexibleEmail]] = Field(
        None,
        alias="alternateAddresses",
    )
    forwarding_addresses: Optional[List[FlexibleEmail]] = Field(
        None,
        alias="forwardingAddresses",
    )
    delivery_mode: Optional[DeliveryMode] = Field(None, alias="deliveryMode")
    vacation_enabled: Optional[bool] = Field(None, alias="vacationEnabled")
    vacation_message: Optional[str] = Field(None, alias="vacationMessage")
    vacation_start: Optional[str] = Field(None, alias="vacationStart")
    vacation_end: Optional[str] = Field(None, alias="vacationEnd")

    model_config = {"populate_by_name": True}

    @field_validator("vacation_start", "vacation_end", mode="before")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate date format (YYYYMMDD)."""
        if v is None or v == "":
            return None
        v = v.strip()
        if not re.match(r"^\d{8}$", v):
            raise ValueError("Date must be in YYYYMMDD format")
        # Validate it's a real date
        try:
            year = int(v[:4])
            month = int(v[4:6])
            day = int(v[6:8])
            date(year, month, day)
        except ValueError:
            raise ValueError("Invalid date")
        return v

    @model_validator(mode="after")
    def validate_vacation_dates(self):
        """Validate vacation date range."""
        if self.vacation_start and self.vacation_end:
            if self.vacation_start > self.vacation_end:
                raise ValueError("Vacation start must be before end date")
        return self


# ============================================================================
# User Mail Status
# ============================================================================


class UserMailStatus(BaseModel):
    """Mail status for a user."""

    uid: str = Field(..., description="User ID")
    dn: str = Field(..., description="User DN")
    active: bool = Field(..., description="Whether mail account is active")
    data: Optional[MailAccountRead] = Field(None, description="Mail account data")

    model_config = {"populate_by_name": True}


# ============================================================================
# Group Mail Schemas
# ============================================================================


class MailGroupCreate(BaseModel):
    """Schema for activating mailing list on a group."""

    mail: FlexibleEmail = Field(..., description="Group email address")
    mail_server: Optional[str] = Field(
        None,
        alias="mailServer",
        max_length=255,
        description="Mail server hostname",
    )
    alternate_addresses: List[FlexibleEmail] = Field(
        default_factory=list,
        alias="alternateAddresses",
        description="Alternative group email addresses",
    )
    forwarding_addresses: List[FlexibleEmail] = Field(
        default_factory=list,
        alias="forwardingAddresses",
        description="Forward to non-members",
    )
    local_only: bool = Field(
        False,
        alias="localOnly",
        description="Accept mail only from local senders",
    )
    max_message_size_kb: Optional[int] = Field(
        None,
        alias="maxMessageSizeKb",
        ge=0,
        le=102400,  # 100 MB max
        description="Maximum message size in KB",
    )

    model_config = {"populate_by_name": True}


class MailGroupRead(BaseModel):
    """Schema for reading group mail data."""

    mail: str = Field(..., description="Group email address")
    mail_server: Optional[str] = Field(None, alias="mailServer")
    alternate_addresses: List[str] = Field(
        default_factory=list,
        alias="alternateAddresses",
    )
    forwarding_addresses: List[str] = Field(
        default_factory=list,
        alias="forwardingAddresses",
    )
    local_only: bool = Field(False, alias="localOnly")
    max_message_size_kb: Optional[int] = Field(None, alias="maxMessageSizeKb")
    member_emails: List[str] = Field(
        default_factory=list,
        alias="memberEmails",
        description="Email addresses of group members",
    )

    model_config = {"populate_by_name": True}


class MailGroupUpdate(BaseModel):
    """Schema for updating group mail."""

    mail: Optional[FlexibleEmail] = None
    mail_server: Optional[str] = Field(None, alias="mailServer")
    alternate_addresses: Optional[List[FlexibleEmail]] = Field(
        None,
        alias="alternateAddresses",
    )
    forwarding_addresses: Optional[List[FlexibleEmail]] = Field(
        None,
        alias="forwardingAddresses",
    )
    local_only: Optional[bool] = Field(None, alias="localOnly")
    max_message_size_kb: Optional[int] = Field(
        None,
        alias="maxMessageSizeKb",
        ge=0,
    )

    model_config = {"populate_by_name": True}


# ============================================================================
# Group Mail Status
# ============================================================================


class GroupMailStatus(BaseModel):
    """Mail status for a group."""

    cn: str = Field(..., description="Group CN")
    dn: str = Field(..., description="Group DN")
    active: bool = Field(..., description="Whether mailing list is active")
    data: Optional[MailGroupRead] = Field(None, description="Mailing list data")

    model_config = {"populate_by_name": True}
