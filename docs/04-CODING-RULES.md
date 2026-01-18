# HERACLES - Règles de Développement

> **Référence**: Ce document définit les standards et règles obligatoires pour tout code Heracles.
> **Application**: Ces règles s'appliquent à TOUS les contributeurs (humains et IA).

---

## 1. Règles Générales

### 1.1 Principes SOLID

Tout code doit respecter les principes SOLID:

| Principe | Application |
|----------|-------------|
| **S**ingle Responsibility | Une classe/fonction = une responsabilité |
| **O**pen/Closed | Ouvert à l'extension, fermé à la modification |
| **L**iskov Substitution | Les sous-types doivent être substituables |
| **I**nterface Segregation | Interfaces spécifiques plutôt que générales |
| **D**ependency Inversion | Dépendre des abstractions, pas des concrétions |

### 1.2 DRY (Don't Repeat Yourself)

- ❌ Pas de copier-coller de code
- ✅ Factoriser en fonctions/classes réutilisables
- ✅ Utiliser l'héritage ou la composition appropriée

### 1.3 KISS (Keep It Simple, Stupid)

- ❌ Pas de sur-ingénierie
- ❌ Pas de patterns complexes sans justification
- ✅ La solution la plus simple qui fonctionne

### 1.4 Langue

- **Code**: Anglais (variables, fonctions, classes, commentaires)
- **Documentation utilisateur**: Français
- **Commits**: Anglais
- **Documentation technique**: Anglais

---

## 2. Règles Rust (heracles-core)

### 2.1 Formatage

```bash
# OBLIGATOIRE avant chaque commit
cargo fmt --all
cargo clippy -- -D warnings
```

### 2.2 Gestion des Erreurs

```rust
// ❌ INTERDIT
fn do_something() -> String {
    some_result.unwrap()  // Panic possible!
}

// ✅ CORRECT
fn do_something() -> Result<String, HeraclesError> {
    let value = some_result?;
    Ok(value)
}
```

### 2.3 Types d'Erreurs

```rust
// Utiliser thiserror pour les erreurs custom
use thiserror::Error;

#[derive(Error, Debug)]
pub enum HeraclesError {
    #[error("LDAP connection failed: {0}")]
    LdapConnection(String),
    
    #[error("LDAP operation failed: {0}")]
    LdapOperation(String),
    
    #[error("Invalid DN format: {0}")]
    InvalidDN(String),
    
    #[error("Password hashing failed: {0}")]
    PasswordHash(String),
    
    #[error("Schema validation failed: {0}")]
    SchemaValidation(String),
}
```

### 2.4 Documentation

```rust
/// Hashes a password using the specified method.
///
/// # Arguments
///
/// * `password` - The plaintext password to hash
/// * `method` - The hashing method (ssha, argon2, bcrypt)
///
/// # Returns
///
/// The hashed password in LDAP format (e.g., `{SSHA}xxxxx`)
///
/// # Errors
///
/// Returns `HeraclesError::PasswordHash` if hashing fails
///
/// # Example
///
/// ```
/// let hash = hash_password("secret123", "ssha")?;
/// assert!(hash.starts_with("{SSHA}"));
/// ```
pub fn hash_password(password: &str, method: &str) -> Result<String, HeraclesError> {
    // ...
}
```

### 2.5 Tests

```rust
#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_hash_password_ssha() {
        let result = hash_password("secret123", "ssha");
        assert!(result.is_ok());
        let hash = result.unwrap();
        assert!(hash.starts_with("{SSHA}"));
    }
    
    #[test]
    fn test_hash_password_invalid_method() {
        let result = hash_password("secret123", "invalid");
        assert!(result.is_err());
    }
}
```

### 2.6 Structure des Modules

```rust
// mod.rs - Export public uniquement ce qui est nécessaire
pub mod connection;
pub mod operations;

// Re-exports pour faciliter l'usage
pub use connection::LdapConnection;
pub use operations::{ldap_search, ldap_add, ldap_modify, ldap_delete};
```

---

## 3. Règles Python (heracles-api)

### 3.1 Formatage

```bash
# OBLIGATOIRE avant chaque commit
black .
isort .
ruff check --fix .
```

### 3.2 Configuration (pyproject.toml)

```toml
[tool.black]
line-length = 88
target-version = ["py311"]

[tool.isort]
profile = "black"
line_length = 88

[tool.ruff]
line-length = 88
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]
ignore = ["E501"]  # line length handled by black

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
```

### 3.3 Type Hints

```python
# ❌ INTERDIT
def get_user(uid):
    return db.query(User).filter_by(uid=uid).first()

# ✅ CORRECT
from typing import Optional
from app.models.schemas.user import UserRead

async def get_user(uid: str) -> Optional[UserRead]:
    """
    Récupère un utilisateur par son UID.
    
    Args:
        uid: Identifiant unique de l'utilisateur
        
    Returns:
        UserRead si trouvé, None sinon
    """
    return await db.query(User).filter_by(uid=uid).first()
```

### 3.4 Docstrings (Google Style)

```python
def create_user(
    user_data: UserCreate,
    requester: UserInfo,
    ldap_service: LdapService,
) -> UserRead:
    """
    Crée un nouvel utilisateur dans LDAP.
    
    Cette fonction vérifie les permissions, valide les données,
    génère les IDs manquants et crée l'entrée LDAP.
    
    Args:
        user_data: Données de l'utilisateur à créer
        requester: Utilisateur effectuant la requête (pour ACL)
        ldap_service: Service LDAP injecté
        
    Returns:
        UserRead: L'utilisateur créé avec son DN
        
    Raises:
        PermissionDeniedError: Si requester n'a pas les droits
        UserAlreadyExistsError: Si l'UID existe déjà
        ValidationError: Si les données sont invalides
        
    Example:
        >>> user = create_user(
        ...     UserCreate(uid="jdoe", cn="John Doe", sn="Doe"),
        ...     current_user,
        ...     ldap_service
        ... )
        >>> print(user.dn)
        uid=jdoe,ou=people,dc=example,dc=com
    """
```

### 3.5 Exceptions Custom

```python
# app/core/exceptions.py

class HeraclesException(Exception):
    """Base exception for Heracles."""
    
    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class UserNotFoundError(HeraclesException):
    """Raised when a user is not found."""
    
    def __init__(self, uid: str):
        super().__init__(
            message=f"User with uid '{uid}' not found",
            code="USER_NOT_FOUND"
        )
        self.uid = uid


class PermissionDeniedError(HeraclesException):
    """Raised when user lacks required permissions."""
    
    def __init__(self, action: str, resource: str):
        super().__init__(
            message=f"Permission denied: {action} on {resource}",
            code="PERMISSION_DENIED"
        )


class LdapOperationError(HeraclesException):
    """Raised when an LDAP operation fails."""
    pass
```

### 3.6 Structure des Routes

```python
# app/api/v1/users.py

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Annotated

from app.api.deps import get_current_user, get_user_service
from app.core.exceptions import UserNotFoundError, PermissionDeniedError
from app.models.schemas.user import UserCreate, UserRead, UserUpdate
from app.models.schemas.common import PaginatedResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=PaginatedResponse[UserRead])
async def list_users(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    filter: Annotated[str | None, Query()] = None,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> PaginatedResponse[UserRead]:
    """Liste les utilisateurs avec pagination."""
    return await user_service.list(
        requester=current_user,
        limit=limit,
        offset=offset,
        filter=filter,
    )


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> UserRead:
    """Crée un nouvel utilisateur."""
    try:
        return await user_service.create(user_data, requester=current_user)
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.message)
```

### 3.7 Structure des Services

```python
# app/services/user_service.py

from typing import Optional, List
from app.models.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.ldap_service import LdapService
from app.services.acl_service import AclService
from app.core.exceptions import UserNotFoundError, PermissionDeniedError


class UserService:
    """Service de gestion des utilisateurs."""
    
    def __init__(
        self,
        ldap_service: LdapService,
        acl_service: AclService,
    ):
        self._ldap = ldap_service
        self._acl = acl_service
    
    async def get_by_uid(self, uid: str, requester: dict) -> UserRead:
        """
        Récupère un utilisateur par son UID.
        
        Args:
            uid: Identifiant de l'utilisateur
            requester: Utilisateur effectuant la requête
            
        Returns:
            UserRead: Données de l'utilisateur
            
        Raises:
            UserNotFoundError: Si utilisateur non trouvé
            PermissionDeniedError: Si accès refusé
        """
        # Vérification ACL
        if not await self._acl.can_read("user", uid, requester):
            raise PermissionDeniedError("read", f"user/{uid}")
        
        # Recherche LDAP
        user = await self._ldap.get_user(uid)
        if not user:
            raise UserNotFoundError(uid)
        
        return user
```

### 3.8 Tests

```python
# tests/test_services/test_user_service.py

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.user_service import UserService
from app.core.exceptions import UserNotFoundError, PermissionDeniedError


@pytest.fixture
def mock_ldap_service():
    return AsyncMock()


@pytest.fixture
def mock_acl_service():
    service = AsyncMock()
    service.can_read.return_value = True
    service.can_write.return_value = True
    return service


@pytest.fixture
def user_service(mock_ldap_service, mock_acl_service):
    return UserService(
        ldap_service=mock_ldap_service,
        acl_service=mock_acl_service,
    )


class TestGetByUid:
    async def test_returns_user_when_found(self, user_service, mock_ldap_service):
        # Arrange
        expected_user = UserRead(
            dn="uid=jdoe,ou=people,dc=example,dc=com",
            uid="jdoe",
            cn="John Doe",
            sn="Doe",
            objectClass=["inetOrgPerson"],
        )
        mock_ldap_service.get_user.return_value = expected_user
        requester = {"dn": "uid=admin,ou=people,dc=example,dc=com"}
        
        # Act
        result = await user_service.get_by_uid("jdoe", requester)
        
        # Assert
        assert result == expected_user
        mock_ldap_service.get_user.assert_called_once_with("jdoe")
    
    async def test_raises_not_found_when_user_missing(
        self, user_service, mock_ldap_service
    ):
        # Arrange
        mock_ldap_service.get_user.return_value = None
        requester = {"dn": "uid=admin,ou=people,dc=example,dc=com"}
        
        # Act & Assert
        with pytest.raises(UserNotFoundError) as exc_info:
            await user_service.get_by_uid("unknown", requester)
        
        assert exc_info.value.uid == "unknown"
    
    async def test_raises_permission_denied_when_acl_fails(
        self, user_service, mock_acl_service
    ):
        # Arrange
        mock_acl_service.can_read.return_value = False
        requester = {"dn": "uid=user,ou=people,dc=example,dc=com"}
        
        # Act & Assert
        with pytest.raises(PermissionDeniedError):
            await user_service.get_by_uid("jdoe", requester)
```

---

## 4. Règles TypeScript/React (heracles-ui)

### 4.1 Configuration TypeScript

```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "jsx": "react-jsx",
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  }
}
```

### 4.2 Formatage

```bash
# OBLIGATOIRE avant chaque commit
npm run lint
npm run format
```

### 4.3 Composants

```typescript
// ❌ INTERDIT - Class components
class UserList extends React.Component { }

// ❌ INTERDIT - any
function UserCard({ user }: { user: any }) { }

// ✅ CORRECT - Functional + typed
interface UserCardProps {
  user: User;
  onEdit?: (uid: string) => void;
  className?: string;
}

export function UserCard({ 
  user, 
  onEdit, 
  className 
}: UserCardProps): JSX.Element {
  return (
    <div className={cn("rounded-lg p-4", className)}>
      <h3>{user.cn}</h3>
      {onEdit && (
        <Button onClick={() => onEdit(user.uid)}>Edit</Button>
      )}
    </div>
  );
}
```

### 4.4 Hooks

```typescript
// src/hooks/useUser.ts

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { usersApi } from '@/api/users';
import type { User, UserCreate, UserUpdate } from '@/types';

export function useUser(uid: string) {
  return useQuery({
    queryKey: ['user', uid],
    queryFn: () => usersApi.getByUid(uid),
    enabled: !!uid,
  });
}

export function useUsers(params?: { filter?: string; limit?: number }) {
  return useQuery({
    queryKey: ['users', params],
    queryFn: () => usersApi.list(params),
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: UserCreate) => usersApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
}

export function useUpdateUser(uid: string) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: UserUpdate) => usersApi.update(uid, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      queryClient.invalidateQueries({ queryKey: ['user', uid] });
    },
  });
}
```

### 4.5 API Client

```typescript
// src/api/client.ts

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

async function request<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<T> {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options?.headers,
    },
  });
  
  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.error.message);
  }
  
  if (response.status === 204) {
    return undefined as T;
  }
  
  return response.json();
}

export const api = {
  get: <T>(endpoint: string) => request<T>(endpoint),
  
  post: <T>(endpoint: string, data: unknown) =>
    request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  put: <T>(endpoint: string, data: unknown) =>
    request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  
  delete: (endpoint: string) =>
    request<void>(endpoint, { method: 'DELETE' }),
};
```

### 4.6 Types

```typescript
// src/types/index.ts

export interface User {
  dn: string;
  uid: string;
  cn: string;
  sn: string;
  givenName?: string;
  mail?: string;
  telephoneNumber?: string;
  objectClass: string[];
  posix?: PosixAccount;
  sshPublicKey?: string[];
}

export interface PosixAccount {
  uidNumber: number;
  gidNumber: number;
  homeDirectory: string;
  loginShell: string;
  gecos?: string;
}

export interface UserCreate {
  uid: string;
  cn: string;
  sn: string;
  givenName?: string;
  mail?: string;
  userPassword?: string;
  posix?: Omit<PosixAccount, 'uidNumber'> & { uidNumber?: number };
}

export interface UserUpdate {
  cn?: string;
  sn?: string;
  givenName?: string;
  mail?: string;
  telephoneNumber?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    total: number;
    limit: number;
    offset: number;
    hasMore: boolean;
  };
}
```

---

## 5. Git & Commits

### 5.1 Branches

| Type | Pattern | Exemple |
|------|---------|---------|
| Feature | `feature/<issue>-<description>` | `feature/42-user-creation` |
| Bugfix | `fix/<issue>-<description>` | `fix/55-password-hash` |
| Hotfix | `hotfix/<description>` | `hotfix/security-patch` |
| Release | `release/<version>` | `release/1.0.0` |

### 5.2 Commits (Conventional Commits)

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

| Type | Description |
|------|-------------|
| feat | Nouvelle fonctionnalité |
| fix | Correction de bug |
| docs | Documentation |
| style | Formatage (pas de changement de code) |
| refactor | Refactoring |
| test | Ajout/modification de tests |
| chore | Maintenance, deps |

**Exemples:**
```
feat(api): add user creation endpoint

- Implement POST /users endpoint
- Add validation for uid format
- Add automatic UID allocation

Closes #42
```

```
fix(core): handle LDAP connection timeout

The connection was not being properly closed on timeout,
causing connection pool exhaustion.

Fixes #55
```

### 5.3 Pull Requests

- Titre: Suit la convention de commit
- Description: Template obligatoire
- Reviews: 1 approbation minimum
- CI: Tous les checks verts
- Tests: Pas de régression

---

## 6. Sécurité

### 6.1 Secrets

```python
# ❌ INTERDIT
LDAP_PASSWORD = "secret123"
SECRET_KEY = "hardcoded-key"

# ✅ CORRECT
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ldap_password: str  # From env LDAP_PASSWORD
    secret_key: str     # From env SECRET_KEY
    
    class Config:
        env_file = ".env"
```

### 6.2 Logging

```python
# ❌ INTERDIT - Ne jamais logger de données sensibles
logger.info(f"User login: {username}, password: {password}")
logger.debug(f"LDAP bind with: {bind_dn}, {bind_password}")

# ✅ CORRECT
logger.info(f"User login attempt: {username}")
logger.debug(f"LDAP bind with DN: {bind_dn}")
```

### 6.3 Validation des Entrées

```python
# ❌ INTERDIT - Injection LDAP possible
filter = f"(uid={user_input})"

# ✅ CORRECT
from ldap3.utils.conv import escape_filter_chars

safe_uid = escape_filter_chars(user_input)
filter = f"(uid={safe_uid})"
```

### 6.4 Dépendances

```bash
# Vérifier régulièrement les vulnérabilités
cargo audit           # Rust
pip-audit             # Python
npm audit             # JavaScript
```

---

## 7. Performance

### 7.1 Requêtes LDAP

```python
# ❌ INTERDIT - N+1 queries
users = ldap.search("(objectClass=posixAccount)")
for user in users:
    groups = ldap.search(f"(memberUid={user.uid})")  # N queries!

# ✅ CORRECT - Single query avec filtre
users = ldap.search("(objectClass=posixAccount)", attributes=["uid", "cn", "memberOf"])
```

### 7.2 Pagination

```python
# ❌ INTERDIT - Charger tous les résultats
all_users = ldap.search("(objectClass=inetOrgPerson)")  # 10000 users!

# ✅ CORRECT - Pagination
users = ldap.search(
    "(objectClass=inetOrgPerson)",
    paged_size=50,
    paged_cookie=cookie,
)
```

### 7.3 Cache

```python
# Utiliser Redis pour les données fréquemment accédées
@cached(ttl=300)  # 5 minutes
async def get_acl_roles() -> list[Role]:
    return await ldap.search("(objectClass=gosaRole)")
```
