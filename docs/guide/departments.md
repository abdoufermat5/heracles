# Departments

Departments are LDAP Organizational Units (OUs) that structure your directory hierarchy.

---

## Department List

View the organizational hierarchy at a glance.

![Departments List](../assets/departments/list.png)

---

## Creating a Department

Click **Create Department** to add a new OU.

![Create Department](../assets/departments/create_modal.png)

| Field | Description |
|---|---|
| Name (`ou`) | Department name |
| Description | Purpose or scope |
| Parent | Parent OU (for nested hierarchy) |

---

## Hierarchy

Departments can be nested to reflect your organization's structure:

```
dc=example,dc=com
├── ou=Engineering
│   ├── ou=Backend
│   └── ou=Frontend
├── ou=Operations
│   ├── ou=Infrastructure
│   └── ou=Security
└── ou=Human Resources
```

Users and groups can be placed within any department to reflect organizational ownership.

---

## Deleting a Department

!!! warning
    A department can only be deleted if it contains no child entries (users, groups, or sub-departments). Move or delete all contents first.
