# Heracles Plugins

Official plugins for Heracles Identity Management.

## Included Plugins

### POSIX Plugin
Provides POSIX account management (Unix accounts) for users and groups.

**LDAP ObjectClasses:**
- `posixAccount` - Unix user account attributes
- `shadowAccount` - Password aging/expiration
- `posixGroup` - Unix group

**Features:**
- Automatic UID/GID allocation
- Home directory generation
- Login shell management
- Shadow password expiration settings

## Installation

```bash
uv pip install -e /path/to/heracles_plugins
```

## Configuration

Enable plugins in your Heracles configuration:

```python
PLUGINS_ENABLED = ["posix"]

# POSIX Plugin Settings
POSIX_UID_MIN = 10000
POSIX_UID_MAX = 60000
POSIX_GID_MIN = 10000
POSIX_GID_MAX = 60000
POSIX_DEFAULT_SHELL = "/bin/bash"
POSIX_DEFAULT_HOME_BASE = "/home"
```
