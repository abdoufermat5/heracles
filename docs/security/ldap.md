# LDAP Security

Securing the connection between Heracles and the LDAP directory.

---

## TLS Configuration

Heracles supports encrypted LDAP connections via LDAPS or StartTLS.

### LDAPS (Recommended for Production)

```bash
LDAP_URI=ldaps://ldap.example.com:636
LDAP_TLS_CACERT=/etc/ssl/certs/ca.crt
```

### StartTLS

```bash
LDAP_URI=ldap://ldap.example.com:389
LDAP_STARTTLS=true
LDAP_TLS_CACERT=/etc/ssl/certs/ca.crt
```

!!! warning
    Never use unencrypted LDAP (`ldap://`) in production. Credentials and directory data would be transmitted in plaintext.

---

## Bind Security

Heracles connects to LDAP using a dedicated service account with the minimum required permissions.

| Setting | Description | Example |
|---|---|---|
| `LDAP_BIND_DN` | Service account DN | `cn=heracles,ou=services,dc=example,dc=com` |
| `LDAP_BIND_PASSWORD` | Service account password | *(from .env)* |

The service account should have:

- **Read access** to all identity OUs (`ou=people`, `ou=groups`, etc.)
- **Write access** limited to managed OUs
- **No access** to other directory branches

---

## LDAP Injection Prevention

All user-supplied input is escaped before being used in LDAP filters or DN construction.

```python
from ldap3.utils.conv import escape_filter_chars

# ✅ Always escape user input
safe_uid = escape_filter_chars(user_input)
filter_str = f"(uid={safe_uid})"

# ❌ Never interpolate directly
filter_str = f"(uid={user_input})"  # Vulnerable!
```

This is enforced at the service layer — individual plugins and routes should never construct raw LDAP queries.

---

## Schema Security

Heracles only uses standard LDAP schemas. Custom schema creation is **forbidden** (except documented auxiliaries like `posixGroupAux`).

This ensures:

- No vendor lock-in to Heracles-specific schemas
- Full interoperability with other LDAP tools
- Migration path to other LDAP management solutions

Schemas are stored in `deploy/docker/ldap/schemas/`.
