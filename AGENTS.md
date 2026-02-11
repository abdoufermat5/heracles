# AGENTS.md

> AI agent guidance for Heracles - Modern LDAP Identity Management System

## Status & Versions

| Component | Version | Tech |
|-----------|---------|------|
| heracles-core | 0.8.1-rc | Rust 1.75+ |
| heracles-api | 0.8.1-rc | Python 3.11+ / FastAPI |
| heracles-ui | 0.8.1-rc | React 18+ / TypeScript 5+ |
| heracles-plugins | 0.8.1-rc | 7 plugins @ v1.0.0 |

**Plugins:** posix, sudo, ssh, systems, dns, dhcp, mail (all operational)

## Architecture

```
heracles-core/     → Rust lib (LDAP ops, password hashing, PyO3 bindings)
heracles-api/      → FastAPI backend (REST API, auth, services)
heracles-ui/       → React frontend (Vite, TailwindCSS, shadcn/ui)
heracles_plugins/  → Plugin package (7 plugins)
docker/            → Docker configs + LDAP schemas
guidelines/        → Specifications (read before development)
```

**Data Flow:** UI → API → Services → LDAP (via heracles-core) / PostgreSQL / Redis

## Commands

```bash
# Infrastructure
make up-infra              # Start LDAP, PostgreSQL, Redis
make up                    # Start all services

# Testing (⚠️ ALWAYS IN CONTAINERS - except Rust)
docker compose exec api sh -c "PYTHONPATH=/app pytest -v"
docker compose exec api sh -c "PYTHONPATH=/app:/heracles_plugins pytest /heracles_plugins -v"
cd heracles-core && cargo test   # Rust can run on host

# Shells
make shell s=api           # API container shell
make shell s=ui            # UI container shell

# Versioning
make version               # Show versions
make bump-api-patch        # Bump patch (0.8.0 → 0.8.1)
make tag-release           # Create Git tags
```

## Critical Rules

### Testing
- **NEVER** run Python/JS tests on host - use `docker compose exec`
- Run `make up-infra` before tests
- Rust tests can run on host (no external deps)

### LDAP Compatibility
- Use **standard schemas only** except documented custom ones
- Custom allowed: `posixGroupAux` (AUXILIARY for Mixed Groups)
- All entries must work with standard LDAP tools
- Schemas: `docker/ldap/schemas/`

### Security
- No hardcoded secrets → use env vars
- Escape LDAP input → `escape_filter_chars()`
- Validate with Pydantic
- Never log sensitive data
- 80% test coverage minimum

## Coding Standards

| Lang | Rules |
|------|-------|
| **Rust** | No `unwrap()` in prod, `///` docs, `thiserror` errors |
| **Python** | Type hints, Google docstrings, async I/O, Pydantic validation |
| **TypeScript** | `strict: true`, functional components, React Query + Zustand, no `any` |

**Commits:** `<type>(<scope>): <desc>` — types: feat, fix, docs, refactor, test, chore

**Forbidden:** Django, Flask, Redux, Axios, MongoDB, MySQL

## Plugin Structure

```
heracles_plugins/<name>/
├── plugin.py      # PluginInfo + TabDefinition
├── routes.py      # FastAPI router
├── schemas.py     # Pydantic models (camelCase aliases)
├── service/       # Business logic
└── tests/
```

## API Reference

**Base:** `/api/v1/` | **Auth:** JWT (30min access, 7d refresh)

**Response format:** `{ "error": { "code": "...", "message": "..." } }`

**Pagination:** `?limit=50&offset=0` | **Filter:** `?filter=cn:contains:john`

## Before Development

1. Read specs in `/guidelines/`
2. Check roadmap scope
3. Look for reusable code
4. Plan tests
5. Verify LDAP schema compatibility
