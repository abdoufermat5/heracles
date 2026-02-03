# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Heracles** is a modern LDAP identity management system. It provides a performant, maintainable, and extensible solution while maintaining **100% compatibility** with existing LDAP deployments and standard schemas.

**Current Status (February 2026):** Phase 3 complete - All infrastructure plugins implemented. POSIX, Sudo, SSH, Systems, DNS, DHCP, and Mail plugins all operational. Department management with hierarchical filtering complete. Database-backed configuration system in place.

## Architecture

```
heracles/
├── heracles-core/          # Rust library (LDAP operations, password hashing, schema validation)
├── heracles-api/           # Python/FastAPI backend (REST API, auth, business logic)
│   ├── heracles_api/       # Main package (core/, api/, services/, models/, plugins/, middleware/)
│   └── alembic/            # Database migrations
├── heracles-ui/            # React 19 / TypeScript frontend (Vite + Bun)
├── heracles_plugins/       # Python plugins (7 plugins: posix, sudo, ssh, systems, dns, dhcp, mail)
├── docker/                 # Docker configurations (LDAP schemas, Dockerfiles, init scripts)
├── guidelines/             # Specification documents (architecture, API, security, etc.)
├── scripts/                # Deployment and bootstrap scripts
├── mk/                     # Makefile modules (docker.mk, demo.mk, help.mk)
└── demo/                   # Vagrant demo environment
```

**Component Communication:**
- Frontend -> API Gateway only (HTTP/REST, WebSocket)
- API Gateway -> Services -> LDAP (via heracles-core Rust bindings)
- Services -> PostgreSQL (config, audit, plugin settings) via SQLAlchemy + Alembic
- Services -> Redis (cache, sessions)

## Tech Stack (Mandatory)

| Component | Technology | Version |
|-----------|------------|---------|
| Core Library | Rust | Edition 2021 |
| API Backend | Python + FastAPI | 3.11+ / 0.109+ |
| Frontend | React + TypeScript | 19+ / 5.9+ |
| Build Tool (UI) | Vite + Bun | 7+ / 1+ |
| CSS Framework | TailwindCSS | v4 |
| Database | PostgreSQL | 15+ |
| Cache | Redis | 7+ |
| Directory | OpenLDAP (osixia) | 1.5.0 |

## Build and Development Commands

**IMPORTANT: All tests MUST be run inside containers, never on the host machine.**

### Docker Infrastructure
```bash
make up-infra            # Start LDAP, PostgreSQL, Redis (required before tests)
make up                  # Start all services (API, UI, infrastructure)
make down                # Stop all services
make build               # Build/rebuild Docker images
make rebuild             # Rebuild without cache
make clean               # Remove containers and volumes
make bootstrap           # Initialize LDAP structure
make schemas             # Load LDAP schemas
make logs                # View logs (use: make logs s=api for specific service)
```

### Rust (heracles-core)
```bash
cd heracles-core
cargo build --release    # Build
cargo test               # Run tests (Rust tests can run on host - no external deps)
cargo fmt --all          # Format (required before commit)
cargo clippy -- -D warnings  # Lint (no warnings allowed)
cargo audit              # Security vulnerability check
```

### Python (heracles-api) - Run in Container
```bash
# All tests MUST run inside the api container
docker compose exec api sh -c "PYTHONPATH=/app pytest -v"                    # Run all tests
docker compose exec api sh -c "PYTHONPATH=/app pytest tests/test_auth.py"    # Single file
docker compose exec api sh -c "PYTHONPATH=/app pytest -k 'test_name'"        # Single test by name

# Linting/formatting (run in container)
docker compose exec api sh -c "cd /app && black ."
docker compose exec api sh -c "cd /app && isort ."
docker compose exec api sh -c "cd /app && ruff check --fix ."
```

### Python Plugins (heracles_plugins) - Run in Container
```bash
# Plugin tests MUST run inside the api container (plugins are mounted)
docker compose exec api sh -c "PYTHONPATH=/app:/heracles_plugins pytest /heracles_plugins -v"
docker compose exec api sh -c "PYTHONPATH=/app:/heracles_plugins pytest /heracles_plugins/heracles_plugins/posix/tests/ -v"
```

### React (heracles-ui) - Run in Container
```bash
# All tests MUST run inside the ui container
docker compose --profile full exec ui npm test               # Run tests
docker compose --profile full exec ui npm run lint           # Lint
docker compose --profile full exec ui npm run format         # Format
```

### Quick Shell Access
```bash
make shell s=api         # Shell into API container
make shell s=ui          # Shell into UI container
make shell-db            # PostgreSQL shell
make shell-redis         # Redis CLI
make shell-ldap          # LDAP search shell
```

## Critical Constraints

### Container-Based Testing (CRITICAL)
- NEVER run Python or JavaScript tests on the host machine
- ALWAYS use `docker compose exec` to run tests inside containers
- Infrastructure must be running before tests: `make up-infra` or `make up`
- Tests depend on LDAP, PostgreSQL, and Redis being available in containers
- Rust tests (heracles-core) can run on host as they have no external dependencies

### LDAP Compatibility (CRITICAL)
- Use ONLY standard LDAP schemas **EXCEPT** for documented custom schemas
- All entries must be readable/writable by existing LDAP tools and clients
- Required standard schemas: core, inetorgperson, nis, sudo, openssh-lpk
- Custom schemas location: `docker/ldap/schemas/` (loaded via `make schemas`)
- Built-in schemas (osixia/openldap): openssh-lpk, samba, postfix-book, kopano

**Documented Custom Schemas:**

| Schema | File | Purpose |
|--------|------|---------|
| `posixGroupAux` | `hrc-aux.schema` | AUXILIARY class for Mixed Groups (LDAP+POSIX) |
| `hrcServer/hrcWorkstation/...` | `hrc-systems.schema` | System object classes (7 types) |
| `hrcDepartment` | `hrc-department.schema` | Hierarchical department management |
| `hrcConf` | `hrc-conf.schema` | Heracles configuration storage |
| `dNSZone/dNSRRset` | `dnszone.schema` | DNS zone and record management |
| `dhcpServer/dhcpSubnet/...` | `hrc-dhcp.schema` | DHCP configuration (11 types) |
| `ldapNSContainer` | `ldapns.schema` | LDAP Name Service container |

Each plugin owns its LDAP schemas in its `ldap/` directory; core schemas live in `docker/ldap/schemas/core/`.

### Security Rules
- NEVER hardcode secrets in code (use environment variables)
- ALWAYS escape user input for LDAP queries using `escape_filter_chars()`
- ALWAYS validate with Pydantic on API layer
- NEVER log passwords, tokens, or sensitive data
- Minimum 80% test coverage

## Coding Standards

### Rust
- No `unwrap()` in production - use `?` or explicit error handling
- Document all public types with `///`
- Use `thiserror` for custom errors

### Python
- Type hints on ALL functions
- Google-style docstrings on public functions
- Async by default for I/O
- No business logic in route handlers - delegate to services
- Use Pydantic for all input validation

### TypeScript/React
- `strict: true` in tsconfig
- Functional components only
- React Query for server state, Zustand for UI state
- Zod for validation
- No `any` types

## Commit Convention

```
<type>(<scope>): <description>

Types: feat, fix, docs, style, refactor, test, chore
Example: feat(api): add user creation endpoint
```

## Forbidden Dependencies

- Django, Flask (use FastAPI)
- Redux (use Zustand)
- Axios (use native fetch or @tanstack/query)
- MongoDB, MySQL (use PostgreSQL)

## Plugin System

Plugins provide tabs (attach to existing object types) or management capabilities (new object types). Each plugin follows this structure:

```
heracles_plugins/heracles_plugins/<plugin_name>/
├── __init__.py           # Auto-registration + exports
├── plugin.py             # PluginInfo + TabDefinition metadata
├── routes.py             # FastAPI APIRouter endpoints
├── schemas.py            # Pydantic models (Create, Read, Update, ListItem, ListResponse)
├── plugin.yaml           # Plugin configuration
├── service/              # Business logic (service package)
│   └── __init__.py       # Service classes
├── ldap/                 # LDAP schema files (.schema, .ldif)
├── tests/                # Test suite
└── schema_*.json         # JSON schemas for UI (optional)
```

**All Implemented Plugins:**
- **posix** - Unix accounts, POSIX groups, Mixed groups, System Trust (posixAccount, shadowAccount, posixGroup, posixGroupAux)
- **sudo** - Sudoers rules management (sudoRole)
- **ssh** - SSH public key management (ldapPublicKey)
- **systems** - System management: server, workstation, terminal, printer, component, phone, mobile (hrcServer, hrcWorkstation, etc.)
- **dns** - DNS zone and record management, 8 record types: A, AAAA, MX, NS, CNAME, PTR, TXT, SRV (dNSZone, dNSRRset)
- **dhcp** - DHCP configuration, 11 object types: service, shared_network, subnet, pool, host, group, class, subclass, tsig_key, dns_zone, failover_peer (dhcpServer, dhcpSubnet, etc.)
- **mail** - Mail attributes management on users and groups

## Configuration System

Heracles has a database-backed configuration system managed via Alembic migrations:

**PostgreSQL Tables:**
- `config_categories` - Configuration categories (general, ldap, security, password, session, audit)
- `config_settings` - Key-value settings with validation rules, data types, and dependencies
- `plugin_configs` - Per-plugin configuration with schema validation
- `config_history` - Audit trail for all configuration changes

**API Endpoints:** `GET/PUT/DELETE /api/v1/config/{key}`, `GET /api/v1/plugins`

## POSIX Plugin Reference

**Three Group Types:**
| Type | ObjectClasses | Members |
|------|---------------|---------|
| LDAP | groupOfNames | member (DNs) |
| POSIX | posixGroup | memberUid |
| Mixed | groupOfNames + posixGroupAux | both |

**Custom Schema:** `posixGroupAux` is AUXILIARY (OID 1.3.6.1.4.1.99999.1.2.1)

**API Endpoints:**
- GET/POST/DELETE `/posix/users/{dn}/posix` - Account management
- GET/POST `/posix/groups/posix` - POSIX groups
- GET/POST `/posix/groups/mixed` - Mixed groups

## API Structure

Base URL: `/api/v1/`
- Authentication: JWT Bearer tokens (configurable, default 60 min access, 7 day refresh)
- Responses: JSON with standard error format `{ "error": { "code": "...", "message": "..." } }`
- Pagination: `?limit=50&offset=0`
- Filtering: `?filter=cn:contains:john`

**Core Endpoints:**
- `/auth` - Login, refresh, logout, me
- `/users` - User CRUD, password change, lock/unlock
- `/groups` - Group CRUD, member management
- `/departments` - Department CRUD, hierarchical tree
- `/config` - Configuration management
- `/plugins` - Plugin information and status

**Plugin Endpoints:**
- `/posix` - POSIX accounts and groups
- `/sudo` - Sudo rules
- `/ssh` - SSH public keys
- `/systems` - System/device management
- `/dns` - DNS zones and records
- `/dhcp` - DHCP services, subnets, hosts, pools
- `/mail` - Mail attributes

## Middleware

- **RateLimitMiddleware** - Redis-backed rate limiting
- **PluginAccessMiddleware** - Controls access to disabled plugin endpoints
- **CORS** - Configurable cross-origin resource sharing

## Pre-Development Checklist

1. Read relevant specification documents in `/guidelines/`
2. Verify task is within roadmap scope
3. Check for existing reusable code
4. Plan tests to write
5. Confirm LDAP schema compatibility
