# Plugin Sudo - Documentation

## Vue d'ensemble

Le plugin Sudo gère les règles sudoers via LDAP. Il remplace le fichier `/etc/sudoers` par une configuration centralisée.

## Architecture

```
┌─────────────────┐      REST API       ┌─────────────────┐
│   Heracles UI   │ ──────────────────▶ │   Sudo Plugin   │
│  (Page Sudo)    │                     │   (FastAPI)     │
└─────────────────┘                     └────────┬────────┘
                                                 │ LDAP
                                                 ▼
┌─────────────────┐      LDAP Query     ┌─────────────────┐
│  Serveur Linux  │ ◀─────────────────▶ │    OpenLDAP     │
│   (sudo)        │   via sudo-ldap     │  (sudoRole)     │
└─────────────────┘                     └─────────────────┘
```

Le binaire `sudo` interroge LDAP via `libsudoers` pour vérifier les autorisations.

## ObjectClass LDAP

| ObjectClass | Type | Attributs |
|-------------|------|-----------|
| `sudoRole` | Structural | sudoUser, sudoHost, sudoCommand, sudoOption |

## Schéma sudoRole

| Attribut | Multi | Description |
|----------|-------|-------------|
| `cn` | Non | Nom de la règle |
| `sudoUser` | Oui | Utilisateurs/groupes autorisés |
| `sudoHost` | Oui | Machines où la règle s'applique |
| `sudoCommand` | Oui | Commandes autorisées |
| `sudoOption` | Oui | Options sudo (NOPASSWD, etc.) |
| `sudoRunAs` | Oui | Utilisateur cible (root par défaut) |
| `sudoNotBefore` | Non | Date de début de validité |
| `sudoNotAfter` | Non | Date de fin de validité |

## Schémas de données

### SudoRoleCreate
Création d'une règle sudo.

```python
{
    "cn": "admins-all",
    "description": "Full admin access",
    "sudoUser": ["%admins"],       # % = groupe
    "sudoHost": ["ALL"],
    "sudoCommand": ["ALL"],
    "sudoOption": ["!authenticate"],  # NOPASSWD
    "sudoRunAs": ["ALL"]
}
```

### SudoRoleRead
Lecture d'une règle sudo.

```python
{
    "dn": "cn=admins-all,ou=sudoers,dc=example,dc=com",
    "cn": "admins-all",
    "description": "Full admin access",
    "sudoUser": ["%admins"],
    "sudoHost": ["ALL"],
    "sudoCommand": ["ALL"],
    "sudoOption": ["!authenticate"],
    "sudoRunAs": ["ALL"],
    "sudoNotBefore": null,
    "sudoNotAfter": null,
    "isDefault": false,
    "isValid": true
}
```

## Endpoints API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/sudo/roles` | Lister les règles sudo |
| GET | `/sudo/roles/{cn}` | Lire une règle |
| POST | `/sudo/roles` | Créer une règle |
| PUT | `/sudo/roles/{cn}` | Modifier une règle |
| DELETE | `/sudo/roles/{cn}` | Supprimer une règle |

## Syntaxe sudoUser

| Préfixe | Signification | Exemple |
|---------|---------------|---------|
| (aucun) | Utilisateur | `jdoe` |
| `%` | Groupe POSIX | `%admins` |
| `+` | Netgroup | `+sysadmins` |
| `#` | UID | `#1000` |
| `%#` | GID | `%#1000` |
| `ALL` | Tous | `ALL` |

## Syntaxe sudoCommand

| Valeur | Signification |
|--------|---------------|
| `ALL` | Toutes les commandes |
| `/usr/bin/apt` | Commande spécifique |
| `/usr/bin/apt update` | Commande avec arguments |
| `!/usr/bin/rm` | Négation (interdit) |
| `sudoedit /etc/hosts` | Édition de fichier |

## Options courantes

| Option | Équivalent sudoers | Effet |
|--------|-------------------|-------|
| `!authenticate` | `NOPASSWD:` | Pas de mot de passe |
| `!requiretty` | `!requiretty` | Pas de TTY requis |
| `env_keep+=SSH_AUTH_SOCK` | `env_keep` | Conserver variable |
| `timestamp_timeout=30` | - | Timeout en minutes |

## Configuration sudo-ldap

```bash
# /etc/sudo-ldap.conf (ou via nsswitch.conf)
uri ldap://ldap.example.com
sudoers_base ou=sudoers,dc=example,dc=com
binddn cn=sudo,ou=services,dc=example,dc=com
bindpw secret
```

Ou via nsswitch :
```bash
# /etc/nsswitch.conf
sudoers: ldap files
```

## Workflow typique

1. **Créer une règle pour les développeurs**
   ```bash
   POST /sudo/roles {
     "cn": "dev-docker",
     "sudoUser": ["%developers"],
     "sudoHost": ["ALL"],
     "sudoCommand": ["/usr/bin/docker", "/usr/bin/docker-compose"],
     "sudoOption": ["!authenticate"]
   }
   ```

2. **Un développeur peut maintenant utiliser docker**
   ```bash
   sudo docker ps  # Sans mot de passe
   ```

## Règle defaults

La règle spéciale `defaults` définit les options globales :

```python
{
    "cn": "defaults",
    "sudoOption": [
        "env_reset",
        "mail_badpass",
        "secure_path=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
    ]
}
```

## Structure LDAP

```
ou=sudoers,dc=example,dc=com
├── cn=defaults
│   └── sudoOption: env_reset, mail_badpass, ...
├── cn=admins-all
│   ├── sudoUser: %admins
│   ├── sudoHost: ALL
│   ├── sudoCommand: ALL
│   └── sudoOption: !authenticate
└── cn=dev-docker
    ├── sudoUser: %developers
    ├── sudoHost: ALL
    └── sudoCommand: /usr/bin/docker, /usr/bin/docker-compose
```
