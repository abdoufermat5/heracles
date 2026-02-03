# HERACLES - Sécurité

> **Référence**: Ce document définit les exigences et règles de sécurité pour Heracles.
> **Criticité**: HAUTE - Ce document doit être respecté sans exception.

---

## 1. Principes de Sécurité

### 1.1 Defense in Depth

```
┌─────────────────────────────────────────────────────────────────┐
│                        COUCHES DE SÉCURITÉ                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 1. Réseau: TLS, Firewall, Rate limiting                 │    │
│  │  ┌───────────────────────────────────────────────────┐  │    │
│  │  │ 2. Application: Auth, ACL, Validation             │  │    │
│  │  │  ┌─────────────────────────────────────────────┐  │  │    │
│  │  │  │ 3. Données: Encryption, Hashing, Audit     │  │  │    │
│  │  │  │  ┌───────────────────────────────────────┐  │  │  │    │
│  │  │  │  │ 4. LDAP: Bind, TLS, ACL              │  │  │  │    │
│  │  │  │  └───────────────────────────────────────┘  │  │  │    │
│  │  │  └─────────────────────────────────────────────┘  │  │    │
│  │  └───────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Principe du Moindre Privilège

- Les utilisateurs n'ont que les droits nécessaires
- Les services ne s'exécutent pas en root
- Les connexions LDAP utilisent un compte dédié avec droits limités

### 1.3 Zero Trust

- Toute requête est authentifiée et autorisée
- Les tokens ont une durée de vie limitée
- Les sessions peuvent être révoquées

---

## 2. Authentification

### 2.1 Méthodes Supportées

| Méthode | Utilisation | Priorité |
|---------|-------------|----------|
| **Form Login** | UI Web | P0 (v1.0) |
| **JWT Bearer** | API | P0 (v1.0) |
| **API Keys** | Intégrations | P1 (v1.1) |
| **OIDC** | SSO Enterprise | P2 (v2.0) |

### 2.2 Tokens JWT

#### Structure

```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "uid=jdoe,ou=people,dc=example,dc=com",
    "uid": "jdoe",
    "iat": 1737100000,
    "exp": 1737101800,
    "jti": "550e8400-e29b-41d4-a716-446655440000",
    "type": "access"
  }
}
```

#### Durées de Vie

| Token Type | Durée | Renouvellement |
|------------|-------|----------------|
| Access Token | 30 minutes | Via refresh token |
| Refresh Token | 7 jours | Via re-login |

#### Stockage

```typescript
// ❌ INTERDIT - localStorage (XSS vulnerable)
localStorage.setItem('token', jwt);

// ✅ CORRECT - httpOnly cookie (géré par backend)
// Le backend définit le cookie:
// Set-Cookie: access_token=xxx; HttpOnly; Secure; SameSite=Strict
```

### 2.3 Validation des Tokens

```python
# heracles_api/core/security.py

from datetime import datetime, timezone
from jose import jwt, JWTError
from fastapi import HTTPException, status

from heracles_api.core.config import settings


def verify_access_token(token: str) -> dict:
    """
    Vérifie et décode un access token JWT.
    
    Args:
        token: Le token JWT à vérifier
        
    Returns:
        dict: Les claims du token
        
    Raises:
        HTTPException 401: Token invalide ou expiré
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
        )
        
        # Vérification du type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        
        # Vérification de l'expiration (double check)
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
            )
        
        return payload
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
```

### 2.4 Blocage de Comptes

| Événement | Action |
|-----------|--------|
| 5 échecs de login en 15 min | Blocage temporaire 15 min |
| 10 échecs de login en 1h | Blocage 1h + alerte |
| 20 échecs de login en 24h | Blocage permanent + alerte admin |

```python
# Implémentation avec Redis
async def check_login_attempts(username: str, ip: str) -> None:
    """Vérifie et enregistre les tentatives de connexion."""
    
    key = f"login_attempts:{username}:{ip}"
    attempts = await redis.incr(key)
    
    if attempts == 1:
        await redis.expire(key, 3600)  # 1 hour window
    
    if attempts >= 5:
        # Blocage temporaire
        await redis.setex(f"blocked:{username}", 900, "1")  # 15 min
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
        )
```

---

## 3. Autorisation (ACL)

### 3.1 Modèle RBAC

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    User     │────▶│    Role     │────▶│ Permissions │
│   (jdoe)    │     │ (user-mgr)  │     │ (user:rw)   │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Target    │
                    │ (ou=people) │
                    └─────────────┘
```

### 3.2 Format des Permissions

Format standard:

```
{category}/{tab}:{permissions}:{target_filter}

Exemples:
- user/posixAccount:rwcd          # CRUD sur onglet POSIX
- user/*:r                        # Lecture sur tous onglets user
- group:crwd:(&(cn=dev-*))        # CRUD sur groupes dev-*
```

| Permission | Signification |
|------------|---------------|
| `c` | Create - Créer |
| `r` | Read - Lire |
| `w` | Write - Modifier |
| `d` | Delete - Supprimer |
| `m` | Move - Déplacer |
| `s` | Self - Auto-modification |

### 3.3 Vérification ACL

```python
# heracles_api/services/acl_service.py

from typing import Optional
from enum import Enum


class Permission(Enum):
    CREATE = "c"
    READ = "r"
    WRITE = "w"
    DELETE = "d"
    MOVE = "m"
    SELF = "s"


class AclService:
    """Service de vérification des ACL."""
    
    async def check(
        self,
        requester_dn: str,
        permission: Permission,
        object_type: str,
        target_dn: Optional[str] = None,
        attribute: Optional[str] = None,
    ) -> bool:
        """
        Vérifie si un utilisateur a une permission.
        
        Args:
            requester_dn: DN de l'utilisateur effectuant l'action
            permission: Permission requise
            object_type: Type d'objet (user, group, system)
            target_dn: DN de l'objet cible (optionnel pour create)
            attribute: Attribut spécifique (optionnel)
            
        Returns:
            bool: True si autorisé
        """
        # Admin bypass
        if await self._is_admin(requester_dn):
            return True
        
        # Self-modification check
        if permission == Permission.SELF and target_dn == requester_dn:
            if await self._has_self_permission(requester_dn, object_type, attribute):
                return True
        
        # Récupérer les rôles de l'utilisateur
        roles = await self._get_user_roles(requester_dn)
        
        # Vérifier chaque rôle
        for role in roles:
            if self._role_grants_permission(role, permission, object_type, target_dn, attribute):
                return True
        
        return False
    
    async def filter_readable_attributes(
        self,
        requester_dn: str,
        object_type: str,
        target_dn: str,
        attributes: dict,
    ) -> dict:
        """
        Filtre les attributs selon les permissions de lecture.
        
        Retourne uniquement les attributs que l'utilisateur peut voir.
        """
        if await self._is_admin(requester_dn):
            return attributes
        
        readable = {}
        for attr, value in attributes.items():
            if await self.check(requester_dn, Permission.READ, object_type, target_dn, attr):
                readable[attr] = value
        
        return readable
```

### 3.4 Stockage des ACL (LDAP)

```ldif
# Rôle ACL
dn: cn=user-manager,ou=aclroles,dc=example,dc=com
objectClass: gosaRole
cn: user-manager
description: Can manage users in ou=people
gosaAclTemplate: 0:user/*:crwd

# Assignation ACL
dn: cn=user-acl,ou=acl,dc=example,dc=com
objectClass: gosaAcl
cn: user-acl
gosaAclEntry: 0:subtree:uid=manager,ou=people,dc=example,dc=com:cn=user-manager,ou=aclroles,dc=example,dc=com
```

---

## 4. Validation des Entrées

### 4.1 Règles de Validation

| Entrée | Validation | Protection contre |
|--------|------------|-------------------|
| UID | `^[a-z][a-z0-9_-]{0,31}$` | Injection |
| Email | Format RFC 5322 | Spam, injection |
| DN | Parser strict | LDAP injection |
| Filtre LDAP | Échappement | LDAP injection |
| HTML | Sanitization | XSS |

### 4.2 Protection LDAP Injection

```python
# ❌ VULNÉRABLE
filter = f"(uid={user_input})"  # Si user_input = "*)(uid=*))(|(uid=*"

# ✅ CORRECT
from ldap3.utils.conv import escape_filter_chars

safe_input = escape_filter_chars(user_input)
filter = f"(uid={safe_input})"
```

### 4.3 Échappement des Caractères

```python
# heracles_api/core/ldap_utils.py

import re

def escape_dn_component(value: str) -> str:
    """
    Échappe une valeur pour utilisation dans un DN.
    
    Caractères échappés: , + " \\ < > ; = / NUL
    """
    # Caractères à échapper selon RFC 4514
    special = {
        ',': '\\,',
        '+': '\\+',
        '"': '\\"',
        '\\': '\\\\',
        '<': '\\<',
        '>': '\\>',
        ';': '\\;',
        '=': '\\=',
        '/': '\\/',
        '\x00': '\\00',
    }
    
    result = []
    for char in value:
        result.append(special.get(char, char))
    
    # Échapper espaces en début/fin
    if result and result[0] == ' ':
        result[0] = '\\ '
    if result and result[-1] == ' ':
        result[-1] = '\\ '
    
    return ''.join(result)


def validate_dn(dn: str) -> bool:
    """
    Valide le format d'un DN.
    
    Returns:
        bool: True si le DN est valide
    """
    # Pattern simplifié - une vraie implémentation utiliserait un parser
    pattern = r'^([a-zA-Z][a-zA-Z0-9-]*=[^,=]+)(,([a-zA-Z][a-zA-Z0-9-]*=[^,=]+))*$'
    return bool(re.match(pattern, dn))
```

---

## 5. Mots de Passe

### 5.1 Méthodes de Hashing Supportées

| Méthode | Format | Recommandé |
|---------|--------|------------|
| Argon2id | `{ARGON2}$argon2id$...` | ✅ Oui |
| bcrypt | `{BCRYPT}$2b$...` | ✅ Oui |
| SSHA | `{SSHA}base64...` | ⚠️ Legacy |
| SHA | `{SHA}base64...` | ❌ Non |
| MD5 | `{MD5}base64...` | ❌ Non |

### 5.2 Configuration par Défaut

```yaml
# heracles.yaml
security:
  password:
    hash_method: argon2id
    argon2:
      time_cost: 3
      memory_cost: 65536  # 64 MB
      parallelism: 4
    bcrypt:
      rounds: 12
```

### 5.3 Politique de Mots de Passe

```python
# heracles_api/core/password_policy.py

from pydantic import BaseModel
import re


class PasswordPolicy(BaseModel):
    """Politique de mots de passe."""
    
    min_length: int = 12
    max_length: int = 128
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digit: bool = True
    require_special: bool = True
    special_chars: str = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    # Historique (empêche réutilisation)
    history_count: int = 5
    
    # Expiration
    max_age_days: int = 90
    warning_days: int = 14


def validate_password(password: str, policy: PasswordPolicy) -> list[str]:
    """
    Valide un mot de passe contre une politique.
    
    Returns:
        list[str]: Liste des erreurs (vide si valide)
    """
    errors = []
    
    if len(password) < policy.min_length:
        errors.append(f"Password must be at least {policy.min_length} characters")
    
    if len(password) > policy.max_length:
        errors.append(f"Password must be at most {policy.max_length} characters")
    
    if policy.require_uppercase and not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    
    if policy.require_lowercase and not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    
    if policy.require_digit and not re.search(r'\d', password):
        errors.append("Password must contain at least one digit")
    
    if policy.require_special:
        escaped = re.escape(policy.special_chars)
        if not re.search(f'[{escaped}]', password):
            errors.append("Password must contain at least one special character")
    
    return errors
```

---

## 6. Communications

### 6.1 TLS Obligatoire

| Connexion | Exigence |
|-----------|----------|
| Client → API | HTTPS (TLS 1.2+) |
| API → LDAP | LDAPS ou STARTTLS |
| API → PostgreSQL | SSL |
| API → Redis | TLS en production |

### 6.2 Configuration TLS

```yaml
# heracles.yaml
tls:
  # Certificat API
  cert_file: /etc/heracles/cert.pem
  key_file: /etc/heracles/key.pem
  
  # LDAP
  ldap:
    ca_file: /etc/heracles/ldap-ca.pem
    verify: true
    
  # PostgreSQL
  database:
    sslmode: verify-full
    sslrootcert: /etc/heracles/db-ca.pem
```

### 6.3 Headers de Sécurité

```python
# heracles_api/core/middleware.py

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware


def setup_security_headers(app: FastAPI) -> None:
    """Configure les headers de sécurité."""
    
    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS protection
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # HSTS (1 year)
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        
        # CSP
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'"
        )
        
        return response
```

---

## 7. Audit et Logging

### 7.1 Événements à Logger

| Catégorie | Événements | Niveau |
|-----------|------------|--------|
| **Auth** | Login, logout, échec login, token refresh | INFO/WARN |
| **User** | Create, update, delete, password change | INFO |
| **ACL** | Permission denied | WARN |
| **Security** | Injection attempt, brute force | ERROR |
| **System** | Startup, shutdown, error | INFO/ERROR |

### 7.2 Format des Logs

```json
{
  "timestamp": "2026-01-17T10:30:00.000Z",
  "level": "INFO",
  "logger": "heracles.auth",
  "message": "User login successful",
  "context": {
    "user_dn": "uid=jdoe,ou=people,dc=example,dc=com",
    "ip": "192.168.1.100",
    "user_agent": "Mozilla/5.0..."
  },
  "trace_id": "abc123"
}
```

### 7.3 Données Sensibles

**JAMAIS logger:**
- Mots de passe (en clair ou hashés)
- Tokens complets
- Numéros de carte bancaire
- Données personnelles non nécessaires

```python
# ❌ INTERDIT
logger.info(f"Password changed for {uid}: {new_password}")
logger.debug(f"Token: {access_token}")

# ✅ CORRECT
logger.info(f"Password changed for {uid}")
logger.debug(f"Token issued for {uid}, jti={token_jti}")
```

### 7.4 Rétention

| Type | Rétention | Stockage |
|------|-----------|----------|
| Logs application | 30 jours | Fichier/ELK |
| Audit LDAP | 1 an | LDAP/PostgreSQL |
| Audit sécurité | 2 ans | PostgreSQL |

---

## 8. Secrets Management

### 8.1 Variables d'Environnement

```bash
# JAMAIS dans le code ou les fichiers versionnés
export HERACLES_SECRET_KEY="..."
export LDAP_BIND_PASSWORD="..."
export DATABASE_URL="postgresql://user:pass@..."
```

### 8.2 Fichier .env

```bash
# .env (dans .gitignore!)
SECRET_KEY=your-secret-key-32-chars-minimum
LDAP_BIND_PASSWORD=ldap-admin-password
DATABASE_URL=postgresql://heracles:pass@localhost/heracles
```

### 8.3 Vault (Production)

```yaml
# heracles.yaml (production)
secrets:
  provider: vault
  vault:
    address: https://vault.example.com
    auth_method: kubernetes
    secret_path: secret/data/heracles
```

---

## 9. Checklist Sécurité

### 9.1 Avant Chaque Release

- [ ] Pas de secrets dans le code (`git-secrets scan`)
- [ ] Dépendances à jour sans vulnérabilités connues
- [ ] Tests de sécurité passants
- [ ] Revue de code effectuée
- [ ] OWASP Top 10 vérifié

### 9.2 Audit Régulier

- [ ] Scan de vulnérabilités mensuel
- [ ] Revue des ACL trimestrielle
- [ ] Test de pénétration annuel
- [ ] Revue des logs d'audit mensuelle
