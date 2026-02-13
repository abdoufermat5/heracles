# Contributing

Guidelines for contributing to the Heracles project.

---

## Development Stack

| Tool | Version | Purpose |
|---|---|---|
| Rust | 1.75+ | heracles-core development |
| Python | 3.11+ | API and plugin development |
| Node.js | 20+ | UI development |
| Docker | 24.0+ | Infrastructure and testing |

---

## Setup

```bash
git clone https://github.com/abdoufermat5/heracles.git
cd heracles
make up-infra   # Start LDAP, PostgreSQL, Redis
```

---

## Coding Standards

### Rust

- No `unwrap()` in production code — use `?` or explicit error handling
- Use `///` doc comments on all public items
- Errors via `thiserror` crate
- Run `cargo fmt` and `cargo clippy` before committing

### Python

- Type hints on all function signatures
- Google-style docstrings
- Async I/O throughout (`async def`)
- Pydantic models for all request/response validation
- Input escaping with `escape_filter_chars()` for LDAP operations

### TypeScript

- `strict: true` in tsconfig
- Functional components only (no class components)
- React Query for server state, Zustand for client state
- No `any` type — use proper typing

---

## Commit Convention

Format: `<type>(<scope>): <description>`

| Type | Usage |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `refactor` | Code restructuring |
| `test` | Adding or updating tests |
| `chore` | Build, CI, tooling |

Examples:

```
feat(api): add user import endpoint
fix(core): handle LDAP connection timeout
docs(plugins): update SSH plugin documentation
test(api): add ACL permission tests
```

---

## Testing

!!! warning "Critical Rule"
    **Never** run Python or JavaScript tests on the host machine. Always use Docker containers.

### Python (API + Plugins)

```bash
# API tests
docker compose exec api sh -c "PYTHONPATH=/app pytest -v"

# Plugin tests
docker compose exec api sh -c "PYTHONPATH=/app:/heracles_plugins pytest /heracles_plugins -v"
```

### Rust

Rust tests can run on the host:

```bash
cd heracles-core && cargo test
```

### Coverage

Minimum **80% test coverage** is required for all components.

---

## Forbidden Dependencies

These are explicitly prohibited — do not add them:

| Forbidden | Use Instead |
|---|---|
| Django, Flask | FastAPI |
| Redux | Zustand |
| Axios | `fetch` / `@tanstack/react-query` |
| MongoDB, MySQL | PostgreSQL |

---

## Before Submitting

1. Read relevant specs in `guidelines/`
2. Ensure tests pass in containers
3. Run linters (`cargo clippy`, `ruff`, `eslint`)
4. Follow commit conventions
5. Verify LDAP schema compatibility
