# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Heracles** is a modern LDAP identity management system. It provides a performant, maintainable, and extensible solution while maintaining **100% compatibility** with existing LDAP deployments and standard schemas.

**Current Status (January 2026):** Sprint 17 complete - DNS plugin fully implemented. POSIX, Sudo, SSH, Systems, and DNS plugins all operational.

## Architecture

```
heracles/
├── heracles-core/          # Rust library (LDAP operations, password hashing, schema validation)
├── heracles-api/           # Python/FastAPI backend (REST API, auth, business logic)
├── heracles-ui/            # React/TypeScript frontend
├── heracles_plugins/       # Python plugins (posix implemented, sudo/ssh planned)
├── docker/                 # Docker configurations (including custom LDAP schemas)
└── docs/                   # Specifications and documentation
```

**Component Communication:**
- Frontend → API Gateway only (HTTP/REST, WebSocket)
- API Gateway → Services → LDAP (via heracles-core Rust bindings)
- Services → PostgreSQL (config, audit, jobs) via SQLAlchemy
- Services → Redis (cache, sessions)

## Tech Stack (Mandatory)

| Component | Technology | Version |
|-----------|------------|---------|
| Core Library | Rust | 1.75+ |
| API Backend | Python + FastAPI | 3.11+ |
| Frontend | React + TypeScript | 18+ / 5+ |
| Database | PostgreSQL | 15+ |
| Cache | Redis | 7+ |
| Directory | OpenLDAP / 389DS | - |

## Build and Development Commands

**IMPORTANT: All tests MUST be run inside containers, never on the host machine.**

### Starting Infrastructure
```bash
make up-infra            # Start LDAP, PostgreSQL, Redis (required before tests)
make up                  # Start all services (API, UI, infrastructure)
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
- Custom schema allowed: `posixGroupAux` (AUXILIARY) for Mixed Groups
- All entries must be readable/writable by existing LDAP tools and clients
- Required schemas: core.schema, inetorgperson.schema, nis.schema, sudo.schema, openssh-lpk.schema
- Custom schemas location: `docker/ldap/schemas/` (loaded via `make ldap-schemas`)
- Built-in schemas (osixia/openldap): openssh-lpk, samba, postfix-book, kopano

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

Plugins provide tabs (attach to existing object types) or management capabilities (new object types). Each plugin has:
- `__init__.py` - Exports router, services, schemas
- `service.py` - Business logic (PosixService, PosixGroupService, MixedGroupService)
- `schemas.py` - Pydantic models with Field(alias="camelCase")
- `router.py` - FastAPI routes

**Implemented Plugins:**
- ✅ **posix** - Unix accounts, POSIX groups, Mixed groups, System Trust
- ✅ **sudo** - Sudoers rules management (sudoRole objectClass)
- ✅ **ssh** - SSH public key management (ldapPublicKey objectClass)
- ✅ **systems** - System management (servers, workstations, etc.)
- ✅ **dns** - DNS zone and record management (dNSZone objectClass)

**Planned Plugins:** dhcp

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
- Authentication: JWT Bearer tokens (30 min access, 7 day refresh)
- Responses: JSON with standard error format `{ "error": { "code": "...", "message": "..." } }`
- Pagination: `?limit=50&offset=0`
- Filtering: `?filter=cn:contains:john`

## Pre-Development Checklist

1. Read relevant specification documents in `/docs/`
2. Verify task is within roadmap scope
3. Check for existing reusable code
4. Plan tests to write
5. Confirm LDAP schema compatibility
