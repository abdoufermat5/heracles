# HERACLES - Modèle de Données

> **Référence**: Ce document définit les schémas LDAP et PostgreSQL utilisés par Heracles.
> **Règle critique**: Les schémas LDAP doivent être 100% compatibles avec les standards LDAP.

---

## 1. Compatibilité LDAP

### 1.1 Schémas LDAP Requis

Heracles nécessite les schémas LDAP suivants:

| Schéma | Source | Description |
|--------|--------|-------------|
| core.schema | OpenLDAP | Schéma de base |
| cosine.schema | OpenLDAP | X.500 classes |
| inetorgperson.schema | OpenLDAP | Utilisateurs |
| nis.schema | OpenLDAP | POSIX (posixAccount, posixGroup) |
| sudo.schema | sudoers | Règles sudo |
| openssh-lpk.schema | OpenSSH | Clés SSH LDAP |

### 1.2 Règle de Compatibilité

```
INTERDIT: Créer de nouveaux objectClass ou attributeType propriétaires à Heracles.
AUTORISÉ: Utiliser uniquement les schémas LDAP standards existants.
EXCEPTION: Schémas auxiliaires documentés (ex: posixGroupAux).
```

---

## 2. Structure LDAP

### 2.1 Arbre LDAP Standard

```
dc=example,dc=com                    # Base DN
├── ou=aclroles                      # Rôles ACL
├── ou=configs                       # Configuration
├── ou=groups                        # Groupes
├── ou=people                        # Utilisateurs
├── ou=sudoers                       # Règles sudo
├── ou=systems                       # Serveurs, workstations
│   ├── ou=servers
│   ├── ou=workstations
│   └── ou=terminals
└── ou=tokens                        # Recovery tokens
```

### 2.2 Compatibilité des OUs

Heracles DOIT supporter la configuration des OUs:

```
hrcUserRDN: ou=people
hrcGroupRDN: ou=groups
hrcSudoRDN: ou=sudoers
```

---

## 3. Schémas des Objets

### 3.1 Utilisateur (User)

#### ObjectClasses

| ObjectClass | Type | Utilisation |
|-------------|------|-------------|
| inetOrgPerson | STRUCTURAL | Base utilisateur |
| posixAccount | AUXILIARY | Compte Unix |
| shadowAccount | AUXILIARY | Expiration mot de passe |
| ldapPublicKey | AUXILIARY | Clés SSH |

#### Attributs

| Attribut | Type | Required | Description | Exemple |
|----------|------|----------|-------------|---------|
| uid | string | ✅ | Identifiant unique | jdoe |
| cn | string | ✅ | Nom complet | John Doe |
| sn | string | ✅ | Nom de famille | Doe |
| givenName | string | ❌ | Prénom | John |
| mail | string | ❌ | Email | jdoe@example.com |
| userPassword | binary | ❌ | Mot de passe hashé | {SSHA}xxx |
| telephoneNumber | string | ❌ | Téléphone | +33 1 23 45 67 89 |
| jpegPhoto | binary | ❌ | Photo (JPEG) | - |
| uidNumber | integer | ✅* | UID Unix | 10001 |
| gidNumber | integer | ✅* | GID primaire | 10001 |
| homeDirectory | string | ✅* | Répertoire home | /home/jdoe |
| loginShell | string | ❌ | Shell | /bin/bash |
| gecos | string | ❌ | Info GECOS | John Doe |
| shadowLastChange | integer | ❌ | Dernier changement pwd | 19739 |
| shadowMin | integer | ❌ | Jours min entre changements | 0 |
| shadowMax | integer | ❌ | Jours max validité | 99999 |
| shadowWarning | integer | ❌ | Jours avertissement | 7 |
| shadowInactive | integer | ❌ | Jours inactif après expiration | -1 |
| shadowExpire | integer | ❌ | Date expiration compte | -1 |
| sshPublicKey | string[] | ❌ | Clés SSH publiques | ssh-ed25519 AAA... |

*Requis si posixAccount activé

#### DN Pattern

```
uid={uid},ou=people,{base_dn}
```

#### Exemple LDIF

```ldif
dn: uid=jdoe,ou=people,dc=example,dc=com
objectClass: inetOrgPerson
objectClass: posixAccount
objectClass: shadowAccount
objectClass: ldapPublicKey
uid: jdoe
cn: John Doe
sn: Doe
givenName: John
mail: jdoe@example.com
userPassword: {SSHA}xxxxxxxxxxxxxxxxxxxxx
uidNumber: 10001
gidNumber: 10001
homeDirectory: /home/jdoe
loginShell: /bin/bash
shadowLastChange: 19739
shadowMax: 99999
sshPublicKey: ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIxxxx jdoe@laptop
```

---

### 3.2 Groupe (Group)

#### ObjectClasses

| ObjectClass | Type | Utilisation |
|-------------|------|-------------|
| groupOfNames | STRUCTURAL | Groupe LDAP standard |
| posixGroup | AUXILIARY | Groupe Unix |

#### Attributs

| Attribut | Type | Required | Description | Exemple |
|----------|------|----------|-------------|---------|
| cn | string | ✅ | Nom du groupe | developers |
| description | string | ❌ | Description | Development team |
| member | dn[] | ✅ | DNs des membres | uid=jdoe,ou=people,... |
| gidNumber | integer | ✅* | GID Unix | 20001 |
| memberUid | string[] | ❌ | UIDs des membres (POSIX) | jdoe |

*Requis si posixGroup activé

#### DN Pattern

```
cn={cn},ou=groups,{base_dn}
```

#### Exemple LDIF

```ldif
dn: cn=developers,ou=groups,dc=example,dc=com
objectClass: groupOfNames
objectClass: posixGroup
cn: developers
description: Development team
gidNumber: 20001
member: uid=jdoe,ou=people,dc=example,dc=com
member: uid=asmith,ou=people,dc=example,dc=com
memberUid: jdoe
memberUid: asmith
```

---

### 3.3 Règle Sudo

#### ObjectClass

| ObjectClass | Type | Source |
|-------------|------|--------|
| sudoRole | STRUCTURAL | sudo.schema |

#### Attributs

| Attribut | Type | Required | Description | Exemple |
|----------|------|----------|-------------|---------|
| cn | string | ✅ | Nom de la règle | developers-sudo |
| sudoUser | string[] | ✅ | Utilisateurs/groupes | %developers, jdoe |
| sudoHost | string[] | ✅ | Hôtes autorisés | ALL, srv-* |
| sudoCommand | string[] | ✅ | Commandes | /usr/bin/docker |
| sudoOption | string[] | ❌ | Options | !authenticate |
| sudoRunAs | string[] | ❌ | Run as user | root |
| sudoRunAsUser | string[] | ❌ | Run as user (nouveau) | root |
| sudoRunAsGroup | string[] | ❌ | Run as group | - |
| sudoNotBefore | string | ❌ | Date début validité | 20260101000000Z |
| sudoNotAfter | string | ❌ | Date fin validité | 20261231235959Z |
| sudoOrder | integer | ❌ | Ordre d'évaluation | 10 |

#### DN Pattern

```
cn={cn},ou=sudoers,{base_dn}
```

#### Exemple LDIF

```ldif
dn: cn=developers-sudo,ou=sudoers,dc=example,dc=com
objectClass: sudoRole
cn: developers-sudo
sudoUser: %developers
sudoHost: ALL
sudoCommand: /usr/bin/docker
sudoCommand: /usr/bin/systemctl restart nginx
sudoOption: !authenticate
sudoRunAsUser: root
sudoOrder: 10
```

---

### 3.4 Système (Server/Workstation)

#### ObjectClasses (Systèmes)

| ObjectClass | Type | Utilisation |
|-------------|------|-------------|
| hrcServer | STRUCTURAL | Serveur |
| hrcWorkstation | STRUCTURAL | Station de travail |
| hrcTerminal | STRUCTURAL | Terminal |
| ieee802Device | AUXILIARY | Adresse MAC |
| ipHost | AUXILIARY | Adresse IP |

#### Attributs

| Attribut | Type | Required | Description | Exemple |
|----------|------|----------|-------------|---------|
| cn | string | ✅ | Nom du système | srv-web-01 |
| description | string | ❌ | Description | Web server |
| ipHostNumber | string[] | ❌ | Adresses IP | 192.168.1.10 |
| macAddress | string[] | ❌ | Adresses MAC | 00:11:22:33:44:55 |
| hrcMode | string | ❌ | Mode de démarrage | - |

#### DN Pattern

```
cn={cn},ou=servers,ou=systems,{base_dn}
cn={cn},ou=workstations,ou=systems,{base_dn}
```

---

### 3.5 Rôle ACL

#### ObjectClass

| ObjectClass | Source |
|-------------|--------|
| gosaRole | core-hrc.schema |

#### Attributs

| Attribut | Type | Required | Description |
|----------|------|----------|-------------|
| cn | string | ✅ | Nom du rôle |
| description | string | ❌ | Description |
| gosaAclTemplate | string[] | ✅ | Templates d'ACL |

#### Format gosaAclTemplate

```
{priority}:{category}:{permissions}:{options}

Exemple: 0:user/posixAccount:rwcd
- 0 = priorité
- user/posixAccount = catégorie/tab
- rwcd = read, write, create, delete
```

---

## 4. Schéma PostgreSQL

### 4.1 Tables

#### heracles_config

Stocke la configuration de l'application (non stockée en LDAP).

```sql
CREATE TABLE heracles_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### heracles_sessions

Sessions utilisateur (si Redis non disponible).

```sql
CREATE TABLE heracles_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_dn VARCHAR(512) NOT NULL,
    token_hash VARCHAR(64) NOT NULL,
    refresh_token_hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX idx_sessions_user_dn ON heracles_sessions(user_dn);
CREATE INDEX idx_sessions_expires ON heracles_sessions(expires_at);
```

#### heracles_audit_logs

Logs d'audit (backup des logs LDAP ou unique source).

```sql
CREATE TABLE heracles_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action VARCHAR(50) NOT NULL, -- create, modify, delete, login, logout
    actor_dn VARCHAR(512) NOT NULL,
    target_dn VARCHAR(512),
    target_type VARCHAR(100), -- user, group, system
    changes JSONB, -- {attribute: {old: x, new: y}}
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

CREATE INDEX idx_audit_timestamp ON heracles_audit_logs(timestamp);
CREATE INDEX idx_audit_actor ON heracles_audit_logs(actor_dn);
CREATE INDEX idx_audit_target ON heracles_audit_logs(target_dn);
CREATE INDEX idx_audit_action ON heracles_audit_logs(action);
```

#### heracles_jobs

File d'attente pour tâches asynchrones.

```sql
CREATE TABLE heracles_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(100) NOT NULL, -- sync_groups, send_notification
    status VARCHAR(20) DEFAULT 'pending', -- pending, running, completed, failed
    payload JSONB NOT NULL,
    result JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    error_message TEXT
);

CREATE INDEX idx_jobs_status ON heracles_jobs(status);
CREATE INDEX idx_jobs_type ON heracles_jobs(type);
```

#### heracles_uid_allocations

Tracking des allocations UID/GID pour éviter les doublons.

```sql
CREATE TABLE heracles_uid_allocations (
    id SERIAL PRIMARY KEY,
    type VARCHAR(10) NOT NULL, -- uid, gid
    next_value INT NOT NULL,
    min_value INT NOT NULL,
    max_value INT NOT NULL,
    UNIQUE(type)
);

-- Valeurs initiales
INSERT INTO heracles_uid_allocations (type, next_value, min_value, max_value) VALUES
    ('uid', 10000, 10000, 60000),
    ('gid', 10000, 10000, 60000);
```

---

## 5. Mapping Heracles ↔ LDAP

### 5.1 Modèles Pydantic

```python
# app/models/schemas/user.py

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List

class PosixAccount(BaseModel):
    """Attributs POSIX d'un compte."""
    uid_number: Optional[int] = Field(None, ge=1000, le=65534, alias="uidNumber")
    gid_number: int = Field(..., ge=1000, le=65534, alias="gidNumber")
    home_directory: str = Field(..., pattern=r"^/[\w/.-]+$", alias="homeDirectory")
    login_shell: str = Field("/bin/bash", alias="loginShell")
    gecos: Optional[str] = None

class UserBase(BaseModel):
    """Attributs communs utilisateur."""
    uid: str = Field(..., min_length=1, max_length=32, pattern=r"^[a-z][a-z0-9_-]*$")
    cn: str = Field(..., min_length=1, max_length=255)
    sn: str = Field(..., min_length=1, max_length=255)
    given_name: Optional[str] = Field(None, alias="givenName")
    mail: Optional[EmailStr] = None
    telephone_number: Optional[str] = Field(None, alias="telephoneNumber")

class UserCreate(UserBase):
    """Schéma création utilisateur."""
    user_password: Optional[str] = Field(None, min_length=8, alias="userPassword")
    posix: Optional[PosixAccount] = None

class UserRead(UserBase):
    """Schéma lecture utilisateur."""
    dn: str
    object_class: List[str] = Field(alias="objectClass")
    posix: Optional[PosixAccount] = None
    ssh_public_key: Optional[List[str]] = Field(None, alias="sshPublicKey")
    
    class Config:
        populate_by_name = True

class UserUpdate(BaseModel):
    """Schéma mise à jour (tous champs optionnels)."""
    cn: Optional[str] = None
    sn: Optional[str] = None
    given_name: Optional[str] = Field(None, alias="givenName")
    mail: Optional[EmailStr] = None
    telephone_number: Optional[str] = Field(None, alias="telephoneNumber")
```

### 5.2 Conversion LDAP ↔ Pydantic

```python
# app/services/ldap_mapper.py

from typing import Dict, Any, List
from app.models.schemas.user import UserRead, PosixAccount

def ldap_entry_to_user(entry: Dict[str, Any]) -> UserRead:
    """
    Convertit une entrée LDAP en modèle UserRead.
    
    Args:
        entry: Dict avec 'dn' et attributs LDAP
        
    Returns:
        UserRead: Modèle Pydantic
    """
    attrs = entry.get("attributes", entry)
    
    # Extraction des attributs (gestion valeur simple vs liste)
    def get_attr(name: str, default=None):
        val = attrs.get(name, default)
        if isinstance(val, list):
            return val[0] if len(val) == 1 else val
        return val
    
    # Construction POSIX si présent
    posix = None
    if "posixAccount" in attrs.get("objectClass", []):
        posix = PosixAccount(
            uidNumber=int(get_attr("uidNumber")),
            gidNumber=int(get_attr("gidNumber")),
            homeDirectory=get_attr("homeDirectory"),
            loginShell=get_attr("loginShell", "/bin/bash"),
            gecos=get_attr("gecos"),
        )
    
    return UserRead(
        dn=entry["dn"],
        uid=get_attr("uid"),
        cn=get_attr("cn"),
        sn=get_attr("sn"),
        givenName=get_attr("givenName"),
        mail=get_attr("mail"),
        telephoneNumber=get_attr("telephoneNumber"),
        objectClass=attrs.get("objectClass", []),
        posix=posix,
        sshPublicKey=attrs.get("sshPublicKey"),
    )


def user_to_ldap_entry(user: UserCreate, base_dn: str) -> Dict[str, Any]:
    """
    Convertit un UserCreate en entrée LDAP.
    
    Args:
        user: Modèle de création
        base_dn: DN de base
        
    Returns:
        Dict avec 'dn' et 'attributes'
    """
    dn = f"uid={user.uid},ou=people,{base_dn}"
    
    object_class = ["inetOrgPerson"]
    attrs = {
        "uid": [user.uid],
        "cn": [user.cn],
        "sn": [user.sn],
    }
    
    if user.given_name:
        attrs["givenName"] = [user.given_name]
    if user.mail:
        attrs["mail"] = [user.mail]
    if user.telephone_number:
        attrs["telephoneNumber"] = [user.telephone_number]
    
    if user.posix:
        object_class.extend(["posixAccount", "shadowAccount"])
        attrs.update({
            "uidNumber": [str(user.posix.uid_number)],
            "gidNumber": [str(user.posix.gid_number)],
            "homeDirectory": [user.posix.home_directory],
            "loginShell": [user.posix.login_shell],
        })
        if user.posix.gecos:
            attrs["gecos"] = [user.posix.gecos]
    
    attrs["objectClass"] = object_class
    
    return {"dn": dn, "attributes": attrs}
```

---

## 6. Validation des Données

### 6.1 Règles de Validation

| Attribut | Règle | Erreur |
|----------|-------|--------|
| uid | `^[a-z][a-z0-9_-]{0,31}$` | "UID must start with lowercase letter" |
| cn | Non vide, max 255 chars | "CN is required" |
| mail | Format email valide | "Invalid email format" |
| uidNumber | 1000-65534, unique | "UID number already in use" |
| gidNumber | 1000-65534, doit exister | "GID does not exist" |
| homeDirectory | Chemin absolu valide | "Invalid home directory path" |
| sshPublicKey | Format clé SSH valide | "Invalid SSH public key format" |

### 6.2 Unicité

| Attribut | Scope | Vérification |
|----------|-------|--------------|
| uid | Global | LDAP search exact |
| uidNumber | Global | LDAP search + PostgreSQL |
| gidNumber | Global | LDAP search + PostgreSQL |
| mail | Global (optionnel) | Configurable |
