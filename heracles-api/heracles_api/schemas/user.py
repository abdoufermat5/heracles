"""
User Schemas
============

Pydantic models for user-related requests and responses.
"""

from pydantic import BaseModel, Field

from heracles_api.schemas.email import TestEmailStr


class UserBase(BaseModel):
    """Base user model."""

    uid: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")
    cn: str = Field(..., min_length=1, max_length=128, description="Common name / Full name")
    sn: str = Field(..., min_length=1, max_length=64, description="Surname")
    given_name: str | None = Field(None, max_length=64, alias="givenName")
    mail: TestEmailStr | None = None
    telephone_number: str | None = Field(None, max_length=32, alias="telephoneNumber")
    title: str | None = Field(None, max_length=64)
    description: str | None = Field(None, max_length=256)
    # Personal
    display_name: str | None = Field(None, max_length=128, alias="displayName")
    labeled_uri: str | None = Field(None, max_length=256, alias="labeledURI", description="Homepage URL")
    preferred_language: str | None = Field(None, max_length=16, alias="preferredLanguage")
    # Contact
    mobile: str | None = Field(None, max_length=32, description="Mobile phone number")
    facsimile_telephone_number: str | None = Field(
        None, max_length=32, alias="facsimileTelephoneNumber", description="Fax number"
    )
    # Address
    street: str | None = Field(None, max_length=256)
    postal_address: str | None = Field(None, max_length=256, alias="postalAddress")
    locality: str | None = Field(None, max_length=128, alias="l", description="City / Locality")
    st: str | None = Field(None, max_length=128, alias="st", description="State / Province")
    postal_code: str | None = Field(None, max_length=16, alias="postalCode")
    c: str | None = Field(None, max_length=2, alias="c", description="Country (2-letter code)")
    room_number: str | None = Field(None, max_length=64, alias="roomNumber")
    # Organization
    o: str | None = Field(None, max_length=128, alias="o", description="Organization")
    ou_field: str | None = Field(
        None, max_length=128, alias="organizationalUnit", description="Organizational Unit label"
    )
    department_number: str | None = Field(None, max_length=64, alias="departmentNumber")
    employee_number: str | None = Field(None, max_length=64, alias="employeeNumber")
    employee_type: str | None = Field(None, max_length=64, alias="employeeType")
    manager: str | None = Field(None, max_length=256, description="Manager DN")


class UserCreate(UserBase):
    """User creation model."""

    password: str = Field(..., min_length=8)
    ou: str = Field(default="people", description="Container OU name (default: people)")
    department_dn: str | None = Field(
        None,
        alias="departmentDn",
        description="Department DN (user will be created under ou=people within this department)",
    )
    template_id: str | None = Field(
        None,
        alias="templateId",
        description="Optional template ID — applies defaults and activates plugins after creation",
    )


class UserUpdate(BaseModel):
    """User update model."""

    cn: str | None = Field(None, max_length=128)
    sn: str | None = Field(None, max_length=64)
    given_name: str | None = Field(None, max_length=64, alias="givenName")
    mail: TestEmailStr | None = None
    telephone_number: str | None = Field(None, max_length=32, alias="telephoneNumber")
    title: str | None = Field(None, max_length=64)
    description: str | None = Field(None, max_length=256)
    # Personal
    display_name: str | None = Field(None, max_length=128, alias="displayName")
    labeled_uri: str | None = Field(None, max_length=256, alias="labeledURI")
    preferred_language: str | None = Field(None, max_length=16, alias="preferredLanguage")
    # Contact
    mobile: str | None = Field(None, max_length=32)
    facsimile_telephone_number: str | None = Field(None, max_length=32, alias="facsimileTelephoneNumber")
    # Address
    street: str | None = Field(None, max_length=256)
    postal_address: str | None = Field(None, max_length=256, alias="postalAddress")
    locality: str | None = Field(None, max_length=128, alias="l")
    st: str | None = Field(None, max_length=128, alias="st")
    postal_code: str | None = Field(None, max_length=16, alias="postalCode")
    c: str | None = Field(None, max_length=2, alias="c")
    room_number: str | None = Field(None, max_length=64, alias="roomNumber")
    # Organization
    o: str | None = Field(None, max_length=128, alias="o")
    ou_field: str | None = Field(None, max_length=128, alias="organizationalUnit")
    department_number: str | None = Field(None, max_length=64, alias="departmentNumber")
    employee_number: str | None = Field(None, max_length=64, alias="employeeNumber")
    employee_type: str | None = Field(None, max_length=64, alias="employeeType")
    manager: str | None = Field(None, max_length=256)


class UserResponse(BaseModel):
    """User response model."""

    dn: str
    uid: str
    cn: str
    sn: str
    given_name: str | None = Field(None, alias="givenName")
    mail: str | None = None
    telephone_number: str | None = Field(None, alias="telephoneNumber")
    title: str | None = None
    description: str | None = None
    # Personal
    display_name: str | None = Field(None, alias="displayName")
    labeled_uri: str | None = Field(None, alias="labeledURI")
    preferred_language: str | None = Field(None, alias="preferredLanguage")
    jpeg_photo: str | None = Field(None, alias="jpegPhoto", description="Base64-encoded photo")
    # Contact
    mobile: str | None = None
    facsimile_telephone_number: str | None = Field(None, alias="facsimileTelephoneNumber")
    # Address
    street: str | None = None
    postal_address: str | None = Field(None, alias="postalAddress")
    locality: str | None = Field(None, alias="l")
    st: str | None = Field(None, alias="st")
    postal_code: str | None = Field(None, alias="postalCode")
    c: str | None = Field(None, alias="c")
    room_number: str | None = Field(None, alias="roomNumber")
    # Organization
    o: str | None = Field(None, alias="o")
    ou_field: str | None = Field(None, alias="organizationalUnit")
    department_number: str | None = Field(None, alias="departmentNumber")
    employee_number: str | None = Field(None, alias="employeeNumber")
    employee_type: str | None = Field(None, alias="employeeType")
    manager: str | None = None
    # Membership
    member_of: list[str] = Field(default_factory=list, alias="memberOf")

    class Config:
        populate_by_name = True


class UserListResponse(BaseModel):
    """Paginated user list response."""

    users: list[UserResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class SetPasswordRequest(BaseModel):
    """Admin password reset request."""

    password: str = Field(..., min_length=8)
