"""
Auth Schemas
============

Pydantic models for authentication-related requests and responses.
"""

from pydantic import BaseModel, Field

from heracles_api.schemas.email import TestEmailStr


class LoginRequest(BaseModel):
    """Login request body."""

    username: str = Field(..., min_length=1, description="User UID or DN")
    password: str = Field(..., min_length=1, description="User password")


class TokenResponse(BaseModel):
    """Token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token TTL in seconds")


class RefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str


class UserInfoResponse(BaseModel):
    """Current user information."""

    dn: str
    uid: str
    display_name: str
    mail: str | None = None
    groups: list[str] = []


class PasswordChangeRequest(BaseModel):
    """Password change request."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


class PasswordResetRequest(BaseModel):
    """Password reset request."""

    email: TestEmailStr
