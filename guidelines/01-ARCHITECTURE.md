# HERACLES - Architecture Technique

> **Référence**: Ce document détaille l'architecture technique d'Heracles.
> **Prérequis**: Lire `00-PROJECT-CHARTER.md` avant ce document.

---

## 1. Vue d'Ensemble des Composants

```
heracles/
├── heracles-core/          # Bibliothèque Rust (LDAP, crypto)
├── heracles-api/           # Backend Python/FastAPI
│   ├── heracles_api/       # Package principal (core/, api/, services/, models/, plugins/, middleware/)
│   └── alembic/            # Migrations base de données
├── heracles-ui/            # Frontend React 19 (Vite + Bun)
├── heracles_plugins/       # Plugins Python (7 plugins opérationnels)
├── deploy/docker/              # Configurations Docker (LDAP schemas, Dockerfiles)
├── guidelines/             # Documentation et spécifications (ce dossier)
├── scripts/                # Scripts de déploiement et bootstrap
├── mk/                     # Modules Makefile (docker.mk, demo.mk, help.mk)
└── demo/                   # Environnement de démonstration Vagrant
```

---

## 2. heracles-core (Rust)

### 2.1 Responsabilités

Le module Rust est responsable des opérations **critiques en performance et sécurité**:

| Responsabilité | Justification |
|----------------|---------------|
| Connexions LDAP | Pool de connexions, reconnexion auto |
| Opérations LDAP | Search, add, modify, delete, bind |
| Hashing mots de passe | Argon2, bcrypt, SHA, SSHA, MD5, SMD5 |
| Validation schéma | Parsing et validation des schémas LDAP |
| Génération UID/GID | Allocation atomique des identifiants |

### 2.2 Structure des Modules

```
heracles-core/
├── Cargo.toml
├── src/
│   ├── lib.rs              # Point d'entrée, exports PyO3
│   ├── ldap/
│   │   ├── mod.rs
│   │   ├── connection.rs   # Pool de connexions
│   │   ├── operations.rs   # CRUD LDAP
│   │   ├── search.rs       # Recherche avec filtres
│   │   ├── schema.rs       # Parsing schéma LDAP
│   │   └── dn.rs           # Manipulation des DNs
│   ├── crypto/
│   │   ├── mod.rs
│   │   ├── password.rs     # Hashing/vérification
│   │   ├── hash_methods.rs # Implémentation des méthodes
│   │   └── random.rs       # Génération aléatoire
│   ├── schema/
│   │   ├── mod.rs
│   │   ├── parser.rs       # Parser de schéma LDAP
│   │   ├── validator.rs    # Validation des entrées
│   │   └── types.rs        # Types de données LDAP
│   └── errors.rs           # Types d'erreurs
└── tests/
    ├── ldap_tests.rs
    └── crypto_tests.rs
```

### 2.3 Interface PyO3 (Bindings Python)

```rust
// Fonctions exposées à Python - EXHAUSTIF
#[pymodule]
fn heracles_core(_py: Python, m: &PyModule) -> PyResult<()> {
    // LDAP
    m.add_class::<LdapConnection>()?;
    m.add_function(wrap_pyfunction!(ldap_search, m)?)?;
    m.add_function(wrap_pyfunction!(ldap_add, m)?)?;
    m.add_function(wrap_pyfunction!(ldap_modify, m)?)?;
    m.add_function(wrap_pyfunction!(ldap_delete, m)?)?;
    m.add_function(wrap_pyfunction!(ldap_bind, m)?)?;
    
    // Crypto
    m.add_function(wrap_pyfunction!(hash_password, m)?)?;
    m.add_function(wrap_pyfunction!(verify_password, m)?)?;
    m.add_function(wrap_pyfunction!(generate_random_password, m)?)?;
    
    // Schema
    m.add_function(wrap_pyfunction!(parse_schema, m)?)?;
    m.add_function(wrap_pyfunction!(validate_entry, m)?)?;
    
    Ok(())
}
```

### 2.4 Règles de Développement Rust

1. **Pas de `unwrap()` en production** - Utiliser `?` ou gestion explicite
2. **Tous les types publics documentés** avec `///`
3. **Tests pour chaque fonction publique**
4. **Pas de dépendances avec vulnérabilités connues** (`cargo audit`)
5. **Format**: `cargo fmt` obligatoire
6. **Lint**: `cargo clippy` sans warnings

---

## 3. heracles-api (Python/FastAPI)

### 3.1 Responsabilités

| Responsabilité | Description |
|----------------|-------------|
| API REST | Endpoints versionnés (/api/v1/) |
| Authentification | JWT, sessions, login |
| Autorisation | Vérification ACL |
| Validation | Pydantic models |
| Orchestration | Coordination des services |
| Plugins | Chargement et exécution |

### 3.2 Structure des Modules

```
heracles-api/
├── pyproject.toml          # Dependencies Python (uv)
├── alembic/                # Migrations DB
│   ├── alembic.ini
│   └── versions/
│       └── 0001_create_config_tables.py
├── heracles_api/
│   ├── __init__.py
│   ├── main.py             # Point d'entrée FastAPI
│   ├── config.py           # Settings (Pydantic BaseSettings)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py       # Configuration avancée
│   │   ├── database.py     # SQLAlchemy setup
│   │   ├── dependencies.py # Injections de dépendances
│   │   ├── ldap_config.py  # Configuration LDAP
│   │   ├── logging.py      # Structured logging
│   │   └── password_policy.py # Validation mots de passe
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── endpoints/
│   │           ├── auth.py         # /auth/*
│   │           ├── users.py        # /users/*
│   │           ├── groups.py       # /groups/*
│   │           ├── departments.py  # /departments/*
│   │           ├── config.py       # /config/*
│   │           └── plugins.py      # /plugins/*
│   ├── models/
│   │   ├── db/             # SQLAlchemy ORM models
│   │   │   ├── auth.py
│   │   │   ├── config.py
│   │   │   ├── departments.py
│   │   │   ├── groups.py
│   │   │   ├── users.py
│   │   │   └── plugins.py
│   │   └── schemas/        # Pydantic validation schemas
│   │       ├── auth.py
│   │       ├── user.py
│   │       └── group.py
│   ├── services/
│   │   ├── ldap_service.py         # LDAP operations wrapper (via heracles-core)
│   │   ├── ldap_migration_service.py
│   │   ├── auth_service.py         # Authentication logic
│   │   └── acl_service.py          # Authorization (planned)
│   ├── repositories/               # Data access layer
│   │   ├── user_repository.py
│   │   ├── group_repository.py
│   │   └── department_repository.py
│   ├── plugins/
│   │   ├── __init__.py
│   │   ├── base.py         # PluginInfo, TabDefinition base classes
│   │   ├── loader.py       # Dynamic plugin loading
│   │   └── registry.py     # Plugin registry
│   ├── middleware/
│   │   ├── plugin_access.py # Plugin access control
│   │   └── rate_limit.py    # Rate limiting (Redis-backed)
│   └── schemas/            # API response schemas
└── tests/
    ├── conftest.py
    └── test_*.py
```

### 3.3 Règles de Développement Python

1. **Type hints obligatoires** sur toutes les fonctions
2. **Docstrings Google style** sur les fonctions publiques
3. **Pydantic pour toute validation** d'entrée
4. **Pas de logique métier dans les routes** (déléguer aux services)
5. **Async par défaut** pour les I/O
6. **Format**: `black` + `isort`
7. **Lint**: `ruff` sans erreurs
8. **Tests**: `pytest` avec fixtures

### 3.4 Exemple de Route Conforme

```python
# heracles_api/api/v1/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from heracles_api.models.schemas.user import UserCreate, UserRead, UserUpdate
from heracles_api.services.user_service import UserService
from heracles_api.api.deps import get_current_user, get_user_service
from heracles_api.core.exceptions import UserNotFoundError, LDAPError

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{uid}", response_model=UserRead)
async def get_user(
    uid: str,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> UserRead:
    """
    Récupère un utilisateur par son UID.
    
    Args:
        uid: Identifiant unique de l'utilisateur
        
    Returns:
        UserRead: Données de l'utilisateur
        
    Raises:
        HTTPException 404: Utilisateur non trouvé
        HTTPException 403: Accès refusé
    """
    # ACL check est fait dans le service
    try:
        return await user_service.get_by_uid(uid, requester=current_user)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {uid} not found"
        )
```

---

## 4. heracles-ui (React)

### 4.1 Responsabilités

| Responsabilité | Description |
|----------------|-------------|
| Interface utilisateur | Rendu des pages et composants |
| State management | Gestion de l'état client |
| API calls | Communication avec heracles-api |
| Formulaires | Génération dynamique depuis schémas |
| ACL-aware rendering | Masquage selon permissions |

### 4.2 Structure des Modules

```
heracles-ui/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── index.html
├── public/
│   └── assets/
├── src/
│   ├── main.tsx            # Point d'entrée
│   ├── App.tsx             # Router principal
│   ├── components/
│   │   ├── auth/            # Auth (ProtectedRoute)
│   │   ├── common/          # UI partagés (data-table, dialogs, forms, tree-viewer)
│   │   ├── groups/          # Widgets groupes LDAP
│   │   ├── departments/     # Department components
│   │   ├── layout/          # Layout app (header/sidebar)
│   │   ├── settings/        # Settings components
│   │   ├── plugins/         # UI plugins (posix/ssh/sudo/systems/dns/dhcp/mail)
│   │   ├── ui/              # Composants de base (shadcn/radix)
│   │   └── users/           # Widgets utilisateurs
│   ├── config/
│   │   ├── constants.ts     # Constantes UI
│   │   └── routes.ts        # Routes applicatives
│   ├── hooks/               # Hooks React Query et UI
│   ├── lib/
│   │   ├── api/             # Clients API par domaine
│   │   ├── api-client.ts    # Client HTTP partagé
│   │   ├── errors.ts        # Gestion d'erreurs
│   │   ├── schemas.ts       # Zod schemas
│   │   ├── string-helpers.ts
│   │   └── utils.ts
│   ├── pages/               # Pages routées
│   │   ├── users/           # list/create/detail
│   │   ├── groups/          # list/create/detail
│   │   ├── posix/           # groupes/mixed
│   │   ├── sudo/            # roles
│   │   ├── systems/         # list/detail
│   │   ├── dns/             # zones/records
│   │   ├── dhcp/            # services/subnets/hosts
│   │   ├── dashboard.tsx
│   │   ├── login.tsx
│   │   └── settings.tsx
│   ├── router.tsx           # Routes React Router
│   ├── stores/              # Zustand stores
│   └── types/               # Types API/Plugins
```

### 4.3 Règles de Développement React

1. **TypeScript strict** - `strict: true` dans tsconfig
2. **Functional components only** - Pas de class components
3. **Hooks pour la logique** - Extraire dans custom hooks
4. **React Query pour les données serveur** - Pas de state local pour API
5. **Zustand pour le state global** - UI state uniquement
6. **Zod pour la validation** - Schémas partagés avec forms
7. **Pas de `any`** - Typer explicitement
8. **Format**: `prettier`
9. **Lint**: `eslint` avec config strict

### 4.4 Exemple de Composant Conforme

```typescript
// src/pages/users/list.tsx
import { useQuery } from '@tanstack/react-query';
import { DataTable } from '@/components/shared/DataTable';
import { Button } from '@/components/ui/button';
import { usersApi } from '@/api/users';
import { usePermissions } from '@/hooks/usePermissions';
import type { User } from '@/types';

const columns = [
  { key: 'uid', label: 'UID' },
  { key: 'cn', label: 'Nom complet' },
  { key: 'mail', label: 'Email' },
] as const;

export function UserListPage(): JSX.Element {
  const { canCreate } = usePermissions('user');
  
  const { data: users, isLoading, error } = useQuery({
    queryKey: ['users'],
    queryFn: () => usersApi.list(),
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Utilisateurs</h1>
        {canCreate && (
          <Button asChild>
            <Link to="/users/new">Créer</Link>
          </Button>
        )}
      </div>
      <DataTable<User> data={users ?? []} columns={columns} />
    </div>
  );
}
```

---

## 5. Communication Inter-Composants

### 5.1 Diagramme de Séquence - Création Utilisateur

```
┌────────┐     ┌─────────────┐     ┌─────────────┐     ┌──────────────┐     ┌──────┐
│   UI   │     │ API Gateway │     │ UserService │     │ heracles-core│     │ LDAP │
└───┬────┘     └──────┬──────┘     └──────┬──────┘     └──────┬───────┘     └──┬───┘
    │                 │                   │                   │                │
    │ POST /users     │                   │                   │                │
    │ {uid, cn, ...}  │                   │                   │                │
    │────────────────>│                   │                   │                │
    │                 │                   │                   │                │
    │                 │ Validate JWT      │                   │                │
    │                 │ Check ACL         │                   │                │
    │                 │ Validate Schema   │                   │                │
    │                 │                   │                   │                │
    │                 │ create_user()     │                   │                │
    │                 │──────────────────>│                   │                │
    │                 │                   │                   │                │
    │                 │                   │ hash_password()   │                │
    │                 │                   │──────────────────>│                │
    │                 │                   │<──────────────────│                │
    │                 │                   │                   │                │
    │                 │                   │ allocate_uid()    │                │
    │                 │                   │──────────────────>│                │
    │                 │                   │<──────────────────│                │
    │                 │                   │                   │                │
    │                 │                   │ ldap_add()        │                │
    │                 │                   │──────────────────>│                │
    │                 │                   │                   │ ADD entry     │
    │                 │                   │                   │──────────────>│
    │                 │                   │                   │<──────────────│
    │                 │                   │<──────────────────│                │
    │                 │                   │                   │                │
    │                 │ UserRead          │                   │                │
    │                 │<──────────────────│                   │                │
    │                 │                   │                   │                │
    │ 201 Created     │                   │                   │                │
    │ {user data}     │                   │                   │                │
    │<────────────────│                   │                   │                │
    │                 │                   │                   │                │
```

### 5.2 Contrats d'Interface

#### Service → heracles-core

```python
# Contrat pour LdapService
from typing import Protocol, Optional
from heracles_core import LdapEntry, LdapFilter

class ILdapOperations(Protocol):
    def search(
        self,
        base_dn: str,
        filter: LdapFilter,
        attributes: list[str],
        scope: str = "subtree"
    ) -> list[LdapEntry]: ...
    
    def add(self, dn: str, attributes: dict[str, list[str]]) -> None: ...
    
    def modify(
        self, 
        dn: str, 
        changes: list[tuple[str, str, list[str]]]
    ) -> None: ...
    
    def delete(self, dn: str) -> None: ...
```

#### API → Service

```python
# Contrat pour UserService
from typing import Protocol
from heracles_api.models.schemas.user import UserCreate, UserRead, UserUpdate

class IUserService(Protocol):
    async def list(
        self,
        requester: dict,
        filter: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[UserRead]: ...
    
    async def get_by_uid(self, uid: str, requester: dict) -> UserRead: ...
    
    async def create(self, data: UserCreate, requester: dict) -> UserRead: ...
    
    async def update(
        self, 
        uid: str, 
        data: UserUpdate, 
        requester: dict
    ) -> UserRead: ...
    
    async def delete(self, uid: str, requester: dict) -> None: ...
```

---

## 6. Configuration

### 6.1 Variables d'Environnement

```bash
# heracles-api/.env.example

# === LDAP ===
LDAP_URI=ldap://localhost:389
LDAP_BASE_DN=dc=example,dc=com
LDAP_BIND_DN=cn=admin,dc=example,dc=com
LDAP_BIND_PASSWORD=secret
LDAP_USE_TLS=false

# === PostgreSQL ===
DATABASE_URL=postgresql://heracles:secret@localhost:5432/heracles

# === Redis ===
REDIS_URL=redis://localhost:6379/0

# === Security ===
SECRET_KEY=your-secret-key-min-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# === App ===
DEBUG=false
LOG_LEVEL=INFO
CORS_ORIGINS=["http://localhost:3000"]
```

### 6.2 Fichier de Configuration Principal

Un convertisseur de configuration legacy sera fourni pour les migrations.

```yaml
# heracles.yaml (format natif Heracles)
ldap:
  uri: ldap://localhost:389
  base_dn: dc=example,dc=com
  admin_dn: cn=admin,dc=example,dc=com
  # password from env var LDAP_BIND_PASSWORD

database:
  url: postgresql://localhost/heracles
  pool_size: 10

redis:
  url: redis://localhost:6379/0

security:
  secret_key: ${SECRET_KEY}
  token_expire_minutes: 30

plugins:
  enabled:
    - posix
    - sudo
    - ssh
    - systems
    - dns
    - dhcp
    - mail
```
