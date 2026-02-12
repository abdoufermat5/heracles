"""
User Schemas
============

Pydantic models for user-related requests and responses.
"""

from typing import Optional, List
from pydantic import BaseModel, Field

from heracles_api.schemas.email import TestEmailStr


class UserBase(BaseModel):
    """Base user model."""
    uid: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")
    cn: str = Field(..., min_length=1, max_length=128, description="Common name / Full name")
    sn: str = Field(..., min_length=1, max_length=64, description="Surname")
    given_name: Optional[str] = Field(None, max_length=64, alias="givenName")
    mail: Optional[TestEmailStr] = None
    telephone_number: Optional[str] = Field(None, max_length=32, alias="telephoneNumber")
    title: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = Field(None, max_length=256)
    # Personal
    display_name: Optional[str] = Field(None, max_length=128, alias="displayName")
    labeled_uri: Optional[str] = Field(None, max_length=256, alias="labeledURI", description="Homepage URL")
    preferred_language: Optional[str] = Field(None, max_length=16, alias="preferredLanguage")
    # Contact
    mobile: Optional[str] = Field(None, max_length=32, description="Mobile phone number")
    facsimile_telephone_number: Optional[str] = Field(None, max_length=32, alias="facsimileTelephoneNumber", description="Fax number")
    # Address
    street: Optional[str] = Field(None, max_length=256)
    postal_address: Optional[str] = Field(None, max_length=256, alias="postalAddress")
    locality: Optional[str] = Field(None, max_length=128, alias="l", description="City / Locality")
    st: Optional[str] = Field(None, max_length=128, alias="st", description="State / Province")
    postal_code: Optional[str] = Field(None, max_length=16, alias="postalCode")
    c: Optional[str] = Field(None, max_length=2, alias="c", description="Country (2-letter code)")
    room_number: Optional[str] = Field(None, max_length=64, alias="roomNumber")
    # Organization
    o: Optional[str] = Field(None, max_length=128, alias="o", description="Organization")
    ou_field: Optional[str] = Field(None, max_length=128, alias="organizationalUnit", description="Organizational Unit label")
    department_number: Optional[str] = Field(None, max_length=64, alias="departmentNumber")
    employee_number: Optional[str] = Field(None, max_length=64, alias="employeeNumber")
    employee_type: Optional[str] = Field(None, max_length=64, alias="employeeType")
    manager: Optional[str] = Field(None, max_length=256, description="Manager DN")


class UserCreate(UserBase):
    """User creation model."""
    password: str = Field(..., min_length=8)
    ou: str = Field(default="people", description="Container OU name (default: people)")
    department_dn: Optional[str] = Field(
        None,
        alias="departmentDn",
        description="Department DN (user will be created under ou=people within this department)"
    )
    template_id: Optional[str] = Field(
        None,
        alias="templateId",
        description="Optional template ID — applies defaults and activates plugins after creation",
    )


class UserUpdate(BaseModel):
    """User update model."""
    cn: Optional[str] = Field(None, max_length=128)
    sn: Optional[str] = Field(None, max_length=64)
    given_name: Optional[str] = Field(None, max_length=64, alias="givenName")
    mail: Optional[TestEmailStr] = None
    telephone_number: Optional[str] = Field(None, max_length=32, alias="telephoneNumber")
    title: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = Field(None, max_length=256)
    # Personal
    display_name: Optional[str] = Field(None, max_length=128, alias="displayName")
    labeled_uri: Optional[str] = Field(None, max_length=256, alias="labeledURI")
    preferred_language: Optional[str] = Field(None, max_length=16, alias="preferredLanguage")
    # Contact
    mobile: Optional[str] = Field(None, max_length=32)
    facsimile_telephone_number: Optional[str] = Field(None, max_length=32, alias="facsimileTelephoneNumber")
    # Address
    street: Optional[str] = Field(None, max_length=256)
    postal_address: Optional[str] = Field(None, max_length=256, alias="postalAddress")
    locality: Optional[str] = Field(None, max_length=128, alias="l")
    st: Optional[str] = Field(None, max_length=128, alias="st")
    postal_code: Optional[str] = Field(None, max_length=16, alias="postalCode")
    c: Optional[str] = Field(None, max_length=2, alias="c")
    room_number: Optional[str] = Field(None, max_length=64, alias="roomNumber")
    # Organization
    o: Optional[str] = Field(None, max_length=128, alias="o")
    ou_field: Optional[str] = Field(None, max_length=128, alias="organizationalUnit")
    department_number: Optional[str] = Field(None, max_length=64, alias="departmentNumber")
    employee_number: Optional[str] = Field(None, max_length=64, alias="employeeNumber")
    employee_type: Optional[str] = Field(None, max_length=64, alias="employeeType")
    manager: Optional[str] = Field(None, max_length=256)


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
    # Personal
    display_name: Optional[str] = Field(None, alias="displayName")
    labeled_uri: Optional[str] = Field(None, alias="labeledURI")
    preferred_language: Optional[str] = Field(None, alias="preferredLanguage")
    jpeg_photo: Optional[str] = Field(None, alias="jpegPhoto", description="Base64-encoded photo")
    # Contact
    mobile: Optional[str] = None
    facsimile_telephone_number: Optional[str] = Field(None, alias="facsimileTelephoneNumber")
    # Address
    street: Optional[str] = None
    postal_address: Optional[str] = Field(None, alias="postalAddress")
    locality: Optional[str] = Field(None, alias="l")
    st: Optional[str] = Field(None, alias="st")
    postal_code: Optional[str] = Field(None, alias="postalCode")
    c: Optional[str] = Field(None, alias="c")
    room_number: Optional[str] = Field(None, alias="roomNumber")
    # Organization
    o: Optional[str] = Field(None, alias="o")
    ou_field: Optional[str] = Field(None, alias="organizationalUnit")
    department_number: Optional[str] = Field(None, alias="departmentNumber")
    employee_number: Optional[str] = Field(None, alias="employeeNumber")
    employee_type: Optional[str] = Field(None, alias="employeeType")
    manager: Optional[str] = None
    # Membership
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
