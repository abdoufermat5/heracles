# Components

Detailed breakdown of each Heracles component.

---

## heracles-core (Rust)

The core library handles performance-critical and security-sensitive operations. It is compiled as a native Python module via PyO3.

### Responsibilities

| Area | What it does |
|---|---|
| LDAP connections | Connection pooling, automatic reconnection |
| LDAP operations | Search, add, modify, delete, bind |
| Password hashing | Argon2, bcrypt, SHA, SSHA, MD5, SMD5 |
| Schema validation | Parse and validate LDAP schemas |
| UID/GID allocation | Atomic generation of unique identifiers |

### Module Structure

```
heracles-core/src/
├── lib.rs               # PyO3 entry point
├── ldap/
│   ├── connection.rs    # Connection pool
│   ├── operations.rs    # CRUD operations
│   ├── search.rs        # Search with filters
│   ├── schema.rs        # Schema parsing
│   └── dn.rs            # DN manipulation
├── crypto/
│   ├── password.rs      # Hash / verify
│   ├── hash_methods.rs  # Algorithm implementations
│   └── random.rs        # Secure random generation
├── schema/
│   ├── parser.rs        # LDAP schema parser
│   ├── validator.rs     # Entry validation
│   └── types.rs         # LDAP data types
└── errors.rs            # Error types (thiserror)
```

### PyO3 Interface

Functions exposed to Python:

```rust
// LDAP
LdapConnection, ldap_search, ldap_add, ldap_modify, ldap_delete, ldap_bind

// Crypto
hash_password, verify_password, generate_random_password

// Schema
parse_schema, validate_entry
```

---

## heracles-api (Python / FastAPI)

The API backend handles HTTP routing, authentication, authorization, and business logic.

### Structure

```
heracles-api/heracles_api/
├── core/           # Settings, security, dependencies
├── api/            # Route definitions (v1)
├── services/       # Business logic layer
├── models/         # SQLAlchemy models (PostgreSQL)
├── schemas/        # Pydantic request/response models
├── middleware/      # CORS, logging, error handling
├── plugins/        # Plugin loader and registry
└── acl/            # Access control system
```

### Key Design Choices

- **Pydantic validation** on every request
- **Async I/O** throughout (async def endpoints)
- **Service layer** separates HTTP concerns from business logic
- **Plugin registry** dynamically loads and mounts plugin routes

---

## heracles-ui (React / TypeScript)

The frontend is a single-page application built with React 18, TypeScript, Vite, and TailwindCSS.

### Structure

```
heracles-ui/src/
├── components/      # Reusable UI components (shadcn/ui)
├── pages/           # Route-level page components
├── hooks/           # Custom React hooks
├── lib/             # API client, utilities
├── stores/          # Zustand state management
└── types/           # TypeScript type definitions
```

### Key Libraries

| Library | Purpose |
|---|---|
| `@tanstack/react-query` | Server state & data fetching |
| `zustand` | Client state management |
| `react-hook-form` + `zod` | Form handling & validation |
| `shadcn/ui` + `@radix-ui` | Accessible component primitives |
| `TailwindCSS` | Utility-first styling |

---

## heracles_plugins

Plugins extend Heracles with domain-specific functionality. Each plugin follows a standard structure:

```
heracles_plugins/<name>/
├── plugin.py       # PluginInfo metadata + tab definitions
├── routes.py       # FastAPI router (API endpoints)
├── schemas.py      # Pydantic models
├── service/        # Business logic
└── tests/          # Plugin-specific tests
```

7 plugins ship with Heracles:

| Plugin | Type | Description |
|---|---|---|
| `posix` | Hybrid | Unix accounts (UID, GID, shell, home) |
| `sudo` | Management | Sudo rules for privilege escalation |
| `ssh` | Tab | SSH public key management |
| `systems` | Management | Server/workstation inventory |
| `dns` | Management | DNS zone and record management |
| `dhcp` | Management | DHCP service configuration |
| `mail` | Tab | Email attribute management |

[:octicons-arrow-right-24: Plugin details](../plugins/index.md)
