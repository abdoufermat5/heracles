# Plugin Schema Organization

This document explains Heracles plugin structure.

## Plugin Directory Structure

Each plugin follows this normalized structure:

```
heracles_plugins/heracles_plugins/<plugin_name>/
├── __init__.py              # Plugin exports
├── plugin.py                # Plugin class definition
├── plugin.yaml              # Plugin metadata (NEW)
├── routes.py                # FastAPI router
├── schemas.py               # Pydantic schemas (API)
├── schema_*.json            # JSON Schema files (UI forms)
├── ldap/                    # LDAP schemas (NEW)
│   ├── <name>.schema        # Traditional format
│   └── <name>.ldif          # cn=config format
├── service/                 # Business logic
│   └── ...
├── docs/                    # Plugin documentation
│   └── ...
└── tests/                   # Plugin tests
    └── ...
```

## plugin.yaml Format

Each plugin declares its metadata in `plugin.yaml`:

```yaml
# Plugin Metadata
information:
  name: ssh
  version: "1.0.0"
  description: SSH public key management via ldapPublicKey objectClass
  author: Heracles Team
  status: Stable
  license: MIT
  tags:
    - user
    - security

# LDAP schema files (.schema and .ldif)
ldap_schemas:
  - openssh-lpk.schema
  - openssh-lpk.ldif

# UI form schema files (JSON Schema)
ui_schemas:
  - schema_ssh.json

# Plugin dependencies
dependencies: []
optional_dependencies:
  - posix

# Object classes managed by this plugin
object_classes:
  - ldapPublicKey

# Object types this plugin extends or provides
object_types:
  - user

# OID information
oid:
  base: "1.3.6.1.4.1.24552.500.1.1"
  registered: true
  owner: "Eric AUGE"
```

## Schema Types

| Schema Type | Location | Purpose |
|-------------|----------|---------|
| LDAP Schema | `ldap/*.schema` | OpenLDAP object/attribute definitions |
| LDAP LDIF | `ldap/*.ldif` | cn=config format for modern OpenLDAP |
| Pydantic | `schemas.py` | API request/response validation |
| JSON Schema | `schema_*.json` | UI form generation and validation |

## Benefits of This Structure

1. **Self-contained plugins** - All artifacts co-located
2. **Auto-discovery** - Schema loader finds schemas automatically
3. **Metadata tracking** - Version, dependencies, OIDs documented
4. **Easier maintenance** - Changes to a plugin stay in one place
