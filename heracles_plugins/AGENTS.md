# heracles_plugins

> Plugin package for Heracles (7 plugins)

## Version: 0.8.0-beta (plugins individually at 1.0.0)

## Plugins

| Plugin | Purpose | ObjectClasses |
|--------|---------|---------------|
| posix | Unix accounts, groups | posixAccount, posixGroup, posixGroupAux |
| sudo | Sudoers rules | sudoRole |
| ssh | SSH public keys | ldapPublicKey |
| systems | Servers, workstations | device + custom |
| dns | DNS zones/records | dNSZone, dNSRRset |
| dhcp | DHCP config | dhcpServer, dhcpSubnet, etc. |
| mail | Mail attributes | mailLocalAddress, etc. |

## Plugin Structure

```
heracles_plugins/<name>/
├── __init__.py    # Exports: router, service, schemas
├── plugin.py      # PluginInfo + TabDefinition
├── routes.py      # FastAPI APIRouter
├── schemas.py     # Pydantic models
├── service/       # Business logic
│   └── __init__.py
└── tests/
```

## Commands (⚠️ Run in container)

```bash
# All plugin tests
docker compose exec api sh -c "PYTHONPATH=/app:/heracles_plugins pytest /heracles_plugins -v"

# Single plugin
docker compose exec api sh -c "PYTHONPATH=/app:/heracles_plugins pytest /heracles_plugins/heracles_plugins/posix/tests -v"
```

## PluginInfo Example

```python
@staticmethod
def info() -> PluginInfo:
    return PluginInfo(
        name="posix",
        version="1.0.0",
        description="POSIX account management",
        author="Heracles Team",
        dependencies=[],
        minimum_api_version="0.8.0",
    )
```

## Rules

- Each plugin declares `minimum_api_version`
- Use standard LDAP schemas when possible
- Custom schemas go in `deploy/docker/ldap/schemas/`
- Pydantic schemas use `Field(alias="camelCase")`
- Service classes handle all business logic
