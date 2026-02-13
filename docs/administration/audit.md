# Audit Logs

Heracles records every significant action in the audit log for compliance and troubleshooting.

---

## What Gets Logged

Every directory-modifying operation is recorded:

| Event Type | Examples |
|---|---|
| **User operations** | Create, update, delete, password change |
| **Group operations** | Create, delete, add/remove members |
| **System operations** | Create, update, delete |
| **DNS operations** | Zone/record creation, modification, deletion |
| **DHCP operations** | Service and subnet changes |
| **Sudo operations** | Rule creation, modification, deletion |
| **Auth events** | Login, logout, failed login attempts |
| **ACL changes** | Policy creation, role assignment |

---

## Audit Log Fields

Each log entry contains:

| Field | Description | Example |
|---|---|---|
| Timestamp | When the action occurred | `2026-02-13T10:30:00Z` |
| Actor | Who performed the action | `uid=admin` |
| Action | What was done | `user.create` |
| Target | What was affected | `uid=jdoe,ou=people,...` |
| Changes | What changed | `{mail: null → jdoe@ex.com}` |
| IP Address | Client IP | `192.168.1.100` |
| Result | Success or failure | `success` |

---

## Viewing Audit Logs

### Web UI

Navigate to **Administration > Audit Logs** to browse the log with filtering.

![Audit Logs](../assets/administration/audit_log.png)

### API

```http
GET /api/v1/audit?limit=100&filter=actor:eq:admin&filter=action:starts:user
```

---

## Storage

Audit logs are stored in **PostgreSQL** (not LDAP) for efficient querying and long-term retention. They are independent of directory data and survive LDAP restores.
