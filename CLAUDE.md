# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Heracles** is a modern rewrite of FusionDirectory, an LDAP identity management system. It provides a more performant, maintainable, and extensible solution while maintaining **100% compatibility** with existing FusionDirectory LDAP deployments.

## Architecture

```
heracles/
├── heracles-core/          # Rust library (LDAP operations, password hashing, schema validation)
├── heracles-api/           # Python/FastAPI backend (REST API, auth, business logic)
├── heracles-ui/            # React/TypeScript frontend
├── heracles-plugins/       # Python plugins (posix, sudo, ssh, systems, dns, dhcp)
├── docker/                 # Docker configurations
└── tests/                  # E2E tests
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

### Rust (heracles-core)
```bash
cd heracles-core
cargo build --release    # Build
cargo test               # Run tests
cargo fmt --all          # Format (required before commit)
cargo clippy -- -D warnings  # Lint (no warnings allowed)
cargo audit              # Security vulnerability check
```

### Python (heracles-api)
```bash
cd heracles-api
poetry install           # Install dependencies
poetry run uvicorn app.main:app --reload  # Start dev server
poetry run pytest        # Run tests
poetry run pytest tests/test_services/test_user_service.py::TestGetByUid  # Single test
poetry run black .       # Format (required)
poetry run isort .       # Sort imports (required)
poetry run ruff check --fix .  # Lint
pip-audit                # Security check
```

### React (heracles-ui)
```bash
cd heracles-ui
npm install              # Install dependencies
npm run dev              # Start dev server
npm test                 # Run tests
npm run lint             # Lint
npm run format           # Format with Prettier
npm audit                # Security check
```

### Docker (Infrastructure)
```bash
docker-compose up -d     # Start LDAP, PostgreSQL, Redis
```

## Critical Constraints

### LDAP Compatibility (CRITICAL)
- Use ONLY existing FusionDirectory LDAP schemas
- NEVER create new objectClass or attributeType
- All entries must be readable/writable by both Heracles and FusionDirectory
- Required schemas: core.schema, inetorgperson.schema, nis.schema, core-fd.schema, sudo.schema, openssh-lpk.schema

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
- `plugin.py` - Plugin definition with PluginInfo
- `service.py` - Business logic extending TabService
- `schemas.py` - Pydantic models
- `schema.json` - UI form schema

Essential plugins for v1.0: core, posix, sudo, ssh, systems, dns, dhcp

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
