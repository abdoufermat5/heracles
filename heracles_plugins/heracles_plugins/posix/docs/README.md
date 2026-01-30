# Plugin POSIX - Documentation

## Vue d'ensemble

Le plugin POSIX gère les comptes Unix/Linux sur les utilisateurs LDAP. Il ajoute les attributs nécessaires pour l'authentification système via NSS/PAM.

## Architecture

```
┌─────────────────┐      REST API       ┌─────────────────┐
│   Heracles UI   │ ──────────────────▶ │   POSIX Plugin  │
│  (Onglet Unix)  │                     │   (FastAPI)     │
└─────────────────┘                     └────────┬────────┘
                                                 │ LDAP
                                                 ▼
┌─────────────────┐      NSS/PAM        ┌─────────────────┐
│  Serveur Linux  │ ◀─────────────────▶ │    OpenLDAP     │
│  (ssh, login)   │                     │                 │
└─────────────────┘                     └─────────────────┘
```

## ObjectClasses LDAP

| ObjectClass | Type | Usage |
|-------------|------|-------|
| `posixAccount` | Auxiliary | Compte Unix sur user |
| `shadowAccount` | Auxiliary | Expiration mot de passe |
| `posixGroup` | Structural | Groupe Unix pur |
| `groupOfNames` + `posixGroupAux` | Mixed | Groupe LDAP avec GID |
| `hostObject` | Auxiliary | Restriction d'accès par host |

## Schémas de données

### PosixAccountCreate
Activation POSIX sur un utilisateur existant.

```python
{
    "gidNumber": 10000,           # GID du groupe primaire (requis)
    "homeDirectory": "/home/jdoe", # Répertoire home (requis)
    "loginShell": "/bin/bash",     # Shell (défaut: /bin/bash)
    "uidNumber": null,             # Auto-alloué si null
    "trustMode": "fullaccess",     # fullaccess | byhost
    "host": ["server1", "server2"] # Requis si trustMode=byhost
}
```

### PosixAccountRead
Lecture des attributs POSIX.

```python
{
    "uidNumber": 10001,
    "gidNumber": 10000,
    "homeDirectory": "/home/jdoe",
    "loginShell": "/bin/bash",
    "gecos": "John Doe",
    "shadowLastChange": 19754,     # Jours depuis epoch
    "shadowMax": 99999,
    "shadowExpire": null,
    "accountStatus": "active",     # active | expired | password_expired | locked
    "trustMode": "fullaccess",
    "host": [],
    "primaryGroupCn": "users",
    "groupMemberships": ["developers", "admins"]
}
```

## Endpoints API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/posix/users/{uid}` | Lire les attributs POSIX d'un user |
| POST | `/posix/users/{uid}/activate` | Activer POSIX sur un user |
| PUT | `/posix/users/{uid}` | Modifier les attributs POSIX |
| DELETE | `/posix/users/{uid}/deactivate` | Désactiver POSIX |
| GET | `/posix/groups` | Lister les groupes POSIX |
| POST | `/posix/groups` | Créer un groupe POSIX |
| GET | `/posix/mixed-groups` | Lister les groupes mixtes |
| POST | `/posix/mixed-groups` | Créer un groupe mixte |

## Allocation UID/GID

Le plugin alloue automatiquement les UID/GID dans une plage configurable :

```
UID_MIN = 10000
UID_MAX = 60000
GID_MIN = 10000
GID_MAX = 60000
```

L'allocation est atomique : le plugin scanne tous les UID/GID existants et attribue le premier disponible.

## System Trust (hostObject)

Permet de restreindre l'accès d'un utilisateur à certains systèmes :

| Mode | Attribut host | Effet |
|------|---------------|-------|
| `fullaccess` | `*` | Accès à tous les systèmes |
| `byhost` | `["server1", "server2"]` | Accès limité aux hosts listés |

## Workflow typique

1. **Créer un groupe POSIX** (optionnel)
   ```bash
   POST /posix/groups {"cn": "developers", "description": "Dev team"}
   ```

2. **Activer POSIX sur un utilisateur**
   ```bash
   POST /posix/users/jdoe/activate {
     "gidNumber": 10000,
     "homeDirectory": "/home/jdoe"
   }
   ```

3. **L'utilisateur peut maintenant se connecter en SSH**
   ```bash
   ssh jdoe@server1.example.com
   ```

## Structure LDAP résultante

```
uid=jdoe,ou=people,dc=example,dc=com
├── objectClass: inetOrgPerson
├── objectClass: posixAccount
├── objectClass: shadowAccount
├── uid: jdoe
├── uidNumber: 10001
├── gidNumber: 10000
├── homeDirectory: /home/jdoe
├── loginShell: /bin/bash
├── shadowLastChange: 19754
└── shadowMax: 99999
```
