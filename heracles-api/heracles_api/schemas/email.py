"""
Custom Email Validation
=======================

Custom email validator that allows test domains (like .local) in debug mode.
"""

import re
from typing import Annotated, Any

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, PydanticCustomError, core_schema

from heracles_api.config import settings


class _TestEmailStr:
    """
    Custom email type that allows test domains in DEBUG mode.

    In DEBUG mode with ALLOW_TEST_EMAIL_DOMAINS=true, domains like
    .local, .test, .localhost are accepted.

    In production mode, standard email validation is enforced.
    """

    # Standard email regex (simplified but effective)
    _EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    # Test domain regex (allows .local, .test, etc.)
    _TEST_EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z0-9]+$")

    @classmethod
    def _validate(cls, value: str) -> str:
        if not isinstance(value, str):
            raise PydanticCustomError("string_type", "Input should be a valid string")

        value = value.strip().lower()

        if not value:
            raise PydanticCustomError("value_error", "Email cannot be empty")

        # Check if we should allow test domains
        allow_test = settings.DEBUG and settings.ALLOW_TEST_EMAIL_DOMAINS

        if allow_test:
            # In debug mode, check against test email regex
            if not cls._TEST_EMAIL_REGEX.match(value):
                raise PydanticCustomError("value_error", "Invalid email format: {email}", {"email": value})

            # Optionally validate against allowed test domains
            domain = value.split("@")[1] if "@" in value else ""
            test_domains = settings.TEST_EMAIL_DOMAINS

            # Check if it's a test domain or a standard valid domain
            is_test_domain = any(domain == td or domain.endswith(f".{td}") for td in test_domains)

            if is_test_domain:
                return value

            # If not a test domain, validate as standard email
            if not cls._EMAIL_REGEX.match(value):
                raise PydanticCustomError("value_error", "Invalid email format: {email}", {"email": value})
        else:
            # In production, use standard email validation
            try:
                from email_validator import EmailNotValidError, validate_email

                result = validate_email(value, check_deliverability=False)
                value = result.normalized
            except EmailNotValidError as e:
                raise PydanticCustomError("value_error", "Invalid email: {error}", {"error": str(e)})

        return value

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
            serialization=core_schema.to_string_ser_schema(),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        return {"type": "string", "format": "email"}


# Type alias for use in schemas
TestEmailStr = Annotated[str, _TestEmailStr]
