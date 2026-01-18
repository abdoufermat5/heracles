"""
User Schemas
============

Pydantic models for user-related requests and responses.
"""

from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user model."""
    uid: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")
    cn: str = Field(..., min_length=1, max_length=128, description="Common name / Full name")
    sn: str = Field(..., min_length=1, max_length=64, description="Surname")
    given_name: Optional[str] = Field(None, max_length=64, alias="givenName")
    mail: Optional[EmailStr] = None
    telephone_number: Optional[str] = Field(None, max_length=32, alias="telephoneNumber")
    title: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = Field(None, max_length=256)


class UserCreate(UserBase):
    """User creation model."""
    password: str = Field(..., min_length=8)
    ou: str = Field(default="people", description="Organizational unit")


class UserUpdate(BaseModel):
    """User update model."""
    cn: Optional[str] = Field(None, max_length=128)
    sn: Optional[str] = Field(None, max_length=64)
    given_name: Optional[str] = Field(None, max_length=64, alias="givenName")
    mail: Optional[EmailStr] = None
    telephone_number: Optional[str] = Field(None, max_length=32, alias="telephoneNumber")
    title: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = Field(None, max_length=256)


class UserResponse(BaseModel):
    """User response model."""
    dn: str
    uid: str
    cn: str
    sn: str
    given_name: Optional[str] = Field(None, alias="givenName")
    mail: Optional[str] = None
    telephone_number: Optional[str] = Field(None, alias="telephoneNumber")
    title: Optional[str] = None
    description: Optional[str] = None
    member_of: List[str] = Field(default_factory=list, alias="memberOf")
    
    class Config:
        populate_by_name = True


class UserListResponse(BaseModel):
    """Paginated user list response."""
    users: List[UserResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class SetPasswordRequest(BaseModel):
    """Admin password reset request."""
    password: str = Field(..., min_length=8)
