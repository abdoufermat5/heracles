# Groups

Organize users and manage access through groups.

---

## Group Types

Heracles supports three group types to cover different use cases:

| Type | ObjectClass | Use Case |
|---|---|---|
| **LDAP Group** | `groupOfNames` | Application-level access control |
| **POSIX Group** | `posixGroup` | Unix/Linux file permissions and login |
| **Mixed Group** | `groupOfNames` + `posixGroupAux` | Both LDAP and POSIX membership |

!!! tip "When to use Mixed Groups"
    Mixed groups are ideal when you need a single group for both LDAP application access and Unix permissions — no need to maintain two separate groups.

---

## Group List

View all groups in the directory with their type, member count, and description.

![Group List](../assets/groups/list.png)

---

## Creating a Group

Click **Create Group** and fill in the required fields:

![Create Group](../assets/groups/create_modal.png)

| Field | Description |
|---|---|
| Name (`cn`) | Group name (must be unique) |
| Description | Purpose of the group |
| Type | LDAP, POSIX, or Mixed |
| GID Number | *(POSIX/Mixed only)* Numeric group ID |
| Department | Parent OU for the group |

---

## Group Details

Click a group to view its members and attributes.

![Group Details](../assets/groups/details.png)

### Managing Members

- **Add members** — Search and select users to add
- **Remove members** — Click the remove icon next to any member
- **Bulk operations** — Select multiple members for batch actions

### POSIX Attributes

For POSIX and Mixed groups, the GID number and member UIDs are managed automatically alongside the DN-based membership.

---

## Deleting a Group

Deleting a group removes the LDAP entry. Users are not deleted — only the membership association is removed.
