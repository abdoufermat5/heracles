# heracles-api

> FastAPI backend for Heracles identity management

## Version: 0.8.0-beta

## Structure

```
heracles_api/
├── main.py            # FastAPI app entry
├── config.py          # Settings (pydantic-settings)
├── api/v1/            # Route handlers
│   └── endpoints/     # auth, users, groups, departments, config, version
├── core/              # Database, logging, security
├── services/          # Business logic (UserService, GroupService, etc.)
├── repositories/      # LDAP/DB data access
├── schemas/           # Pydantic models
├── models/            # SQLAlchemy models
├── plugins/           # Plugin loader, registry, base classes
└── middleware/        # Rate limit, plugin access
```

## Commands (⚠️ Run in container)

```bash
# Tests
docker compose exec api sh -c "PYTHONPATH=/app pytest -v"
docker compose exec api sh -c "PYTHONPATH=/app pytest -k 'test_name'"

# Lint/Format
docker compose exec api sh -c "black . && isort . && ruff check --fix ."

# Shell
make shell s=api
```

## Key Patterns

```python
# Route handler → delegate to service
@router.post("/users")
async def create_user(data: UserCreate, service: UserService = Depends()):
    return await service.create(data)

# Pydantic schema with camelCase
class UserCreate(BaseModel):
    user_name: str = Field(alias="userName")
    class Config:
        populate_by_name = True
```

## Rules

- Type hints on ALL functions
- Google-style docstrings
- Async by default for I/O
- No business logic in routes → use services
- Validate with Pydantic
- Escape LDAP input: `escape_filter_chars()`
- Never log sensitive data
