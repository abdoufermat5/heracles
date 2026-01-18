# HERACLES - Directives pour Agents IA

> **Référence**: Ce document définit les règles que tout agent IA doit suivre lors du développement d'Heracles.
> **Criticité**: Ce document doit être lu EN PREMIER avant toute action.

---

## 1. Instructions Fondamentales

### 1.1 Ordre de Lecture des Documents

Avant de coder quoi que ce soit, l'agent DOIT lire dans cet ordre:

1. `00-PROJECT-CHARTER.md` - Vision et contraintes
2. `01-ARCHITECTURE.md` - Structure technique
3. `04-CODING-RULES.md` - Standards de code
4. Le document spécifique à la tâche (API, Plugin, etc.)

### 1.2 Règles Absolues (JAMAIS violer)

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                           RÈGLES INVIOLABLES                                  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  1. COMPATIBILITÉ LDAP                                                        ║
║     Utiliser UNIQUEMENT les schémas LDAP FusionDirectory existants.          ║
║     NE JAMAIS créer de nouveaux objectClass ou attributeType.                 ║
║                                                                               ║
║  2. STACK TECHNOLOGIQUE                                                       ║
║     - Rust pour heracles-core                                                 ║
║     - Python 3.11+ / FastAPI pour heracles-api                               ║
║     - React 18+ / TypeScript pour heracles-ui                                ║
║     NE JAMAIS utiliser d'autres langages/frameworks.                         ║
║                                                                               ║
║  3. STRUCTURE DES FICHIERS                                                    ║
║     Respecter EXACTEMENT la structure définie dans 01-ARCHITECTURE.md.       ║
║     NE JAMAIS créer de fichiers hors de cette structure.                     ║
║                                                                               ║
║  4. SÉCURITÉ                                                                  ║
║     - Pas de secrets en dur dans le code                                     ║
║     - Échapper toutes les entrées utilisateur                                ║
║     - Valider avec Pydantic côté API                                         ║
║                                                                               ║
║  5. TESTS                                                                     ║
║     Toute nouvelle fonction DOIT avoir des tests unitaires.                  ║
║     Coverage minimum: 80%                                                     ║
║                                                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## 2. Processus de Développement

### 2.1 Avant de Coder

```
┌─────────────────────────────────────────────────────────────────┐
│                    CHECKLIST PRÉ-DÉVELOPPEMENT                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  □ Ai-je lu les documents de spécification pertinents?          │
│  □ La tâche est-elle dans le scope de la roadmap?               │
│  □ Existe-t-il du code similaire que je peux réutiliser?        │
│  □ Ai-je identifié les fichiers à créer/modifier?               │
│  □ La tâche respecte-t-elle la compatibilité LDAP?              │
│  □ Ai-je planifié les tests à écrire?                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Pendant le Développement

1. **Une chose à la fois**: Ne pas mélanger plusieurs fonctionnalités
2. **Commits atomiques**: Un commit = un changement logique
3. **Tests en parallèle**: Écrire les tests avec le code
4. **Documentation inline**: Docstrings sur toutes les fonctions publiques

### 2.3 Après le Développement

```
┌─────────────────────────────────────────────────────────────────┐
│                    CHECKLIST POST-DÉVELOPPEMENT                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  □ Les tests passent-ils? (cargo test, pytest, npm test)        │
│  □ Le linting passe-t-il? (clippy, ruff, eslint)                │
│  □ Le formatage est-il correct? (cargo fmt, black, prettier)    │
│  □ La documentation est-elle à jour?                            │
│  □ Le code compile/s'exécute sans erreur?                       │
│  □ Ai-je testé manuellement si applicable?                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Patterns à Suivre

### 3.1 Création d'un Endpoint API

```python
# TEMPLATE: Nouvel endpoint FastAPI

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated

from app.api.deps import get_current_user, get_service
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.schemas.xxx import XxxCreate, XxxRead, XxxUpdate
from app.services.xxx_service import XxxService

router = APIRouter(prefix="/xxx", tags=["xxx"])


@router.get("/{id}", response_model=XxxRead)
async def get_xxx(
    id: str,
    current_user: dict = Depends(get_current_user),
    service: XxxService = Depends(get_service),
) -> XxxRead:
    """
    Récupère un XXX par son ID.
    
    Args:
        id: Identifiant unique
        
    Returns:
        XxxRead: Données de l'objet
        
    Raises:
        HTTPException 404: Non trouvé
        HTTPException 403: Accès refusé
    """
    try:
        return await service.get_by_id(id, requester=current_user)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"XXX {id} not found"
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
```

### 3.2 Création d'un Service

```python
# TEMPLATE: Nouveau service

from typing import Optional, List
from app.services.ldap_service import LdapService
from app.services.acl_service import AclService
from app.core.exceptions import NotFoundError, PermissionDeniedError


class XxxService:
    """Service de gestion des XXX."""
    
    def __init__(
        self,
        ldap_service: LdapService,
        acl_service: AclService,
    ):
        self._ldap = ldap_service
        self._acl = acl_service
    
    async def get_by_id(self, id: str, requester: dict) -> XxxRead:
        """
        Récupère un XXX par son ID.
        
        Args:
            id: Identifiant de l'objet
            requester: Utilisateur effectuant la requête
            
        Returns:
            XxxRead: Données de l'objet
            
        Raises:
            NotFoundError: Si non trouvé
            PermissionDeniedError: Si accès refusé
        """
        # 1. Vérifier ACL
        if not await self._acl.can_read("xxx", id, requester):
            raise PermissionDeniedError("read", f"xxx/{id}")
        
        # 2. Chercher dans LDAP
        result = await self._ldap.search(
            filter=f"(cn={id})",
            base_dn=self._config["xxx_base_dn"],
            attributes=["*"],
        )
        
        if not result:
            raise NotFoundError(f"XXX {id}")
        
        # 3. Convertir et retourner
        return self._to_read_model(result[0])
```

### 3.3 Création d'un Composant React

```typescript
// TEMPLATE: Nouveau composant React

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { Button } from '@/components/ui/button';
import { xxxApi } from '@/api/xxx';
import type { Xxx, XxxCreate } from '@/types';

interface XxxFormProps {
  initialData?: Xxx;
  onSuccess?: (xxx: Xxx) => void;
  onCancel?: () => void;
}

export function XxxForm({ 
  initialData, 
  onSuccess, 
  onCancel 
}: XxxFormProps): JSX.Element {
  const queryClient = useQueryClient();
  const isEdit = !!initialData;
  
  const mutation = useMutation({
    mutationFn: isEdit 
      ? (data: XxxCreate) => xxxApi.update(initialData.id, data)
      : (data: XxxCreate) => xxxApi.create(data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['xxx'] });
      onSuccess?.(data);
    },
  });
  
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    // ... validation et mutation
  };
  
  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* ... champs du formulaire */}
      <div className="flex justify-end gap-2">
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel}>
            Annuler
          </Button>
        )}
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? 'Enregistrement...' : 'Enregistrer'}
        </Button>
      </div>
    </form>
  );
}
```

### 3.4 Création d'un Plugin

Voir `05-PLUGIN-SPECIFICATION.md` pour le template complet.

---

## 4. Erreurs Courantes à Éviter

### 4.1 Erreurs LDAP

```python
# ❌ ERREUR: Injection LDAP
filter = f"(uid={user_input})"

# ✅ CORRECT: Échappement
from ldap3.utils.conv import escape_filter_chars
filter = f"(uid={escape_filter_chars(user_input)})"
```

```python
# ❌ ERREUR: Nouveau schéma LDAP
objectClass: heraclesCustomClass  # INTERDIT!

# ✅ CORRECT: Schéma FusionDirectory existant
objectClass: inetOrgPerson
objectClass: posixAccount
```

### 4.2 Erreurs API

```python
# ❌ ERREUR: Logique dans la route
@router.post("/users")
async def create_user(data: UserCreate):
    # Trop de logique ici!
    ldap.add(...)
    db.insert(...)
    send_email(...)

# ✅ CORRECT: Déléguer au service
@router.post("/users")
async def create_user(
    data: UserCreate,
    service: UserService = Depends(get_user_service),
):
    return await service.create(data)
```

```python
# ❌ ERREUR: Pas de type hints
def get_user(uid):
    return ldap.search(uid)

# ✅ CORRECT: Type hints complets
async def get_user(uid: str) -> Optional[UserRead]:
    return await ldap.search(uid)
```

### 4.3 Erreurs React

```typescript
// ❌ ERREUR: any
const UserCard = ({ user }: { user: any }) => { }

// ✅ CORRECT: Types stricts
interface UserCardProps {
  user: User;
}
const UserCard = ({ user }: UserCardProps): JSX.Element => { }
```

```typescript
// ❌ ERREUR: State pour données serveur
const [users, setUsers] = useState<User[]>([]);
useEffect(() => {
  fetch('/api/users').then(r => r.json()).then(setUsers);
}, []);

// ✅ CORRECT: React Query
const { data: users } = useQuery({
  queryKey: ['users'],
  queryFn: () => usersApi.list(),
});
```

### 4.4 Erreurs Sécurité

```python
# ❌ ERREUR: Secret en dur
SECRET_KEY = "my-super-secret-key"

# ✅ CORRECT: Variable d'environnement
from app.core.config import settings
SECRET_KEY = settings.secret_key
```

```python
# ❌ ERREUR: Logger des données sensibles
logger.info(f"User {uid} logged in with password {password}")

# ✅ CORRECT: Pas de données sensibles
logger.info(f"User {uid} logged in successfully")
```

---

## 5. Questions Fréquentes

### Q: Puis-je utiliser une bibliothèque non listée?

**R**: Non, sauf si elle est ajoutée à la liste des dépendances autorisées dans `00-PROJECT-CHARTER.md`. Si vous pensez qu'une bibliothèque est nécessaire, documentez pourquoi et attendez approbation.

### Q: Comment gérer une fonctionnalité non spécifiée?

**R**: Si la fonctionnalité n'est pas dans la roadmap ou les spécifications:
1. Vérifier si elle est vraiment nécessaire
2. Si oui, documenter la proposition
3. Ne PAS implémenter sans approbation

### Q: Que faire si je trouve un bug dans le code existant?

**R**: 
1. Créer une issue/ticket séparé
2. Ne pas mélanger le fix avec la tâche en cours
3. Documenter le bug et la correction proposée

### Q: Comment gérer la compatibilité avec FusionDirectory?

**R**: 
1. Utiliser uniquement les schémas LDAP FD
2. Tester en environnement avec FD installé
3. Vérifier que les entrées créées sont lisibles par FD
4. Vérifier que les entrées FD sont lisibles par Heracles

### Q: Puis-je refactorer du code existant?

**R**: Oui, si:
1. Le refactoring améliore la qualité/lisibilité
2. Les tests existants continuent de passer
3. Le changement est documenté dans le commit
4. C'est fait dans un commit séparé

---

## 6. Contacts et Ressources

### Documentation

| Document | Usage |
|----------|-------|
| `00-PROJECT-CHARTER.md` | Vision, contraintes |
| `01-ARCHITECTURE.md` | Structure technique |
| `02-API-SPECIFICATION.md` | Contrat API |
| `03-DATA-MODEL.md` | Schémas LDAP/DB |
| `04-CODING-RULES.md` | Standards de code |
| `05-PLUGIN-SPECIFICATION.md` | Création plugins |
| `06-SECURITY.md` | Règles sécurité |
| `07-ROADMAP.md` | Planning |

### Schémas LDAP FusionDirectory

Référence pour les schémas LDAP:
- `core-fd.schema`
- `core-fd-conf.schema`
- Schémas des plugins dans `fd-plugins/`

---

## 7. Résumé des Commandes

```bash
# Rust (heracles-core)
cd heracles-core
cargo build
cargo test
cargo fmt
cargo clippy

# Python (heracles-api)
cd heracles-api
poetry install
poetry run pytest
poetry run black .
poetry run ruff check --fix .

# React (heracles-ui)
cd heracles-ui
npm install
npm run dev
npm test
npm run lint
npm run format

# Docker (développement)
docker-compose up -d  # LDAP, PostgreSQL, Redis
```
