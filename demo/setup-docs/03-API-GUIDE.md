# Guide API Heracles

## Authentification

L'API utilise des tokens JWT. Obtenez un token avant toute requête :

```bash
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "hrc-admin", "password": "hrc-admin-secret"}' | jq -r '.access_token')
```

Utilisez le token dans les requêtes :

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/users
```

## Endpoints principaux

### Utilisateurs

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/users` | Lister les utilisateurs |
| POST | `/api/v1/users` | Créer un utilisateur |
| GET | `/api/v1/users/{uid}` | Détails d'un utilisateur |
| DELETE | `/api/v1/users/{uid}` | Supprimer un utilisateur |

**Créer un utilisateur :**

```bash
curl -X POST "http://localhost:8000/api/v1/users" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "newuser",
    "givenName": "New",
    "sn": "User",
    "cn": "New User",
    "mail": "newuser@heracles.local",
    "password": "secretpassword123"
  }'
```

### POSIX

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/v1/users/{uid}/posix` | Activer POSIX |
| DELETE | `/api/v1/users/{uid}/posix` | Désactiver POSIX |
| GET | `/api/v1/posix/groups` | Lister les groupes |
| POST | `/api/v1/posix/groups` | Créer un groupe |

**Activer POSIX :**

```bash
curl -X POST "http://localhost:8000/api/v1/users/newuser/posix" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "uidNumber": 10010,
    "gidNumber": 10010,
    "homeDirectory": "/home/newuser",
    "loginShell": "/bin/bash"
  }'
```

### SSH

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/v1/ssh/users/{uid}/activate` | Activer SSH |
| POST | `/api/v1/ssh/users/{uid}/deactivate` | Désactiver SSH |
| POST | `/api/v1/ssh/users/{uid}/keys` | Ajouter une clé |
| DELETE | `/api/v1/ssh/users/{uid}/keys/{fingerprint}` | Supprimer une clé |

**Activer SSH et ajouter une clé :**

```bash
# Activer SSH
curl -X POST "http://localhost:8000/api/v1/ssh/users/newuser/activate" \
  -H "Authorization: Bearer $TOKEN"

# Ajouter une clé
curl -X POST "http://localhost:8000/api/v1/ssh/users/newuser/keys" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"key": "ssh-ed25519 AAAAC3... comment"}'
```

### Sudo

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/sudo/roles` | Lister les règles |
| POST | `/api/v1/sudo/roles` | Créer une règle |
| GET | `/api/v1/sudo/roles/{cn}` | Détails d'une règle |
| DELETE | `/api/v1/sudo/roles/{cn}` | Supprimer une règle |

**Créer une règle sudo :**

```bash
curl -X POST "http://localhost:8000/api/v1/sudo/roles" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cn": "newuser-sudo",
    "sudoUser": ["newuser"],
    "sudoHost": ["ALL"],
    "sudoCommand": ["ALL"],
    "sudoOption": ["!authenticate"]
  }'
```

## Documentation interactive

Accédez à Swagger UI : http://localhost:8000/api/docs

> Note: Nécessite `DEBUG=true` dans la configuration API.
