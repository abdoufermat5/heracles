"""
Import / Export Pydantic Schemas
=================================

Request/response models for import/export operations.

Matches or exceeds FusionDirectory's ldapmanager plugin capabilities:
- CSV import with separator config, template integration, column mapping, fixed values
- LDIF import with overwrite mode
- CSV/LDIF export with field selection and object type support
"""

from typing import Literal

from pydantic import BaseModel, Field, validator

# ---------------------------------------------------------------------------
# Shared / Enums
# ---------------------------------------------------------------------------

ObjectType = Literal["user", "group", "custom"]
ExportFormat = Literal["csv", "ldif"]
CsvSeparator = Literal[",", ";", "\t"]


# ---------------------------------------------------------------------------
# Column Mapping
# ---------------------------------------------------------------------------


class ColumnMappingSchema(BaseModel):
    """CSV column to LDAP attribute mapping."""

    csv_column: str = Field(alias="csv_column")
    ldap_attribute: str = Field(alias="ldap_attribute")

    class Config:
        populate_by_name = True


# ---------------------------------------------------------------------------
# Fixed Value
# ---------------------------------------------------------------------------


class FixedValueSchema(BaseModel):
    """A fixed LDAP attribute value applied to every imported entry."""

    attribute: str
    value: str


# ---------------------------------------------------------------------------
# CSV Import Schemas
# ---------------------------------------------------------------------------


class CsvImportConfigRequest(BaseModel):
    """Configuration for CSV import (sent as JSON alongside file)."""

    object_type: ObjectType = Field("user", alias="object_type")
    separator: CsvSeparator = Field(",", alias="separator")
    template_id: str | None = Field(None, alias="template_id")
    column_mapping: list[ColumnMappingSchema] | None = Field(None, alias="column_mapping")
    fixed_values: list[FixedValueSchema] | None = Field(None, alias="fixed_values")
    default_password: str | None = Field(None, alias="default_password")
    department_dn: str | None = Field(None, alias="department_dn")
    object_classes: list[str] | None = Field(
        None,
        alias="object_classes",
        description="Custom objectClass list for generic imports (required when object_type='custom')",
    )
    rdn_attribute: str | None = Field(
        None,
        alias="rdn_attribute",
        description="RDN attribute name for building DN (e.g. 'cn', 'uid'). Required when object_type='custom'.",
    )

    class Config:
        populate_by_name = True

    @validator("column_mapping", pre=True)
    @classmethod
    def _normalize_column_mapping(cls, v: object) -> list[dict[str, str]] | None:
        """Accept both dict and list formats for column_mapping.

        Dict format:  {"uid": "uid", "cn": "cn"}
        List format:  [{"csv_column": "uid", "ldap_attribute": "uid"}, ...]
        """
        if v is None:
            return v
        if isinstance(v, dict):
            return [{"csv_column": k, "ldap_attribute": val} for k, val in v.items()]
        return v


class ImportValidationErrorSchema(BaseModel):
    """Single row validation error."""

    row: int
    field: str
    message: str


class ImportResultResponse(BaseModel):
    """Result of a bulk import operation (CSV or LDIF)."""

    total_rows: int = Field(0, alias="total_rows")
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[ImportValidationErrorSchema] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class ImportPreviewRow(BaseModel):
    """A single row in the import preview."""

    row: int
    attributes: dict[str, str]
    valid: bool
    errors: list[str] = Field(default_factory=list)


class ImportPreviewResponse(BaseModel):
    """Preview of a CSV file before import."""

    headers: list[str]
    rows: list[ImportPreviewRow]
    total_rows: int = Field(alias="total_rows")
    valid_rows: int = Field(alias="valid_rows")
    invalid_rows: int = Field(alias="invalid_rows")

    class Config:
        populate_by_name = True


# ---------------------------------------------------------------------------
# LDIF Import Schemas
# ---------------------------------------------------------------------------


class LdifImportRequest(BaseModel):
    """Configuration for LDIF import."""

    overwrite: bool = Field(
        False,
        description="If true, existing entries will be overwritten. If false, existing entries are skipped.",
    )

    class Config:
        populate_by_name = True


class LdifImportResultResponse(BaseModel):
    """Result of an LDIF import operation."""

    total_entries: int = Field(0, alias="total_entries")
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[ImportValidationErrorSchema] = Field(default_factory=list)

    class Config:
        populate_by_name = True


# ---------------------------------------------------------------------------
# Export Schemas
# ---------------------------------------------------------------------------


class ExportRequest(BaseModel):
    """Request body for export."""

    format: ExportFormat = Field("csv", description="Export format: csv or ldif")
    object_type: ObjectType | None = Field(
        None,
        alias="object_type",
        description="Object type preset (user, group) or null for raw LDAP export. "
        "When null, department_dn and filter must be provided.",
    )
    fields: list[str] | None = Field(None, description="Specific fields to include. None = all attributes found.")
    department_dn: str | None = Field(
        None,
        alias="department_dn",
        description="Search base DN. Defaults to LDAP base DN when no object_type.",
    )
    filter: str | None = Field(
        None,
        description="LDAP search filter. Defaults to (objectClass=*) when no object_type.",
    )
    ldif_wrap: int = Field(
        76,
        alias="ldif_wrap",
        description="LDIF line wrap width (0 = no wrap). Default 76 per RFC 2849.",
    )

    class Config:
        populate_by_name = True


# ---------------------------------------------------------------------------
# Metadata Schemas
# ---------------------------------------------------------------------------


class PluginFieldInfo(BaseModel):
    """Field contributed by a plugin."""

    name: str
    label: str
    required: bool = False
    description: str | None = None
    plugin_name: str = Field(alias="plugin_name")

    class Config:
        populate_by_name = True


class PluginFieldGroup(BaseModel):
    """Group of fields contributed by a single plugin."""

    plugin_name: str = Field(alias="plugin_name")
    plugin_label: str = Field(alias="plugin_label")
    fields: list[PluginFieldInfo]

    class Config:
        populate_by_name = True


class AvailableFieldsResponse(BaseModel):
    """Available LDAP fields for a given object type."""

    object_type: str = Field(alias="object_type")
    required_fields: list[str] = Field(alias="required_fields")
    optional_fields: list[str] = Field(alias="optional_fields")
    all_fields: list[str] = Field(alias="all_fields")
    plugin_fields: list[PluginFieldGroup] = Field(default_factory=list, alias="plugin_fields")

    class Config:
        populate_by_name = True


class ImportTemplateInfo(BaseModel):
    """Minimal template info for import template picker."""

    id: str
    name: str
    description: str | None = None
    department_dn: str | None = Field(None, alias="department_dn")

    class Config:
        populate_by_name = True


class ImportTemplateListResponse(BaseModel):
    """List of templates available for import."""

    templates: list[ImportTemplateInfo]

    class Config:
        populate_by_name = True
