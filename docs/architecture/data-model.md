# Data Model

Heracles uses LDAP as the authoritative identity store and PostgreSQL for application state.

!!! warning "Compatibility Rule"
    Every LDAP entry created or modified by Heracles **must** be readable and editable by standard LDAP tools (ldapsearch, ldapmodify, phpLDAPadmin), and vice versa.

---

## LDAP Tree Structure

```
dc=example,dc=com                     # Base DN
├── ou=aclroles                       # ACL role definitions
├── ou=configs                        # Application configuration
├── ou=departments                    # Organizational hierarchy
├── ou=dhcp                           # DHCP configuration
├── ou=dns                            # DNS zones
├── ou=groups                         # Groups (LDAP, POSIX, Mixed)
├── ou=people                         # User accounts
├── ou=sudoers                        # Sudo rules
├── ou=systems                        # Infrastructure inventory
│   ├── ou=servers
│   ├── ou=workstations
│   ├── ou=terminals
│   ├── ou=printers
│   ├── ou=components
│   ├── ou=phones
│   └── ou=mobiles
└── ou=tokens                         # Recovery tokens
```

---

## Required LDAP Schemas

| Schema | Source | Purpose |
|---|---|---|
| `core.schema` | OpenLDAP | Base schema |
| `cosine.schema` | OpenLDAP | X.500 directory classes |
| `inetorgperson.schema` | OpenLDAP | User objects |
| `nis.schema` | OpenLDAP | POSIX accounts and groups |
| `sudo.schema` | sudoers | Sudo rule definitions |
| `openssh-lpk.schema` | OpenSSH | SSH public keys in LDAP |

Custom schemas are **forbidden** except for documented auxiliaries like `posixGroupAux` (used for mixed groups).

---

## User Object

### Object Classes

| ObjectClass | Type | Usage |
|---|---|---|
| `inetOrgPerson` | STRUCTURAL | Base user entry |
| `posixAccount` | AUXILIARY | Unix account (via POSIX plugin) |
| `shadowAccount` | AUXILIARY | Password expiration |
| `ldapPublicKey` | AUXILIARY | SSH keys (via SSH plugin) |

### Core Attributes

| Attribute | Type | Required | Example |
|---|---|---|---|
| `uid` | string | :white_check_mark: | `jdoe` |
| `cn` | string | :white_check_mark: | `John Doe` |
| `sn` | string | :white_check_mark: | `Doe` |
| `givenName` | string | | `John` |
| `mail` | string | | `jdoe@example.com` |
| `userPassword` | binary | | `{ARGON2}$argon2id$...` |
| `telephoneNumber` | string | | `+33 1 23 45 67 89` |

### POSIX Attributes (when plugin enabled)

| Attribute | Type | Required | Example |
|---|---|---|---|
| `uidNumber` | integer | :white_check_mark: | `10001` |
| `gidNumber` | integer | :white_check_mark: | `10001` |
| `homeDirectory` | string | :white_check_mark: | `/home/jdoe` |
| `loginShell` | string | | `/bin/bash` |
| `gecos` | string | | `John Doe` |

---

## Group Object

### Group Types

Heracles supports three group types:

| Type | ObjectClass | Members stored as |
|---|---|---|
| **LDAP Group** | `groupOfNames` | Full DNs (`member`) |
| **POSIX Group** | `posixGroup` | UIDs (`memberUid`) |
| **Mixed Group** | `groupOfNames` + `posixGroupAux` | Both DNs and UIDs |

---

## Sudo Rule Object

| Attribute | Description | Example |
|---|---|---|
| `cn` | Rule name | `web-admins-sudo` |
| `sudoUser` | Users / groups | `jdoe`, `%webadmins` |
| `sudoHost` | Target hosts | `ALL`, `web*.example.com` |
| `sudoCommand` | Allowed commands | `/usr/bin/systemctl restart nginx` |
| `sudoOption` | Sudo options | `!authenticate` |

---

## PostgreSQL Tables

PostgreSQL stores application state — not identity data.

| Table | Purpose |
|---|---|
| `audit_logs` | Action history (who, what, when) |
| `settings` | Global application configuration |
| `templates` | User creation templates |
| `sessions` | Active user sessions |
| `alembic_version` | Database migration tracking |
