"""
Import / Export API Endpoints
===============================

Comprehensive import/export matching or exceeding FusionDirectory's ldapmanager:

CSV Import:
  - Configurable separator (comma, semicolon, tab)
  - Object type selection (user, group)
  - Template integration (apply template defaults during import)
  - Column mapping (remap CSV headers → LDAP attributes)
  - Fixed values (constant values for all entries)
  - Preview with validation

LDIF Import:
  - Full LDIF file import
  - Overwrite mode (update existing entries)

Export:
  - CSV and LDIF formats
  - Object type selection
  - Field selection
  - LDIF line wrapping (RFC 2849)
  - LDAP filter support

Metadata:
  - Available fields per object type
  - Available templates for import
"""

from typing import Optional

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import PlainTextResponse

from heracles_api.schemas.import_export import (
    AvailableFieldsResponse,
    CsvImportConfigRequest,
    ExportRequest,
    ImportPreviewResponse,
    ImportPreviewRow,
    ImportResultResponse,
    ImportTemplateInfo,
    ImportTemplateListResponse,
    ImportValidationErrorSchema,
    LdifImportResultResponse,
    PluginFieldGroup,
    PluginFieldInfo,
)
from heracles_api.services.import_service import (
    ColumnMapping,
    FixedValue,
    export_users_to_csv,
    export_users_to_ldif,
    get_export_fields_for_type,
    get_fields_for_type,
    import_from_ldif,
    import_users_from_csv,
    parse_csv,
    validate_rows,
)

router = APIRouter(prefix="/import-export", tags=["Import/Export"])


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


@router.get("/fields/{object_type}", response_model=AvailableFieldsResponse)
async def get_available_fields(
    object_type: str,
) -> AvailableFieldsResponse:
    """
    Get available LDAP fields for a given object type.

    Returns required and optional fields that can be used in CSV import/export.
    """
    if object_type not in ("user", "group", "custom"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown object type: {object_type}. Use 'user', 'group', or 'custom'.",
        )

    required, allowed = get_fields_for_type(object_type)
    optional = allowed - required

    # Gather plugin field groups for the response
    from heracles_api.plugins.registry import plugin_registry

    plugin_groups: list[PluginFieldGroup] = []
    import_fields = plugin_registry.get_import_fields_for_type(object_type)
    # Group by plugin_name
    groups_map: dict[str, list[PluginFieldInfo]] = {}
    for pf in import_fields:
        groups_map.setdefault(pf.plugin_name, []).append(
            PluginFieldInfo(
                name=pf.name,
                label=pf.label,
                required=pf.required,
                description=pf.description,
                plugin_name=pf.plugin_name,
            )
        )
    for pname, fields in groups_map.items():
        # Derive a human-readable label from plugin name
        plugin_groups.append(
            PluginFieldGroup(
                plugin_name=pname,
                plugin_label=pname.replace("_", " ").title(),
                fields=fields,
            )
        )

    return AvailableFieldsResponse(
        object_type=object_type,
        required_fields=sorted(required),
        optional_fields=sorted(optional),
        all_fields=sorted(allowed),
        plugin_fields=plugin_groups,
    )


@router.get("/templates", response_model=ImportTemplateListResponse)
async def get_import_templates(
    department_dn: Optional[str] = Query(None, alias="departmentDn"),
) -> ImportTemplateListResponse:
    """
    Get available templates for import.

    Templates can be applied during CSV import to provide default values.
    """
    try:
        from heracles_api.services.template_service import get_template_service
        tmpl_service = get_template_service()
        tmpl_list = await tmpl_service.list_templates(department_dn=department_dn)

        templates = [
            ImportTemplateInfo(
                id=str(t.id),
                name=t.name,
                description=t.description,
                department_dn=t.departmentDn,
            )
            for t in tmpl_list.templates
        ]
    except Exception:
        templates = []

    return ImportTemplateListResponse(templates=templates)


# ---------------------------------------------------------------------------
# CSV Import
# ---------------------------------------------------------------------------


@router.post("/import/preview", response_model=ImportPreviewResponse)
async def preview_import(
    file: UploadFile = File(..., description="CSV file to preview"),
    separator: str = Form(",", description="CSV separator: comma, semicolon, or tab"),
    object_type: str = Form("user", description="Object type: user or group"),
) -> ImportPreviewResponse:
    """
    Preview a CSV file before importing.

    Returns parsed rows with validation status. Supports configurable
    separator and object type (like FusionDirectory).
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .csv files are supported",
        )

    content = await file.read()
    rows, headers = parse_csv(content, separator=separator)

    errors = validate_rows(rows, object_type=object_type)
    error_by_row: dict[int, list[str]] = {}
    for e in errors:
        error_by_row.setdefault(e.row, []).append(f"{e.field}: {e.message}")

    preview_rows = []
    valid_count = 0
    for idx, row in enumerate(rows, start=2):
        row_errors = error_by_row.get(idx, [])
        is_valid = len(row_errors) == 0
        if is_valid:
            valid_count += 1
        preview_rows.append(
            ImportPreviewRow(
                row=idx,
                attributes={k: v.strip() if v else "" for k, v in row.items()},
                valid=is_valid,
                errors=row_errors,
            )
        )

    return ImportPreviewResponse(
        headers=headers,
        rows=preview_rows[:100],
        total_rows=len(rows),
        valid_rows=valid_count,
        invalid_rows=len(rows) - valid_count,
    )


@router.post("/import/csv", response_model=ImportResultResponse)
async def import_csv(
    file: UploadFile = File(..., description="CSV file to import"),
    config_json: str = Form(
        "{}",
        alias="config",
        description="JSON config: object_type, separator, template_id, "
        "column_mapping, fixed_values, default_password, department_dn",
    ),
) -> ImportResultResponse:
    """
    Import entries from a CSV file with full configuration.

    Accepts a multipart form with the file and a JSON config string.
    Config supports all FusionDirectory features and more:
    - object_type: 'user' or 'group'
    - separator: ',' or ';' or '\\t'
    - template_id: apply template defaults
    - column_mapping: remap CSV columns to LDAP attributes
    - fixed_values: constant values for all entries
    - default_password: password for new users
    - department_dn: target container DN
    """
    import json

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .csv files are supported",
        )

    # Parse config
    try:
        config_data = json.loads(config_json)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid config JSON: {e}",
        )

    try:
        config = CsvImportConfigRequest(**config_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid config: {e}",
        )

    # Resolve template defaults if template_id provided
    template_defaults: Optional[dict[str, str]] = None
    template_plugin_activations: Optional[dict] = None
    if config.template_id:
        try:
            import uuid as _uuid
            from heracles_api.services.template_service import get_template_service
            tmpl_service = get_template_service()
            tmpl = await tmpl_service.get_template(_uuid.UUID(config.template_id))
            if tmpl and tmpl.defaults:
                template_defaults = {
                    k: str(v) for k, v in tmpl.defaults.items()
                }
            if tmpl and tmpl.pluginActivations:
                template_plugin_activations = tmpl.pluginActivations
        except Exception:
            pass  # template not found is non-fatal

    # Build column mappings
    col_mappings = None
    if config.column_mapping:
        col_mappings = [
            ColumnMapping(csv_column=m.csv_column, ldap_attribute=m.ldap_attribute)
            for m in config.column_mapping
        ]

    # Build fixed values
    fixed_vals = None
    if config.fixed_values:
        fixed_vals = [
            FixedValue(attribute=fv.attribute, value=fv.value)
            for fv in config.fixed_values
        ]

    content = await file.read()
    result = await import_users_from_csv(
        data=content,
        column_mapping=col_mappings,
        fixed_values=fixed_vals,
        default_password=config.default_password,
        department_dn=config.department_dn,
        object_type=config.object_type,
        template_defaults=template_defaults,
        template_plugin_activations=template_plugin_activations,
        separator=config.separator,
        object_classes=config.object_classes,
        rdn_attribute=config.rdn_attribute,
    )

    return ImportResultResponse(
        total_rows=result.total_rows,
        created=result.created,
        updated=result.updated,
        skipped=result.skipped,
        errors=[
            ImportValidationErrorSchema(row=e.row, field=e.field, message=e.message)
            for e in result.errors
        ],
    )


# Legacy endpoint for backward compatibility
@router.post("/import", response_model=ImportResultResponse)
async def import_users_legacy(
    file: UploadFile = File(..., description="CSV file to import"),
    department_dn: Optional[str] = Query(
        None, alias="departmentDn", description="Target department DN"
    ),
    default_password: Optional[str] = Query(
        None, alias="defaultPassword", description="Default password for new users"
    ),
) -> ImportResultResponse:
    """
    Import users from a CSV file (legacy endpoint).

    Use POST /import/csv for full configuration support.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .csv files are supported",
        )

    content = await file.read()
    result = await import_users_from_csv(
        data=content,
        department_dn=department_dn,
        default_password=default_password,
    )

    return ImportResultResponse(
        total_rows=result.total_rows,
        created=result.created,
        updated=result.updated,
        skipped=result.skipped,
        errors=[
            ImportValidationErrorSchema(row=e.row, field=e.field, message=e.message)
            for e in result.errors
        ],
    )


# ---------------------------------------------------------------------------
# LDIF Import
# ---------------------------------------------------------------------------


@router.post("/import/ldif", response_model=LdifImportResultResponse)
async def import_ldif(
    file: UploadFile = File(..., description="LDIF file to import"),
    overwrite: bool = Form(
        False, description="Overwrite existing entries (like FD's overwrite toggle)"
    ),
) -> LdifImportResultResponse:
    """
    Import entries from an LDIF file.

    Like FusionDirectory's LDIF import:
    - Parses standard LDIF format
    - Creates new entries in LDAP
    - If overwrite=True, updates existing entries
    - If overwrite=False, skips existing entries
    - Supports base64-encoded values and continuation lines
    """
    if not file.filename or not (
        file.filename.lower().endswith(".ldif")
        or file.filename.lower().endswith(".ldf")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .ldif or .ldf files are supported",
        )

    content = await file.read()
    result = await import_from_ldif(data=content, overwrite=overwrite)

    return LdifImportResultResponse(
        total_entries=result.total_rows,
        created=result.created,
        updated=result.updated,
        skipped=result.skipped,
        errors=[
            ImportValidationErrorSchema(row=e.row, field=e.field, message=e.message)
            for e in result.errors
        ],
    )


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


@router.post("/export")
async def export_entries(body: ExportRequest) -> PlainTextResponse:
    """
    Export LDAP entries as CSV or LDIF.

    Supports:
    - Object type presets (user, group) — like FD
    - No object type — raw LDAP export of any subtree / filter
    - Field selection — choose which attributes to export
    - LDIF line wrapping — configurable per RFC 2849
    - LDAP filter — custom search filter
    - Department DN — search base
    """
    from heracles_api.config import settings
    from heracles_api.services import get_ldap_service

    ldap = get_ldap_service()

    # Determine defaults based on object_type (if provided)
    if body.object_type == "group":
        from heracles_api.core.ldap_config import get_full_groups_dn
        default_base = get_full_groups_dn(settings.LDAP_BASE_DN)
        default_filter = "(objectClass=groupOfNames)"
        type_fields = get_export_fields_for_type("group")
    elif body.object_type == "user":
        from heracles_api.core.ldap_config import get_full_users_dn
        default_base = get_full_users_dn(settings.LDAP_BASE_DN)
        default_filter = "(objectClass=inetOrgPerson)"
        type_fields = get_export_fields_for_type("user")
    else:
        # Generic / raw LDAP export — any object
        default_base = settings.LDAP_BASE_DN
        default_filter = "(objectClass=*)"
        type_fields = None  # no preset field list

    search_base = body.department_dn or default_base
    search_filter = body.filter or default_filter

    # Fetch entries from LDAP
    entries = await ldap.search(
        search_base=search_base,
        search_filter=search_filter,
    )

    # Determine fields to export
    if body.fields:
        export_fields = body.fields
    elif type_fields is not None:
        export_fields = sorted(type_fields)
    else:
        # Generic mode: collect all attribute names found across entries
        all_keys: set[str] = set()
        for entry in entries:
            all_keys.update(entry.attributes.keys())
        all_keys.discard("dn")
        export_fields = sorted(all_keys)

    # Convert to plain dicts
    items = []
    for entry in entries:
        item_dict: dict = {"dn": entry.dn}
        for attr in export_fields:
            val = entry.get_first(attr)
            if val:
                item_dict[attr] = val
        items.append(item_dict)

    if body.format == "ldif":
        output = export_users_to_ldif(items, wrap=body.ldif_wrap)
        media_type = "application/ldif"
    else:
        output = export_users_to_csv(items, fields=export_fields)
        media_type = "text/csv"

    return PlainTextResponse(content=output, media_type=media_type)
