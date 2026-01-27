# Configuration

## Architecture réseau

```
┌─────────────────────────────────────────────────────────────┐
│                       HOST                                   │
│                                                              │
│   Docker: LDAP(:389), PostgreSQL(:5432), Redis, API(:8000)  │
│                          │                                   │
│                   192.168.56.1                               │
│                          │                                   │
├──────────────────────────┼───────────────────────────────────┤
│              VirtualBox Private Network                      │
│                   192.168.56.0/24                            │
│                          │                                   │
│         ┌────────────────┴────────────────┐                  │
│         ▼                                 ▼                  │
│  ┌─────────────┐                  ┌─────────────┐           │
│  │   server1   │                  │ workstation1│           │
│  │ .56.10      │                  │ .56.11      │           │
│  │ SSSD + SSH  │                  │ SSSD + SSH  │           │
│  └─────────────┘                  └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

## Réseau VirtualBox

```bash
# Créer le réseau host-only si nécessaire
VBoxManage hostonlyif create
VBoxManage hostonlyif ipconfig vboxnet0 --ip 192.168.56.1

# Vérifier
ip addr show vboxnet0
```

## Configuration SSSD

Fichier `/etc/sssd/sssd.conf` sur les VMs :

```ini
[sssd]
services = nss, pam, sudo
domains = heracles.local

[domain/heracles.local]
id_provider = ldap
auth_provider = ldap
sudo_provider = ldap

ldap_uri = ldap://192.168.56.1:389
ldap_search_base = dc=heracles,dc=local
ldap_default_bind_dn = cn=admin,dc=heracles,dc=local
ldap_default_authtok = admin_secret

# Schema RFC2307 (posixGroup avec memberUid)
ldap_schema = rfc2307
ldap_group_object_class = posixGroup
ldap_group_member = memberUid
```

## Configuration SSH

Le script `/usr/local/bin/ldap-ssh-keys.sh` récupère les clés depuis LDAP :

```bash
#!/bin/bash
USER="$1"
ldapsearch -x -H ldap://192.168.56.1:389 \
  -b "uid=$USER,ou=people,dc=heracles,dc=local" \
  sshPublicKey 2>/dev/null | awk '/^sshPublicKey:/ {print $2}'
```

Configuration `/etc/ssh/sshd_config` :

```
AuthorizedKeysCommand /usr/local/bin/ldap-ssh-keys.sh %u
AuthorizedKeysCommandUser nobody
```

## Configuration Sudo

Fichier `/etc/nsswitch.conf` :

```
sudoers: files sss
```

Les règles sudo sont stockées dans `ou=sudoers,dc=heracles,dc=local`.

## Variables d'environnement

| Variable | Valeur par défaut | Description |
|----------|-------------------|-------------|
| LDAP_SERVER_IP | 192.168.56.1 | IP du serveur LDAP |
| LDAP_PORT | 389 | Port LDAP |
| LDAP_BASE_DN | dc=heracles,dc=local | Base DN |
| LDAP_BIND_DN | cn=admin,dc=heracles,dc=local | Bind DN |
| LDAP_BIND_PASSWORD | admin_secret | Mot de passe |
