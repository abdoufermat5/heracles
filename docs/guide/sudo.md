# Sudo Roles

Define privilege escalation rules for users on Unix/Linux systems using LDAP-stored sudo policies.

---

## Role List

View all sudo roles with their assigned users, hosts, and commands.

![Sudo Roles](../assets/security/sudo_roles_list.png)

---

## Creating a Sudo Role

Click **Create Role** to define a new sudo policy.

![Create Role](../assets/security/create_role_modal.png)

### Fields

| Field | Description | Example |
|---|---|---|
| Role name (`cn`) | Unique rule identifier | `web-admins-sudo` |
| Users (`sudoUser`) | Users or groups allowed | `jdoe`, `%webadmins` |
| Hosts (`sudoHost`) | Target machines | `ALL`, `web*.example.com` |
| Commands (`sudoCommand`) | Permitted commands | `/usr/bin/systemctl restart nginx` |
| Options (`sudoOption`) | Sudo behavior flags | `!authenticate`, `NOPASSWD` |
| Run As (`sudoRunAs`) | Execute as this user | `root` |

### User Syntax

| Syntax | Meaning |
|---|---|
| `jdoe` | Specific user |
| `%webadmins` | All members of group `webadmins` |
| `ALL` | Any user |

### Host Syntax

| Syntax | Meaning |
|---|---|
| `ALL` | Any host |
| `server1` | Specific hostname |
| `192.168.1.0/24` | Network range |
| `web*.example.com` | Wildcard pattern |

### Command Syntax

| Syntax | Meaning |
|---|---|
| `ALL` | Any command |
| `/usr/bin/systemctl restart nginx` | Specific command with args |
| `/usr/bin/systemctl *` | Command with wildcard args |
| `!/usr/bin/su` | Deny specific command |

---

## How It Works

Sudo rules are stored in LDAP under `ou=sudoers` using the standard `sudoRole` object class. Linux clients configured with SSSD or `nss_ldap` can read these rules directly from the directory.

```
dn: cn=web-admins-sudo,ou=sudoers,dc=example,dc=com
objectClass: sudoRole
cn: web-admins-sudo
sudoUser: %webadmins
sudoHost: ALL
sudoCommand: /usr/bin/systemctl restart nginx
sudoCommand: /usr/bin/systemctl restart apache2
sudoOption: !authenticate
```

---

## Client Configuration

On Linux machines using SSSD, add to `/etc/sssd/sssd.conf`:

```ini
[domain/example.com]
sudo_provider = ldap
ldap_sudo_search_base = ou=sudoers,dc=example,dc=com
```

Then enable the sudo responder:

```ini
[sssd]
services = nss, pam, sudo
```
