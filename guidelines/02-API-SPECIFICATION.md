# HERACLES - Spécification API REST

> **Référence**: Ce document définit le contrat d'API REST d'Heracles.
> **Format**: OpenAPI 3.0 compatible

---

## 1. Conventions Générales

### 1.1 Base URL

```
Production: https://heracles.example.com/api/v1
Development: http://localhost:8000/api/v1
```

### 1.2 Versioning

- L'API est versionnée via le path: `/api/v1/`, `/api/v2/`
- Une version est supportée minimum 12 mois après dépréciation
- Les breaking changes nécessitent une nouvelle version majeure

### 1.3 Format des Réponses

Toutes les réponses sont en JSON avec les headers:
```http
Content-Type: application/json; charset=utf-8
```

### 1.4 Codes HTTP Utilisés

| Code | Signification | Utilisation |
|------|---------------|-------------|
| 200 | OK | GET, PUT réussis |
| 201 | Created | POST réussi |
| 204 | No Content | DELETE réussi |
| 400 | Bad Request | Validation échouée |
| 401 | Unauthorized | Token manquant/invalide |
| 403 | Forbidden | ACL refusé |
| 404 | Not Found | Ressource inexistante |
| 409 | Conflict | Entrée déjà existante |
| 422 | Unprocessable Entity | Erreur métier |
| 500 | Internal Server Error | Erreur serveur |

### 1.5 Format des Erreurs

```json
{
  "error": {
    "code": "USER_NOT_FOUND",
    "message": "User with uid 'jdoe' not found",
    "details": {
      "uid": "jdoe",
      "search_base": "ou=people,dc=example,dc=com"
    }
  }
}
```

### 1.6 Pagination

Pour les endpoints de liste:

```http
GET /api/v1/users?limit=20&offset=40
```

Réponse:
```json
{
  "data": [...],
  "pagination": {
    "total": 150,
    "limit": 20,
    "offset": 40,
    "has_more": true
  }
}
```

### 1.7 Filtrage

Syntaxe de filtre LDAP simplifiée:

```http
GET /api/v1/users?filter=cn:contains:john&filter=mail:ends:@example.com
```

Opérateurs supportés:
- `eq` - Égalité exacte
- `contains` - Contient
- `starts` - Commence par
- `ends` - Termine par
- `present` - Attribut présent

---

## 2. Authentification

### 2.1 POST /auth/login

Authentifie un utilisateur et retourne des tokens.

**Request:**
```json
{
  "username": "admin",
  "password": "secret"
}
```

**Response 200:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "dn": "uid=admin,ou=people,dc=example,dc=com",
    "uid": "admin",
    "cn": "Administrator"
  }
}
```

**Response 401:**
```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid username or password"
  }
}
```

### 2.2 POST /auth/refresh

Renouvelle un access token.

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response 200:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_in": 1800
}
```

### 2.3 POST /auth/logout

Invalide les tokens de l'utilisateur.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Response 204:** (No Content)

### 2.4 GET /auth/me

Retourne les informations de l'utilisateur courant.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Response 200:**
```json
{
  "dn": "uid=admin,ou=people,dc=example,dc=com",
  "uid": "admin",
  "cn": "Administrator",
  "mail": "admin@example.com",
  "permissions": ["user:read", "user:write", "group:read"]
}
```

---

## 3. Utilisateurs (/users)

### 3.1 GET /users

Liste les utilisateurs.

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| limit | int | 50 | Nombre max de résultats |
| offset | int | 0 | Décalage pour pagination |
| filter | string | - | Filtre de recherche |
| attributes | string | - | Attributs à retourner (comma-separated) |

**Response 200:**
```json
{
  "data": [
    {
      "dn": "uid=jdoe,ou=people,dc=example,dc=com",
      "uid": "jdoe",
      "cn": "John Doe",
      "sn": "Doe",
      "givenName": "John",
      "mail": "jdoe@example.com",
      "objectClass": ["inetOrgPerson", "posixAccount"],
      "uidNumber": 10001,
      "gidNumber": 10001
    }
  ],
  "pagination": {
    "total": 150,
    "limit": 50,
    "offset": 0,
    "has_more": true
  }
}
```

### 3.2 GET /users/{uid}

Récupère un utilisateur par son UID.

**Response 200:**
```json
{
  "dn": "uid=jdoe,ou=people,dc=example,dc=com",
  "uid": "jdoe",
  "cn": "John Doe",
  "sn": "Doe",
  "givenName": "John",
  "mail": "jdoe@example.com",
  "telephoneNumber": "+33 1 23 45 67 89",
  "objectClass": ["inetOrgPerson", "posixAccount", "shadowAccount"],
  "uidNumber": 10001,
  "gidNumber": 10001,
  "homeDirectory": "/home/jdoe",
  "loginShell": "/bin/bash",
  "shadowLastChange": 19739,
  "shadowMax": 99999,
  "tabs": {
    "posix": true,
    "sudo": false,
    "ssh": true
  }
}
```

### 3.3 POST /users

Crée un nouvel utilisateur.

**Request:**
```json
{
  "uid": "jdoe",
  "cn": "John Doe",
  "sn": "Doe",
  "givenName": "John",
  "mail": "jdoe@example.com",
  "userPassword": "SecureP@ss123",
  "posix": {
    "uidNumber": null,
    "gidNumber": 10000,
    "homeDirectory": "/home/jdoe",
    "loginShell": "/bin/bash"
  }
}
```

**Notes:**
- `uidNumber: null` → allocation automatique
- `userPassword` → hashé automatiquement selon la méthode configurée

**Response 201:**
```json
{
  "dn": "uid=jdoe,ou=people,dc=example,dc=com",
  "uid": "jdoe",
  "cn": "John Doe",
  ...
}
```

### 3.4 PUT /users/{uid}

Met à jour un utilisateur.

**Request:**
```json
{
  "cn": "John M. Doe",
  "mail": "john.doe@example.com",
  "telephoneNumber": "+33 1 98 76 54 32"
}
```

**Notes:**
- Seuls les champs fournis sont modifiés
- Pour supprimer un attribut, utiliser `null`

**Response 200:**
```json
{
  "dn": "uid=jdoe,ou=people,dc=example,dc=com",
  "uid": "jdoe",
  "cn": "John M. Doe",
  ...
}
```

### 3.5 DELETE /users/{uid}

Supprime un utilisateur.

**Response 204:** (No Content)

### 3.6 PUT /users/{uid}/password

Change le mot de passe d'un utilisateur.

**Request:**
```json
{
  "current_password": "OldP@ss123",
  "new_password": "NewSecureP@ss456"
}
```

**Notes:**
- `current_password` requis sauf pour admin
- Validation des règles de complexité configurées

**Response 200:**
```json
{
  "message": "Password changed successfully"
}
```

### 3.7 POST /users/{uid}/lock

Verrouille un compte utilisateur.

**Response 200:**
```json
{
  "uid": "jdoe",
  "locked": true,
  "locked_at": "2026-01-17T10:30:00Z"
}
```

### 3.8 POST /users/{uid}/unlock

Déverrouille un compte utilisateur.

**Response 200:**
```json
{
  "uid": "jdoe",
  "locked": false
}
```

---

## 4. Groupes (/groups)

### 4.1 GET /groups

Liste les groupes.

**Response 200:**
```json
{
  "data": [
    {
      "dn": "cn=developers,ou=groups,dc=example,dc=com",
      "cn": "developers",
      "description": "Development team",
      "objectClass": ["groupOfNames", "posixGroup"],
      "gidNumber": 20001,
      "memberCount": 15
    }
  ],
  "pagination": {...}
}
```

### 4.2 GET /groups/{cn}

Récupère un groupe par son CN.

**Response 200:**
```json
{
  "dn": "cn=developers,ou=groups,dc=example,dc=com",
  "cn": "developers",
  "description": "Development team",
  "gidNumber": 20001,
  "members": [
    {"uid": "jdoe", "cn": "John Doe"},
    {"uid": "asmith", "cn": "Alice Smith"}
  ]
}
```

### 4.3 POST /groups

Crée un nouveau groupe.

**Request:**
```json
{
  "cn": "qa-team",
  "description": "Quality Assurance team",
  "gidNumber": null,
  "members": ["uid=jdoe,ou=people,dc=example,dc=com"]
}
```

**Response 201:** Groupe créé

### 4.4 PUT /groups/{cn}

Met à jour un groupe.

### 4.5 DELETE /groups/{cn}

Supprime un groupe.

### 4.6 POST /groups/{cn}/members

Ajoute des membres à un groupe.

**Request:**
```json
{
  "members": ["jdoe", "asmith"]
}
```

### 4.7 DELETE /groups/{cn}/members

Retire des membres d'un groupe.

**Request:**
```json
{
  "members": ["jdoe"]
}
```

---

## 5. Systèmes (/systems)

### 5.1 Types de Systèmes

| Type | Description | objectClass |
|------|-------------|-------------|
| server | Serveur | hrcServer |
| workstation | Station de travail | hrcWorkstation |
| terminal | Terminal | hrcTerminal |
| printer | Imprimante | hrcPrinter |
| component | Composant réseau | hrcComponent |
| phone | Téléphone | hrcPhone |
| mobile | Mobile | hrcMobile |

### 5.2 GET /systems

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| type | string | Filtre par type |

### 5.3 GET /systems/{cn}

### 5.4 POST /systems

**Request:**
```json
{
  "cn": "srv-web-01",
  "type": "server",
  "description": "Web server #1",
  "ipHostNumber": "192.168.1.10",
  "macAddress": "00:11:22:33:44:55"
}
```

### 5.5 PUT /systems/{cn}

### 5.6 DELETE /systems/{cn}

---

## 6. Sudo (/sudo)

### 6.1 GET /sudo/rules

Liste les règles sudo.

**Response 200:**
```json
{
  "data": [
    {
      "dn": "cn=developers-sudo,ou=sudoers,dc=example,dc=com",
      "cn": "developers-sudo",
      "sudoUser": ["%developers"],
      "sudoHost": ["ALL"],
      "sudoCommand": ["/usr/bin/docker", "/usr/bin/systemctl restart nginx"]
    }
  ]
}
```

### 6.2 POST /sudo/rules

**Request:**
```json
{
  "cn": "webapp-deploy",
  "sudoUser": ["%deployers", "jdoe"],
  "sudoHost": ["srv-web-*"],
  "sudoCommand": ["/usr/local/bin/deploy.sh"],
  "sudoOption": ["!authenticate"]
}
```

---

## 7. SSH Keys (/ssh)

### 7.1 GET /users/{uid}/ssh-keys

Liste les clés SSH d'un utilisateur.

**Response 200:**
```json
{
  "keys": [
    {
      "id": "sha256:AAAA...",
      "type": "ssh-ed25519",
      "fingerprint": "SHA256:xxxxxxxxxxx",
      "comment": "jdoe@laptop",
      "added_at": "2025-06-15T10:00:00Z"
    }
  ]
}
```

### 7.2 POST /users/{uid}/ssh-keys

**Request:**
```json
{
  "public_key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIxxx jdoe@laptop"
}
```

### 7.3 DELETE /users/{uid}/ssh-keys/{id}

---

## 8. ACL (/acl)

### 8.1 GET /acl/roles

Liste les rôles ACL.

**Response 200:**
```json
{
  "data": [
    {
      "dn": "cn=admin-role,ou=aclroles,dc=example,dc=com",
      "cn": "admin-role",
      "description": "Full administrator access",
      "permissions": [
        "user:crwdms",
        "group:crwdms",
        "system:crwdms"
      ]
    }
  ]
}
```

### 8.2 GET /acl/assignments

Liste les assignations ACL.

### 8.3 POST /acl/check

Vérifie une permission pour l'utilisateur courant.

**Request:**
```json
{
  "action": "write",
  "object_type": "user",
  "object_dn": "uid=jdoe,ou=people,dc=example,dc=com",
  "attribute": "mail"
}
```

**Response 200:**
```json
{
  "allowed": true,
  "reason": "Role admin-role grants user:w on ou=people"
}
```

---

## 9. Schema (/schema)

### 9.1 GET /schema/object-types

Liste les types d'objets disponibles.

**Response 200:**
```json
{
  "types": [
    {
      "name": "user",
      "label": "Utilisateur",
      "icon": "user",
      "base_dn": "ou=people",
      "structural_class": "inetOrgPerson",
      "tabs": ["personal", "posix", "sudo", "ssh"]
    },
    {
      "name": "group",
      "label": "Groupe",
      "icon": "users",
      "base_dn": "ou=groups",
      "structural_class": "groupOfNames"
    }
  ]
}
```

### 9.2 GET /schema/object-types/{type}/form

Retourne le schéma de formulaire pour un type d'objet.

**Response 200:**
```json
{
  "type": "user",
  "sections": [
    {
      "id": "personal",
      "label": "Informations personnelles",
      "fields": [
        {
          "name": "uid",
          "type": "string",
          "label": "Identifiant",
          "required": true,
          "pattern": "^[a-z][a-z0-9_-]{2,31}$",
          "readonly_after_create": true
        },
        {
          "name": "cn",
          "type": "string",
          "label": "Nom complet",
          "required": true
        },
        {
          "name": "mail",
          "type": "email",
          "label": "Email",
          "required": false
        }
      ]
    }
  ]
}
```

---

## 10. Audit (/audit)

### 10.1 GET /audit/logs

Liste les logs d'audit.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| action | string | Filtre par action (create, modify, delete) |
| actor | string | Filtre par utilisateur |
| target | string | Filtre par DN cible |
| from | datetime | Date de début |
| to | datetime | Date de fin |

**Response 200:**
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "timestamp": "2026-01-17T10:30:00Z",
      "action": "modify",
      "actor": "uid=admin,ou=people,dc=example,dc=com",
      "target": "uid=jdoe,ou=people,dc=example,dc=com",
      "changes": [
        {"attribute": "mail", "old": "old@example.com", "new": "new@example.com"}
      ]
    }
  ]
}
```

---

## 11. Health & Info

### 11.1 GET /health

**Response 200:**
```json
{
  "status": "healthy",
  "checks": {
    "ldap": {"status": "up", "latency_ms": 5},
    "database": {"status": "up", "latency_ms": 2},
    "redis": {"status": "up", "latency_ms": 1}
  }
}
```

### 11.2 GET /info

**Response 200:**
```json
{
  "name": "Heracles",
  "version": "1.0.0",
  "api_version": "v1",
  "ldap_base": "dc=example,dc=com",
  "plugins": ["core", "posix", "sudo", "ssh", "systems", "dns", "dhcp", "mail"]
}
```

---

## 12. DNS (/dns)

### 12.1 GET /dns/zones

Liste les zones DNS.

**Response 200:**
```json
{
  "data": [
    {
      "dn": "dc=example.com,ou=dns,dc=example,dc=com",
      "zoneName": "example.com",
      "soa": "ns1.example.com. admin.example.com. 2026020401 3600 900 604800 86400",
      "recordCount": 15
    }
  ]
}
```

### 12.2 POST /dns/zones

Crée une zone DNS.

### 12.3 GET /dns/zones/{name}/records

Liste les enregistrements d'une zone (types: A, AAAA, MX, NS, CNAME, PTR, TXT, SRV).

### 12.4 POST /dns/zones/{name}/records

Crée un enregistrement DNS.

---

## 13. DHCP (/dhcp)

### 13.1 Types d'objets DHCP

| Type | Description | objectClass |
|------|-------------|-------------|
| service | Service DHCP | dhcpService |
| shared_network | Réseau partagé | dhcpSharedNetwork |
| subnet | Sous-réseau | dhcpSubnet |
| pool | Pool d'adresses | dhcpPool |
| host | Hôte réservé | dhcpHost |
| group | Groupe DHCP | dhcpGroup |
| class | Classe DHCP | dhcpClass |
| subclass | Sous-classe | dhcpSubClass |
| tsig_key | Clé TSIG | dhcpTSigKey |
| dns_zone | Zone DNS liée | dhcpDnsZone |
| failover_peer | Failover | dhcpFailOverPeer |

### 13.2 GET /dhcp/services

### 13.3 POST /dhcp/services

### 13.4 GET /dhcp/subnets

### 13.5 POST /dhcp/subnets

### 13.6 GET /dhcp/hosts

### 13.7 POST /dhcp/hosts

---

## 14. Départements (/departments)

### 14.1 GET /departments

Liste les départements.

### 14.2 GET /departments/tree

Retourne l'arbre hiérarchique des départements.

### 14.3 GET /departments/{dn}

Récupère un département par son DN.

### 14.4 POST /departments

Crée un département.

### 14.5 PUT /departments/{dn}

Met à jour un département.

### 14.6 DELETE /departments/{dn}

Supprime un département.

---

## 15. Configuration (/config)

### 15.1 GET /config

Retourne toutes les catégories et settings de configuration.

### 15.2 GET /config/{key}

Récupère une valeur de configuration.

### 15.3 PUT /config/{key}

Met à jour une valeur de configuration.

### 15.4 DELETE /config/{key}

Réinitialise une valeur à sa valeur par défaut.

---

## 16. Plugins (/plugins)

### 16.1 GET /plugins

Liste les plugins activés avec leurs métadonnées.

**Response 200:**
```json
{
  "data": [
    {
      "name": "posix",
      "version": "1.0.0",
      "description": "POSIX account management",
      "enabled": true,
      "object_types": ["user", "group", "mixed-group"],
      "tabs": [
        {"id": "posix-user", "label": "Unix", "object_type": "user"},
        {"id": "posix-group", "label": "POSIX", "object_type": "group"}
      ]
    }
  ]
}
```

### 16.2 GET /plugins/{name}

Récupère les informations détaillées d'un plugin.

---

## 17. Mail (/mail)

### 17.1 GET /mail/users/{uid}

Récupère les attributs mail d'un utilisateur.

### 17.2 POST /mail/users/{uid}

Active/met à jour les attributs mail d'un utilisateur.

### 17.3 DELETE /mail/users/{uid}

Désactive les attributs mail d'un utilisateur.
