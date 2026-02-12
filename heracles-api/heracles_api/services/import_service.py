"""
Import / Export Service
========================

Business logic for bulk importing users/groups via CSV and LDIF,
and exporting entries as CSV/LDIF.

Matches or exceeds FusionDirectory's ldapmanager plugin:
- CSV: separator config, column mapping, fixed values, template integration
- LDIF: import with overwrite mode, line-wrapped export
- Object types: users and groups
"""

import csv
import io
import re
from dataclasses import dataclass, field
from typing import Any

import structlog

from heracles_api.services.audit_service import get_audit_service

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Password hashing helper
# ---------------------------------------------------------------------------

# Known LDAP password scheme prefixes (case-insensitive check)
_KNOWN_HASH_PREFIXES = (
    "{ARGON2}",
    "{SSHA}",
    "{SSHA256}",
    "{SSHA512}",
    "{SHA}",
    "{SHA256}",
    "{SHA512}",
    "{SMD5}",
    "{MD5}",
    "{BCRYPT}",
    "{CRYPT}",
    "{LOCKED}",
)


def _is_already_hashed(value: str) -> bool:
    """Return True if the password value already has an LDAP hash scheme prefix."""
    upper = value.upper()
    return any(upper.startswith(prefix) for prefix in _KNOWN_HASH_PREFIXES)


async def _hash_password_if_needed(password: str, ldap_service: Any) -> str:
    """Hash a password using the configured algorithm, unless it is already hashed.

    This is the single enforcement point that ensures **no** import code-path
    can write a cleartext password to LDAP.
    """
    if _is_already_hashed(password):
        return password

    from heracles_api.core.password_policy import get_password_hash_algorithm

    algorithm = await get_password_hash_algorithm()
    return ldap_service._hash_password(password, algorithm)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ImportValidationError:
    """Single validation error for an import row."""

    row: int
    field: str
    message: str


@dataclass
class ImportResult:
    """Result of a bulk import operation."""

    total_rows: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[ImportValidationError] = field(default_factory=list)


@dataclass
class ColumnMapping:
    """Mapping of CSV column header → LDAP attribute name."""

    csv_column: str
    ldap_attribute: str


@dataclass
class FixedValue:
    """A fixed LDAP attribute value applied to every entry."""

    attribute: str
    value: str


# ---------------------------------------------------------------------------
# Field definitions per object type
# ---------------------------------------------------------------------------

USER_REQUIRED_FIELDS = {"uid", "cn", "sn"}
USER_ALLOWED_FIELDS = {
    "uid",
    "cn",
    "sn",
    "givenName",
    "displayName",
    "mail",
    "telephoneNumber",
    "title",
    "description",
    "userPassword",
    "uidNumber",
    "gidNumber",
    "homeDirectory",
    "loginShell",
    "employeeNumber",
    "employeeType",
    "departmentNumber",
    "postalAddress",
    "street",
    "l",
    "st",
    "postalCode",
    "c",
    "o",
    "ou",
    "mobile",
    "facsimileTelephoneNumber",
    "jpegPhoto",
    "labeledURI",
    "preferredLanguage",
}

GROUP_REQUIRED_FIELDS = {"cn"}
GROUP_ALLOWED_FIELDS = {
    "cn",
    "description",
    "member",
    "owner",
    "businessCategory",
    "seeAlso",
    "ou",
    "o",
}

# Legacy alias for backward compatibility
REQUIRED_FIELDS = USER_REQUIRED_FIELDS
ALLOWED_FIELDS = USER_ALLOWED_FIELDS


def get_fields_for_type(
    object_type: str,
) -> tuple[set[str], set[str]]:
    """Return (required_fields, allowed_fields) for the given object type.

    For ``user`` and ``group`` types the core fields are augmented with
    any fields contributed by active plugins (via the plugin registry).
    """
    if object_type == "custom":
        return set(), set()  # no preset for custom type

    base_req = USER_REQUIRED_FIELDS if object_type != "group" else GROUP_REQUIRED_FIELDS
    base_all = USER_ALLOWED_FIELDS.copy() if object_type != "group" else GROUP_ALLOWED_FIELDS.copy()

    # Merge plugin-contributed fields
    try:
        from heracles_api.plugins.registry import plugin_registry

        for field_def in plugin_registry.get_import_fields_for_type(object_type):
            base_all.add(field_def.name)
    except Exception:
        pass  # registry may not be initialised during tests

    return base_req, base_all


def get_export_fields_for_type(
    object_type: str,
) -> set[str]:
    """Return all exportable fields for the given object type.

    Like ``get_fields_for_type`` but uses the plugin registry's
    *export* field list which may include extra read-only attributes
    (e.g. POSIX shadow fields).
    """
    if object_type == "custom":
        return set()

    base = USER_ALLOWED_FIELDS.copy() if object_type != "group" else GROUP_ALLOWED_FIELDS.copy()

    try:
        from heracles_api.plugins.registry import plugin_registry

        for field_def in plugin_registry.get_export_fields_for_type(object_type):
            base.add(field_def.name)
    except Exception:
        pass

    return base


# ---------------------------------------------------------------------------
# CSV Parsing
# ---------------------------------------------------------------------------


def parse_csv(
    data: str | bytes,
    separator: str = ",",
) -> tuple[list[dict[str, str]], list[str]]:
    """
    Parse CSV data and return (rows, headers).

    Accepts either a string or bytes (UTF-8 decoded).
    Supports configurable separator (comma, semicolon, tab).
    """
    if isinstance(data, bytes):
        data = data.decode("utf-8-sig")  # handle BOM

    # Skip comment lines (like FD does)
    lines = data.splitlines()
    clean_lines = [line for line in lines if not line.strip().startswith("#")]
    clean_data = "\n".join(clean_lines)

    reader = csv.DictReader(io.StringIO(clean_data), delimiter=separator)
    headers = reader.fieldnames or []
    rows = list(reader)
    return rows, headers


# ---------------------------------------------------------------------------
# CSV Row Validation
# ---------------------------------------------------------------------------


def validate_rows(
    rows: list[dict[str, str]],
    column_mapping: list[ColumnMapping] | None = None,
    fixed_values: list[FixedValue] | None = None,
    object_type: str = "user",
) -> list[ImportValidationError]:
    """
    Validate parsed CSV rows.

    Returns a list of validation errors (empty == all valid).
    Supports column mapping and fixed values (FD-style).
    """
    errors: list[ImportValidationError] = []
    required, allowed = get_fields_for_type(object_type)

    # Build mapping dict
    mapping = {m.csv_column: m.ldap_attribute for m in (column_mapping or [])}
    fixed = {fv.attribute: fv.value for fv in (fixed_values or [])}

    for idx, row in enumerate(rows, start=2):  # row 1 is header
        # Apply mapping
        mapped: dict[str, str] = {}
        for col, val in row.items():
            attr = mapping.get(col, col)
            mapped[attr] = val.strip() if val else ""

        # Merge fixed values (fixed values override CSV values like FD)
        for attr, val in fixed.items():
            mapped[attr] = val

        # Required fields check
        for req in required:
            if not mapped.get(req):
                errors.append(
                    ImportValidationError(
                        row=idx,
                        field=req,
                        message=f"Missing required field: {req}",
                    )
                )

        # Object-type-specific validations
        if object_type == "user":
            # Validate uid format
            uid = mapped.get("uid", "")
            if uid and not re.match(r"^[a-zA-Z][a-zA-Z0-9._-]{0,63}$", uid):
                errors.append(ImportValidationError(row=idx, field="uid", message="Invalid uid format"))

            # Validate mail format
            mail = mapped.get("mail", "")
            if mail and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", mail):
                errors.append(ImportValidationError(row=idx, field="mail", message="Invalid email format"))

        elif object_type == "group":
            cn = mapped.get("cn", "")
            if cn and not re.match(r"^[a-zA-Z][a-zA-Z0-9._-]{0,63}$", cn):
                errors.append(ImportValidationError(row=idx, field="cn", message="Invalid group cn format"))

    return errors


# ---------------------------------------------------------------------------
# CSV Import
# ---------------------------------------------------------------------------


async def import_users_from_csv(
    data: str | bytes,
    column_mapping: list[ColumnMapping] | None = None,
    fixed_values: list[FixedValue] | None = None,
    default_password: str | None = None,
    department_dn: str | None = None,
    object_type: str = "user",
    template_defaults: dict[str, str] | None = None,
    separator: str = ",",
    actor_dn: str | None = None,
    ldap_service: Any = None,
    object_classes: list[str] | None = None,
    rdn_attribute: str | None = None,
    template_plugin_activations: dict[str, Any] | None = None,
) -> ImportResult:
    """
    Parse, validate, and create entries from CSV data.

    Supports:
    - Column mapping (remap CSV headers → LDAP attributes)
    - Fixed values (constant values for all rows)
    - Template defaults (from Heracles templates)
    - Separator configuration
    - Object type: user, group, or custom (with object_classes + rdn_attribute)
    """
    rows, headers = parse_csv(data, separator=separator)
    result = ImportResult(total_rows=len(rows))

    if object_type == "custom":
        # Custom type: no preset field restrictions
        allowed = None  # accept everything
    else:
        _, allowed = get_fields_for_type(object_type)

    # Build mapping
    mapping = {m.csv_column: m.ldap_attribute for m in (column_mapping or [])}
    fixed = {fv.attribute: fv.value for fv in (fixed_values or [])}

    # Validate (skip for custom type — no schema to validate against)
    if object_type != "custom":
        errors = validate_rows(rows, column_mapping, fixed_values, object_type)
    else:
        errors = []
    if errors:
        result.errors = errors
        return result

    if ldap_service is None:
        from heracles_api.services import get_ldap_service

        ldap_service = get_ldap_service()

    for idx, row in enumerate(rows, start=2):
        # Apply mapping
        mapped: dict[str, str] = {}
        for col, val in row.items():
            attr = mapping.get(col, col)
            mapped[attr] = val.strip() if val else ""

        # Merge template defaults (lowest priority)
        if template_defaults:
            for attr, val in template_defaults.items():
                if attr not in mapped or not mapped[attr]:
                    mapped[attr] = val

        # Merge fixed values (highest priority — override everything)
        for attr, val in fixed.items():
            mapped[attr] = val

        entity_id = mapped.get("uid" if object_type == "user" else "cn", "")
        try:
            if object_type == "custom":
                # Generic / custom object — accept all non-empty attributes
                attrs = {k: v for k, v in mapped.items() if v}
                if not object_classes:
                    raise ValueError("object_classes is required for custom object type")
                if not rdn_attribute:
                    raise ValueError("rdn_attribute is required for custom object type")
                if default_password and "userPassword" not in attrs:
                    attrs["userPassword"] = await _hash_password_if_needed(
                        default_password,
                        ldap_service,
                    )
                await _create_generic_entry(
                    ldap_service,
                    attrs,
                    department_dn,
                    object_classes=object_classes,
                    rdn_attribute=rdn_attribute,
                )
                entity_id = mapped.get(rdn_attribute, "")
            else:
                # Build attributes (only allowed fields for known types)
                attrs = {k: v for k, v in mapped.items() if v and k in allowed}

                if object_type == "user":
                    if default_password and "userPassword" not in attrs:
                        attrs["userPassword"] = await _hash_password_if_needed(
                            default_password,
                            ldap_service,
                        )
                    await _create_user_entry(ldap_service, attrs, department_dn)
                    entity_id = mapped.get("uid", "")

                    # --- Plugin activation (Phase C) ---
                    uid = mapped.get("uid", "")
                    user_dn = _build_user_dn(uid, department_dn)
                    await _activate_plugins_for_import(
                        ldap_service,
                        user_dn,
                        uid,
                        attrs,
                        plugin_activations=template_plugin_activations,
                    )
                elif object_type == "group":
                    await _create_group_entry(ldap_service, attrs, department_dn)
                    entity_id = mapped.get("cn", "")

            result.created += 1

            # Audit success
            try:
                audit = get_audit_service()
                await audit.log_action(
                    actor_dn=actor_dn or "system",
                    action="import",
                    entity_type=object_type,
                    entity_id=entity_id,
                    entity_name=mapped.get("cn", entity_id),
                    department_dn=department_dn,
                    status="success",
                )
            except Exception:
                pass  # audit failures are non-critical

        except Exception as e:
            logger.warning(
                "import_entry_failed",
                object_type=object_type,
                entity_id=entity_id,
                error=str(e),
            )
            result.errors.append(ImportValidationError(row=idx, field=entity_id, message=str(e)))
            result.skipped += 1

            # Audit failure
            try:
                audit = get_audit_service()
                await audit.log_action(
                    actor_dn=actor_dn or "system",
                    action="import",
                    entity_type=object_type,
                    entity_id=entity_id,
                    entity_name=mapped.get("cn", entity_id),
                    department_dn=department_dn,
                    status="failure",
                    error_message=str(e),
                )
            except Exception:
                pass

    return result


def _build_user_dn(uid: str, department_dn: str | None) -> str:
    """Build the DN for a user entry (reused by import + plugin activation)."""
    from heracles_api.config import settings
    from heracles_api.core.ldap_config import get_full_users_dn

    base = department_dn or get_full_users_dn(settings.LDAP_BASE_DN)
    return f"uid={uid},{base}"


# ---------------------------------------------------------------------------
# Post-import plugin activation
# ---------------------------------------------------------------------------

# Map of LDAP attributes → plugin name for auto-detection
_POSIX_INDICATOR_ATTRS = {"uidNumber", "gidNumber", "homeDirectory", "loginShell"}
_SSH_INDICATOR_ATTRS = {"sshPublicKey"}
_MAIL_INDICATOR_ATTRS = {"hrcMailServer", "hrcMailQuota", "hrcMailAlternateAddress"}


async def _activate_plugins_for_import(
    ldap_service: Any,
    dn: str,
    uid: str,
    attrs: dict[str, str],
    plugin_activations: dict[str, Any] | None = None,
) -> None:
    """
    Activate plugins on a freshly imported user entry.

    Activation sources (in order of priority):
    1. Explicit ``plugin_activations`` from template (e.g. ``{"posix": {"loginShell": "/bin/bash"}}``)
    2. Auto-detection from imported attributes (e.g. uidNumber present → activate posix)

    Plugin activation failures are logged but *never* fail the import row.
    """
    from heracles_api.plugins.registry import plugin_registry

    plugins_to_activate: dict[str, dict[str, Any]] = {}

    # 1. Explicit template activations
    if plugin_activations:
        for plugin_name, activation_data in plugin_activations.items():
            if isinstance(activation_data, dict):
                plugins_to_activate[plugin_name] = activation_data
            elif activation_data is True:
                plugins_to_activate[plugin_name] = {}

    # 2. Auto-detection from attributes (only if not already explicitly set)
    present = set(attrs.keys())
    if "posix" not in plugins_to_activate and present & _POSIX_INDICATOR_ATTRS:
        posix_data: dict[str, Any] = {}
        if "loginShell" in attrs:
            posix_data["loginShell"] = attrs["loginShell"]
        if "homeDirectory" in attrs:
            posix_data["homeDirectory"] = attrs["homeDirectory"]
        if "gidNumber" in attrs:
            posix_data["gidNumber"] = int(attrs["gidNumber"])
        if "uidNumber" in attrs:
            posix_data["uidNumber"] = int(attrs["uidNumber"])
        plugins_to_activate["posix"] = posix_data

    if "ssh" not in plugins_to_activate and present & _SSH_INDICATOR_ATTRS:
        plugins_to_activate["ssh"] = {}

    if "mail" not in plugins_to_activate and present & _MAIL_INDICATOR_ATTRS:
        mail_data: dict[str, Any] = {}
        if "mail" in attrs:
            mail_data["mail"] = attrs["mail"]
        plugins_to_activate["mail"] = mail_data

    # 3. Actually activate each plugin
    for plugin_name, activation_data in plugins_to_activate.items():
        try:
            service = plugin_registry.get_service_for_plugin(plugin_name, "user")
            if service is None:
                logger.debug("import_plugin_not_found", plugin=plugin_name)
                continue

            # Check if already active (shouldn't be, but be safe)
            if await service.is_active(dn):
                continue

            # Build activation data - pass as a dict, let the service handle it
            await service.activate(dn, activation_data)
            logger.info(
                "import_plugin_activated",
                plugin=plugin_name,
                uid=uid,
            )
        except Exception as exc:
            logger.warning(
                "import_plugin_activation_failed",
                plugin=plugin_name,
                uid=uid,
                error=str(exc),
            )
            # Non-fatal: user was created, just plugin activation failed


async def _create_user_entry(
    ldap_service: Any,
    attrs: dict[str, str],
    department_dn: str | None,
) -> None:
    """Create a user entry in LDAP.

    Safety-net: if ``userPassword`` is present and not yet hashed,
    it will be hashed before writing to LDAP.
    """
    from heracles_api.config import settings
    from heracles_api.core.ldap_config import get_full_users_dn

    uid = attrs.get("uid", "")
    base = department_dn or get_full_users_dn(settings.LDAP_BASE_DN)
    dn = f"uid={uid},{base}"

    # --- Safety-net: hash any plaintext password before writing to LDAP ---
    if "userPassword" in attrs:
        attrs["userPassword"] = await _hash_password_if_needed(
            attrs["userPassword"],
            ldap_service,
        )

    object_classes = ["inetOrgPerson", "organizationalPerson", "person"]

    # Remove uid from attrs since it's in the DN
    entry_attrs = {k: [v] for k, v in attrs.items() if k != "uid"}
    entry_attrs["uid"] = [uid]

    await ldap_service.add(
        dn=dn,
        object_classes=object_classes,
        attributes=entry_attrs,
    )


async def _create_group_entry(
    ldap_service: Any,
    attrs: dict[str, str],
    department_dn: str | None,
) -> None:
    """Create a group entry in LDAP."""
    from heracles_api.config import settings
    from heracles_api.core.ldap_config import get_full_groups_dn

    cn = attrs.get("cn", "")
    base = department_dn or get_full_groups_dn(settings.LDAP_BASE_DN)
    dn = f"cn={cn},{base}"

    object_classes = ["groupOfNames"]

    entry_attrs = {k: [v] for k, v in attrs.items() if k != "cn"}
    entry_attrs["cn"] = [cn]
    # groupOfNames requires at least one member
    if "member" not in entry_attrs:
        entry_attrs["member"] = [dn]  # self-reference as placeholder

    await ldap_service.add(
        dn=dn,
        object_classes=object_classes,
        attributes=entry_attrs,
    )


async def _create_generic_entry(
    ldap_service: Any,
    attrs: dict[str, str],
    department_dn: str | None,
    object_classes: list[str],
    rdn_attribute: str,
) -> None:
    """Create a generic LDAP entry with user-supplied objectClasses and RDN."""
    from heracles_api.config import settings

    rdn_value = attrs.get(rdn_attribute, "")
    if not rdn_value:
        raise ValueError(f"RDN attribute '{rdn_attribute}' is empty or missing")

    base = department_dn or settings.LDAP_BASE_DN
    dn = f"{rdn_attribute}={rdn_value},{base}"

    entry_attrs = {k: [v] for k, v in attrs.items() if k != rdn_attribute}
    entry_attrs[rdn_attribute] = [rdn_value]

    await ldap_service.add(
        dn=dn,
        object_classes=object_classes,
        attributes=entry_attrs,
    )


# ---------------------------------------------------------------------------
# LDIF Parsing & Import
# ---------------------------------------------------------------------------


def parse_ldif(data: str | bytes) -> list[dict[str, Any]]:
    """
    Parse LDIF data into a list of entry dicts.

    Each entry dict has:
    - 'dn': str
    - attributes: {attr_name: [values]}

    Handles:
    - Continuation lines (lines starting with a single space)
    - Comment lines (starting with #)
    - Base64-encoded values (attr:: value)
    - Multiple entries separated by blank lines
    """
    import base64

    if isinstance(data, bytes):
        data = data.decode("utf-8-sig")

    entries: list[dict[str, Any]] = []
    current_lines: list[str] = []

    def _flush_entry(lines: list[str]) -> dict[str, Any] | None:
        if not lines:
            return None

        # Join continuation lines
        joined: list[str] = []
        for line in lines:
            if line.startswith(" ") and joined:
                joined[-1] += line[1:]  # continuation
            else:
                joined.append(line)

        entry: dict[str, Any] = {}
        dn = ""

        for line in joined:
            if not line or line.startswith("#"):
                continue

            # Skip changetype lines
            if line.lower().startswith("changetype:"):
                continue

            # Check for base64 encoding (attr:: value)
            if ":: " in line:
                attr, val_b64 = line.split(":: ", 1)
                attr = attr.strip()
                try:
                    val = base64.b64decode(val_b64.strip()).decode("utf-8")
                except Exception:
                    val = val_b64.strip()
            elif ": " in line:
                attr, val = line.split(": ", 1)
                attr = attr.strip()
                val = val.strip()
            else:
                continue

            if attr.lower() == "dn":
                dn = val
                continue

            if attr not in entry:
                entry[attr] = []
            entry[attr].append(val)

        if dn:
            entry["dn"] = dn
            return entry
        return None

    for line in data.splitlines():
        if line.strip() == "":
            entry = _flush_entry(current_lines)
            if entry:
                entries.append(entry)
            current_lines = []
        else:
            current_lines.append(line)

    # Flush last entry
    entry = _flush_entry(current_lines)
    if entry:
        entries.append(entry)

    return entries


async def import_from_ldif(
    data: str | bytes,
    overwrite: bool = False,
    actor_dn: str | None = None,
    ldap_service: Any = None,
) -> ImportResult:
    """
    Import entries from LDIF data.

    Like FusionDirectory's import_complete_ldif:
    - Parses LDIF
    - Creates entries in LDAP
    - If overwrite=True, modifies existing entries
    - If overwrite=False, skips existing entries
    """
    entries = parse_ldif(data)
    result = ImportResult(total_rows=len(entries))

    if ldap_service is None:
        from heracles_api.services import get_ldap_service

        ldap_service = get_ldap_service()

    for idx, entry in enumerate(entries, start=1):
        dn = entry.pop("dn", "")
        if not dn:
            result.errors.append(ImportValidationError(row=idx, field="dn", message="Entry has no DN"))
            result.skipped += 1
            continue

        try:
            # --- Hash any plaintext userPassword in LDIF entries ---
            if "userPassword" in entry:
                pw_values = entry["userPassword"]
                hashed_values = []
                for pw in pw_values if isinstance(pw_values, list) else [pw_values]:
                    hashed_values.append(await _hash_password_if_needed(str(pw), ldap_service))
                entry["userPassword"] = hashed_values

            # Check if entry already exists
            existing = await ldap_service.get_by_dn(dn)

            if existing:
                if overwrite:
                    # Build modify changes (replace all attributes)
                    changes = {}
                    for attr, values in entry.items():
                        changes[attr] = ("replace", values)
                    await ldap_service.modify(dn=dn, changes=changes)
                    result.updated += 1
                    logger.info("ldif_entry_updated", dn=dn)
                else:
                    result.skipped += 1
                    logger.debug("ldif_entry_skipped_exists", dn=dn)
                    continue
            else:
                # Extract objectClass for add()
                object_classes = entry.pop("objectClass", ["top"])
                await ldap_service.add(
                    dn=dn,
                    object_classes=object_classes,
                    attributes=entry,
                )
                result.created += 1
                logger.info("ldif_entry_created", dn=dn)

            # Audit
            try:
                audit = get_audit_service()
                # Infer entity type from DN
                entity_type = "user" if "uid=" in dn else "group" if "cn=" in dn else "entry"
                entity_id = dn.split(",")[0].split("=", 1)[1] if "=" in dn else dn
                await audit.log_action(
                    actor_dn=actor_dn or "system",
                    action="import",
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity_name=entity_id,
                    status="success",
                )
            except Exception:
                pass

        except Exception as e:
            logger.warning("ldif_import_failed", dn=dn, error=str(e))
            result.errors.append(ImportValidationError(row=idx, field="dn", message=f"{dn}: {e}"))
            result.skipped += 1

            # Audit failure
            try:
                audit = get_audit_service()
                entity_type = "user" if "uid=" in dn else "group" if "cn=" in dn else "entry"
                entity_id = dn.split(",")[0].split("=", 1)[1] if "=" in dn else dn
                await audit.log_action(
                    actor_dn=actor_dn or "system",
                    action="import",
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity_name=entity_id,
                    status="failure",
                    error_message=str(e),
                )
            except Exception:
                pass

    return result


# ---------------------------------------------------------------------------
# CSV Export
# ---------------------------------------------------------------------------


def export_users_to_csv(
    users: list[dict[str, Any]],
    fields: list[str] | None = None,
) -> str:
    """Export entries to CSV format."""
    if not users:
        return ""

    if fields is None:
        # Collect all unique keys across all entries
        all_keys: set[str] = set()
        for u in users:
            all_keys.update(u.keys())
        all_keys.discard("dn")
        fields = sorted(all_keys)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for user in users:
        writer.writerow(user)
    return output.getvalue()


# ---------------------------------------------------------------------------
# LDIF Export
# ---------------------------------------------------------------------------


def export_users_to_ldif(
    users: list[dict[str, Any]],
    base_dn: str = "",
    wrap: int = 76,
) -> str:
    """
    Export a list of entry attribute dicts to LDIF format.

    Each entry dict should have at least 'dn' and attribute key/value pairs.

    Args:
        users: List of entry dicts.
        base_dn: Optional base DN (unused, kept for compat).
        wrap: Line wrap width for LDIF (0=no wrap). Default 76 per RFC 2849.
    """
    lines: list[str] = []
    for user in users:
        dn = user.get("dn", "")
        lines.append(_ldif_line("dn", dn, wrap))

        for key, val in user.items():
            if key == "dn":
                continue
            if isinstance(val, list):
                for v in val:
                    lines.append(_ldif_line(key, str(v), wrap))
            else:
                lines.append(_ldif_line(key, str(val), wrap))
        lines.append("")  # blank line between entries

    return "\n".join(lines)


def _ldif_line(attr: str, value: str, wrap: int = 76) -> str:
    """
    Format a single LDIF attribute line with optional wrapping.

    Per RFC 2849:
    - Lines > wrap chars are continued on next line with leading space
    - Non-ASCII or binary values are base64-encoded (attr:: value)
    """
    import base64

    # Check if value needs base64 encoding
    needs_b64 = False
    try:
        value.encode("ascii")
        if value and (value[0] in (" ", ":", "<") or value[-1] == " " or "\n" in value):
            needs_b64 = True
    except UnicodeEncodeError:
        needs_b64 = True

    if needs_b64:
        b64 = base64.b64encode(value.encode("utf-8")).decode("ascii")
        line = f"{attr}:: {b64}"
    else:
        line = f"{attr}: {value}"

    if wrap <= 0 or len(line) <= wrap:
        return line

    # Wrap: first line at `wrap`, continuations at `wrap - 1` (leading space)
    result = line[:wrap]
    remaining = line[wrap:]
    while remaining:
        chunk = remaining[: wrap - 1]
        result += "\n " + chunk
        remaining = remaining[wrap - 1 :]

    return result
