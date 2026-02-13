# Plugin Development

How to create a new Heracles plugin.

---

## Plugin Structure

Every plugin follows this layout:

```
heracles_plugins/heracles_plugins/<plugin_name>/
├── __init__.py        # Exports and auto-registration
├── plugin.py          # PluginInfo + TabDefinitions
├── routes.py          # FastAPI router
├── schemas.py         # Pydantic models
├── service/           # Business logic
│   └── __init__.py
├── plugin.yaml        # Plugin configuration
├── ldap/              # LDAP schemas (if needed)
└── tests/             # Plugin tests
```

---

## Step 1: Define Plugin Metadata

Create `plugin.py` with a `get_info()` function:

```python
from heracles_api.plugins.base import PluginInfo, TabDefinition


def get_info() -> PluginInfo:
    return PluginInfo(
        name="my-plugin",
        version="1.0.0",
        description="Description of what this plugin does",
        author="Your Name",
        object_types=["user"],  # Objects this plugin attaches to
        object_classes=["myObjectClass"],  # LDAP objectClasses used
    )


def get_tabs() -> list[TabDefinition]:
    """Define tabs to add to existing object types."""
    return [
        TabDefinition(
            name="my-tab",
            label="My Tab",
            object_type="user",
            detection_attribute="myAttribute",
        )
    ]
```

---

## Step 2: Define API Routes

Create `routes.py` with a FastAPI router:

```python
from fastapi import APIRouter, Depends
from heracles_api.core.dependencies import get_current_user

router = APIRouter(prefix="/my-plugin", tags=["my-plugin"])


@router.get("/")
async def list_items(user=Depends(get_current_user)):
    """List plugin items."""
    ...


@router.post("/")
async def create_item(user=Depends(get_current_user)):
    """Create a plugin item."""
    ...
```

---

## Step 3: Define Schemas

Create `schemas.py` with Pydantic models:

```python
from pydantic import BaseModel, Field


class MyItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    description: str | None = None

    class Config:
        populate_by_name = True


class MyItemRead(BaseModel):
    dn: str
    name: str
    description: str | None = None
```

!!! note "camelCase Aliases"
    Use `alias` on fields for camelCase JSON output while keeping snake_case in Python.

---

## Step 4: Implement Service Logic

Create `service/__init__.py`:

```python
from heracles_api.core.ldap import get_ldap_connection


class MyPluginService:
    def __init__(self, ldap_conn):
        self.conn = ldap_conn

    async def list_items(self):
        """Fetch items from LDAP."""
        ...

    async def create_item(self, data):
        """Create an item in LDAP."""
        ...
```

---

## Step 5: Write Tests

Create tests under `tests/`:

```python
import pytest


class TestMyPlugin:
    def test_list_items(self, api_client):
        response = api_client.get("/api/v1/my-plugin/")
        assert response.status_code == 200

    def test_create_item(self, api_client):
        response = api_client.post("/api/v1/my-plugin/", json={
            "name": "test-item",
            "description": "Test"
        })
        assert response.status_code == 201
```

Run tests in the container:

```bash
docker compose exec api sh -c "PYTHONPATH=/app:/heracles_plugins pytest /heracles_plugins -v"
```

---

## Rules

1. **Standard LDAP schemas only** — no custom `objectClass` or `attributeType` definitions (except documented auxiliaries)
2. **Type hints everywhere** — all function signatures must have type annotations
3. **Google docstrings** — document all public functions
4. **Pydantic validation** — validate all input with Pydantic models
5. **Escape LDAP input** — always use `escape_filter_chars()` for user-supplied values
6. **80% test coverage** — minimum coverage requirement
