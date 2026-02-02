# LDAP Schema Organization

This directory contains **core LDAP schemas** and **symlinks** to plugin schemas.

## Directory Structure

```
docker/ldap/schemas/
├── core/                          # Heracles core configuration schemas
│   ├── hrc-conf.schema            # Main configuration object (hrcConfig)
│   └── hrc-conf.ldif              # LDIF format for cn=config
│
├── hrc-department.{schema,ldif}   # Department schema (non-plugin)
├── hrc-mail.ldif                  # Mail schema (non-plugin)
├── ldapns.{schema,ldif}           # LDAP Name Service (non-plugin)
│
└── *.{schema,ldif} → symlinks     # Symlinks to plugin schemas
```

## Schema Organization

Heracles follows a **distributed schema pattern** where each plugin owns its schemas:

### 1. Core Configuration Schemas (`docker/ldap/schemas/core/`)
Centralized schemas for Heracles application configuration:
- `hrc-conf` - RDN paths, UID/GID ranges, default settings

### 2. Plugin Schemas (`heracles_plugins/heracles_plugins/*/ldap/`)
Each plugin owns its schemas, co-located with the plugin code:

| Plugin | Schema Files | OID Base |
|--------|--------------|----------|
| posix | `hrc-aux.{schema,ldif}` | 1.3.6.1.4.1.99999.1 |
| ssh | `openssh-lpk.{schema,ldif}` | 1.3.6.1.4.1.24552.500.1.1 |
| sudo | `sudo.{schema,ldif}` | 1.3.6.1.4.1.15953.9 |
| dns | `dnszone.{schema,ldif}` | 1.3.6.1.4.1.2428.20 |
| dhcp | `hrc-dhcp.{schema,ldif}` | 1.3.6.1.4.1.99999.3 |
| systems | `hrc-systems.{schema,ldif}` | 1.3.6.1.4.1.99999.2 |

## File Naming Convention

| Type | Convention | Example |
|------|------------|---------|
| Heracles custom | `hrc-<feature>.{schema,ldif}` | `hrc-systems.schema` |
| Third-party standard | `<original-name>.{schema,ldif}` | `sudo.schema` |

### 3. Plugin Metadata (`plugin.yaml`)
Each plugin has a `plugin.yaml` describing:
- LDAP schemas it provides
- UI form schemas (JSON Schema files)
- Dependencies and object classes
- OID information

## Loading Schemas

The bootstrap script auto-discovers schemas:

```bash
# Load all schemas (core + plugins + legacy)
make ldap-schemas

# Or directly:
./scripts/ldap-bootstrap.sh schemas
```

**Loading order:**
1. Core schemas (`docker/ldap/schemas/core/`)
2. Plugin schemas (`heracles_plugins/heracles_plugins/*/ldap/`)
3. Compatibility schemas (`docker/ldap/schemas/` - symlinks skipped)

## File Formats

Both formats are provided for flexibility:

| Format | Use Case |
|--------|----------|
| `.schema` | Traditional `slapd.conf` deployments |
| `.ldif` | Modern `cn=config` (OLC) deployments |

## OID Registration

> **⚠️ Development Only**: Heracles uses placeholder OID `1.3.6.1.4.1.99999` for custom schemas.
> For production, register a proper enterprise OID with IANA.

**Standard OIDs (registered by others):**
- `1.3.6.1.4.1.24552.500.1.1` - OpenSSH LPK
- `1.3.6.1.4.1.15953.9` - Sudo project
- `1.3.6.1.4.1.2428.20` - PowerDNS/DNS zone

## Symlinks for Backward Compatibility

Files in `docker/ldap/schemas/` that correspond to plugin schemas are **symlinks** pointing to the plugin source:

```
docker/ldap/schemas/
├── openssh-lpk.ldif    → ../../heracles_plugins/heracles_plugins/ssh/ldap/openssh-lpk.ldif
├── openssh-lpk.schema  → ../../heracles_plugins/heracles_plugins/ssh/ldap/openssh-lpk.schema
├── sudo.ldif           → ../../heracles_plugins/heracles_plugins/sudo/ldap/sudo.ldif
├── sudo.schema         → ../../heracles_plugins/heracles_plugins/sudo/ldap/sudo.schema
├── dnszone.ldif        → ../../heracles_plugins/heracles_plugins/dns/ldap/dnszone.ldif
├── dnszone.schema      → ../../heracles_plugins/heracles_plugins/dns/ldap/dnszone.schema
├── hrc-dhcp.ldif       → ../../heracles_plugins/heracles_plugins/dhcp/ldap/hrc-dhcp.ldif
├── hrc-dhcp.schema     → ../../heracles_plugins/heracles_plugins/dhcp/ldap/hrc-dhcp.schema
├── hrc-systems.ldif    → ../../heracles_plugins/heracles_plugins/systems/ldap/hrc-systems.ldif
├── hrc-systems.schema  → ../../heracles_plugins/heracles_plugins/systems/ldap/hrc-systems.schema
├── hrc-aux.ldif        → ../../heracles_plugins/heracles_plugins/posix/ldap/hrc-aux.ldif
└── hrc-aux.schema      → ../../heracles_plugins/heracles_plugins/posix/ldap/hrc-aux.schema
```

**Why symlinks?**
- Scripts/docs that reference `docker/ldap/schemas/` continue to work
- Single source of truth in plugin directories
- Bootstrap script auto-discovers from plugins and skips duplicate symlinks

**Real files (non-plugin):**
- `hrc-department.{schema,ldif}` - Organizational units
- `hrc-mail.ldif` - Mail attributes
- `ldapns.{schema,ldif}` - LDAP name service
- ✅ posix (heracles-aux) → `heracles_plugins/heracles_plugins/posix/ldap/`
