"""
Configuration Validators
========================

Validation utilities for configuration values.
"""

import json
from typing import Any

import structlog

from heracles_api.plugins.base import ConfigSection
from heracles_api.schemas.config import (
    ConfigFieldOption,
    ConfigFieldResponse,
    ConfigFieldType,
    ConfigFieldValidation,
    ConfigSectionResponse,
)

logger = structlog.get_logger(__name__)


def parse_json_value(value: Any) -> Any:
    """
    Parse a JSON value from database storage.

    Values are stored as JSON strings in the database.
    Returns the parsed value or the original if parsing fails.
    """
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    return value


def parse_validation(rules: Any | None) -> ConfigFieldValidation | None:
    """Parse validation rules from JSON/JSONB."""
    if not rules:
        return None

    # Handle case where rules might be a string (needs JSON parsing)
    if isinstance(rules, str):
        try:
            rules = json.loads(rules)
        except json.JSONDecodeError:
            logger.warning("invalid_validation_rules_json", rules=rules)
            return None

    if not isinstance(rules, dict):
        logger.warning("validation_rules_not_a_dict", type=type(rules).__name__)
        return None

    return ConfigFieldValidation(
        required=rules.get("required", True),
        min_value=rules.get("min"),
        max_value=rules.get("max"),
        min_length=rules.get("minLength"),
        max_length=rules.get("maxLength"),
        pattern=rules.get("pattern"),
    )


def parse_options(options: Any | None) -> list[ConfigFieldOption] | None:
    """Parse options from JSON/JSONB."""
    if not options:
        return None

    # Handle case where options might be a string (needs JSON parsing)
    if isinstance(options, str):
        try:
            options = json.loads(options)
        except json.JSONDecodeError:
            logger.warning("invalid_options_json", options=options)
            return None

    # Now options should be a list
    if not isinstance(options, list):
        logger.warning("options_not_a_list", type=type(options).__name__)
        return None

    return [
        ConfigFieldOption(
            value=opt["value"],
            label=opt["label"],
            description=opt.get("description"),
        )
        for opt in options
    ]


def validate_value(
    value: Any,
    data_type: str,
    validation_rules: dict | None,
) -> list[str]:
    """Validate a value against its type and rules."""
    errors = []
    rules = validation_rules or {}

    # Type validation
    type_validators = {
        "string": lambda v: isinstance(v, str),
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "boolean": lambda v: isinstance(v, bool),
        "float": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "list": lambda v: isinstance(v, list),
        "select": lambda v: True,
        "multiselect": lambda v: isinstance(v, list),
    }

    validator = type_validators.get(data_type)
    if validator and not validator(value):
        errors.append(f"Invalid type: expected {data_type}")
        return errors

    # Range validation
    if data_type in ("integer", "float"):
        if "min" in rules and value < rules["min"]:
            errors.append(f"Value must be at least {rules['min']}")
        if "max" in rules and value > rules["max"]:
            errors.append(f"Value must be at most {rules['max']}")

    # Length validation
    if data_type == "string":
        if "minLength" in rules and len(value) < rules["minLength"]:
            errors.append(f"Must be at least {rules['minLength']} characters")
        if "maxLength" in rules and len(value) > rules["maxLength"]:
            errors.append(f"Must be at most {rules['maxLength']} characters")

    return errors


def convert_sections_to_response(
    sections: list[ConfigSection],
    current_config: dict[str, Any],
) -> list[ConfigSectionResponse]:
    """Convert plugin ConfigSection objects to response format."""
    result = []

    for section in sections:
        fields = []
        for field in section.fields:
            # Get current value or default
            value = current_config.get(field.key, field.default_value)

            # Convert validation
            validation = None
            if field.validation:
                validation = ConfigFieldValidation(
                    required=field.validation.required,
                    min_value=field.validation.min_value,
                    max_value=field.validation.max_value,
                    min_length=field.validation.min_length,
                    max_length=field.validation.max_length,
                    pattern=field.validation.pattern,
                )

            # Convert options
            options = None
            if field.options:
                options = [
                    ConfigFieldOption(
                        value=opt.value,
                        label=opt.label,
                        description=opt.description,
                    )
                    for opt in field.options
                ]

            fields.append(
                ConfigFieldResponse(
                    key=field.key,
                    label=field.label,
                    field_type=ConfigFieldType(field.field_type.value),
                    value=value,
                    default_value=field.default_value,
                    description=field.description,
                    validation=validation,
                    options=options,
                    requires_restart=field.requires_restart,
                    sensitive=field.sensitive,
                    depends_on=field.depends_on,
                    depends_on_value=field.depends_on_value,
                )
            )

        result.append(
            ConfigSectionResponse(
                id=section.id,
                label=section.label,
                description=section.description,
                icon=section.icon,
                fields=fields,
                order=section.order,
            )
        )

    return result
