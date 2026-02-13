# Security

Heracles implements defense-in-depth security across all layers of the stack.

---

## Security Layers

```mermaid
graph TB
    subgraph "Layer 1 — Network"
        TLS["TLS encryption"]
        FW["Firewall / Rate limiting"]
    end
    subgraph "Layer 2 — Application"
        Auth["JWT Authentication"]
        ACL["Role-based ACL"]
        Val["Input Validation (Pydantic)"]
    end
    subgraph "Layer 3 — Data"
        Hash["Password Hashing (Argon2)"]
        Audit["Audit Logging"]
    end
    subgraph "Layer 4 — LDAP"
        Bind["LDAP Bind Auth"]
        LTLS["LDAP TLS (StartTLS / LDAPS)"]
    end

    TLS --> Auth
    Auth --> Hash
    Hash --> Bind
```

---

## Core Principles

| Principle | Implementation |
|---|---|
| **Defense in Depth** | Four security layers — network, application, data, LDAP |
| **Least Privilege** | Users only get the permissions they need |
| **Zero Trust** | Every request is authenticated and authorized |
| **No Secrets in Code** | All credentials via environment variables |
| **Input Validation** | Pydantic models on every API request |
| **LDAP Injection Prevention** | All user input escaped with `escape_filter_chars()` |

---

## Quick Links

- [Authentication & Tokens](auth-tokens.md) — JWT lifecycle, token storage, session management
- [LDAP Security](ldap.md) — TLS configuration, bind security, input escaping
- [Access Control](../guide/acl.md) — Role-based permissions
