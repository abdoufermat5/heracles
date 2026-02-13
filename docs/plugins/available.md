# Available Plugins

Heracles ships with 7 plugins covering core identity and infrastructure management.

---

## POSIX

**Type:** Hybrid (Tab + Management)

Adds Unix/Linux account management to users and groups.

**User tab features:**

- UID/GID number management (auto-allocation available)
- Home directory and login shell configuration
- Shadow password attributes

**Group features:**

- POSIX groups (`posixGroup`)
- Mixed groups (`groupOfNames` + `posixGroupAux`) — combining LDAP and POSIX membership

**LDAP schemas:** `nis.schema` (standard)

---

## Sudo

**Type:** Management

Manages sudo rules stored in LDAP for centralized privilege escalation management.

**Features:**

- Define permitted commands per user/group
- Target specific hosts or host patterns
- Set sudo options (NOPASSWD, etc.)
- Standard `sudoRole` object class

**LDAP schemas:** `sudo.schema` (standard)

See [Sudo Roles](../guide/sudo.md) for usage details.

---

## SSH

**Type:** Tab

Manages SSH public keys stored in LDAP for passwordless server authentication.

**Features:**

- Add/remove SSH public keys per user
- Supports RSA, Ed25519, ECDSA key types
- Keys stored as `sshPublicKey` attribute

**LDAP schemas:** `openssh-lpk.schema` (standard)

Client-side: configure SSSD or `AuthorizedKeysCommand` to fetch keys from LDAP.

---

## Systems

**Type:** Management

Inventory management for servers, workstations, and network devices.

**Features:**

- Register machines with hostname, IP, MAC, type, and description
- Categorize by type (server, workstation, printer, terminal, etc.)
- Track location and ownership
- Integration with DNS and DHCP plugins

See [Systems](../guide/systems.md) for usage details.

---

## DNS

**Type:** Management

Manage DNS zones and records stored in LDAP.

**Features:**

- Forward and reverse zone management
- Record types: A, AAAA, CNAME, MX, NS, PTR, SRV, TXT
- Automatic reverse zone creation
- BIND9 integration via `sdb-ldap` or `dlz` backend

See [DNS Management](../guide/dns.md) for usage details.

---

## DHCP

**Type:** Management

Configure ISC DHCP servers through LDAP.

**Features:**

- DHCP service instances
- Subnet and pool configuration
- Fixed host reservations
- Global and per-subnet options

See [DHCP Management](../guide/dhcp.md) for usage details.

---

## Mail

**Type:** Tab

Manage email-related attributes on user entries.

**Features:**

- Primary email address
- Mail aliases
- Mail routing attributes
- Forward addresses

**LDAP schemas:** `cosine.schema`, `inetorgperson.schema` (standard)

---

## Plugin Compatibility Matrix

| Plugin | User Tab | Group Tab | Own Pages | LDAP Schema |
|---|---|---|---|---|
| POSIX | :white_check_mark: | :white_check_mark: | :white_check_mark: | `nis.schema` |
| Sudo | | | :white_check_mark: | `sudo.schema` |
| SSH | :white_check_mark: | | | `openssh-lpk.schema` |
| Systems | | | :white_check_mark: | `nis.schema` |
| DNS | | | :white_check_mark: | Custom DNS |
| DHCP | | | :white_check_mark: | Custom DHCP |
| Mail | :white_check_mark: | | | `cosine.schema` |
