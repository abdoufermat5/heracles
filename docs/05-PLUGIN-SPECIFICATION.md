# HERACLES - Spécification des Plugins

> **Référence**: Ce document définit comment créer et intégrer un plugin dans Heracles.
> **Mise à jour**: 24 Janvier 2026
> **Scope**: Uniquement les plugins essentiels listés dans le Project Charter.
> **Statut**: Validé avec l'implémentation du plugin POSIX (65+ tests)

---

## 1. Architecture des Plugins

### 1.1 Vue d'Ensemble

```
┌─────────────────────────────────────────────────────────────────┐
│                     PLUGIN ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  heracles_plugins/              heracles-ui/src/                │
│  └── <plugin_name>/             └── components/plugins/         │
│      ├── __init__.py                └── <plugin_name>/          │
│      ├── plugin.py                      ├── *-tab.tsx           │
│      ├── service.py                     ├── *-form.tsx          │
│      ├── schemas.py                     └── *-status.tsx        │
│      ├── routes.py                                               │
│      └── schemas/                   types/                       │
│          ├── schema.json            └── <plugin_name>.ts        │
│          └── schema_*.json                                       │
│                                                                  │
│                    ┌───────────────────┐                        │
│                    │  Plugin Registry  │                        │
│                    │   - Activation    │                        │
│                    │   - Dependencies  │                        │
│                    │   - Route mount   │                        │
│                    └───────────────────┘                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Types de Plugins

| Type | Description | Exemple |
|------|-------------|---------|
| **Tab Plugin** | Ajoute un onglet à un type d'objet | posix (onglet Unix sur user) |
| **Management Plugin** | Nouveau type d'objet à gérer | systems, sudo |
| **Hybrid Plugin** | Tab + Management combinés | posix (tab user + groups management) |
| **Service Plugin** | Intégration service externe | (future) |

---

## 2. Structure d'un Plugin

### 2.1 Arborescence (Exemple: Plugin POSIX)

```
heracles_plugins/
└── heracles_plugins/
    └── posix/
        ├── __init__.py           # Export du plugin + register_plugin()
        ├── plugin.py             # Définition PluginInfo + Tabs
        ├── service.py            # Logique métier (PosixService, PosixGroupService, MixedGroupService)
        ├── schemas.py            # Modèles Pydantic (Create, Read, Update, List)
        ├── routes.py             # Endpoints API FastAPI
        └── schemas/              # JSON schemas pour UI (optionnel)
            ├── schema.json
            ├── schema_group.json
            └── schema_mixed_group.json
```

### 2.2 Fichier Plugin Principal (Réel)

```python
# heracles_plugins/posix/plugin.py

from typing import List
from heracles_api.plugins.base import PluginInfo, TabDefinition


def get_info() -> PluginInfo:
    """Retourne les métadonnées du plugin."""
    return PluginInfo(
        name="posix",
        version="1.0.0",
        description="POSIX account management (Unix accounts, groups, mixed groups)",
        author="Heracles Team",
        
        # Types d'objets auxquels ce plugin s'attache
        object_types=["user", "group"],
        
        # ObjectClasses LDAP gérés
        object_classes=[
            "posixAccount", 
            "shadowAccount", 
            "posixGroup",
            "posixGroupAux",  # Custom auxiliary for mixed groups
            "hostObject",     # System trust
        ],
        
        # Dépendances (autres plugins requis)
        dependencies=[],  # No hard dependencies
        
        # Dépendances optionnelles
        optional_dependencies=["systems"],  # For host validation
        
        # Priorité d'affichage (ordre des onglets)
        priority=10,
    )


def get_tabs() -> List[TabDefinition]:
    """Définit les onglets fournis par ce plugin."""
    return [
        TabDefinition(
            id="posix-user",
            label="Unix",
            icon="terminal",
            object_type="user",
            description="POSIX/Unix account settings",
        ),
        TabDefinition(
            id="posix-group",
            label="POSIX",
            icon="users",
            object_type="group",
            description="POSIX group settings",
        ),
        TabDefinition(
            id="posix-mixed",
            label="Mixed Groups",
            icon="users-cog",
            object_type="group",
            description="Combined LDAP + POSIX groups",
        ),
    ]
```

### 2.3 Fichier __init__.py (Point d'entrée)

```python
# heracles_plugins/posix/__init__.py

from heracles_api.plugins.registry import get_registry
from .plugin import get_info, get_tabs
from .routes import router


def register_plugin():
    """Register the POSIX plugin with the registry."""
    registry = get_registry()
    info = get_info()
    tabs = get_tabs()
    
    # Register plugin info and tabs
    registry.register(info, tabs)
    
    # Register API routes under /api/v1/
    registry.register_routes(router)
    
    # Optional: activation hook
    print(f"POSIX plugin activated (UID range: {config.get('uid_min', 10000)}-{config.get('uid_max', 60000)})")


# Auto-registration on import
register_plugin()
```

---

## 3. Modèles Pydantic du Plugin

### 3.1 Conventions de Nommage

| Pattern | Usage | Exemple |
|---------|-------|---------|
| `*Create` | Activation/création d'un objet | `PosixAccountCreate` |
| `*Read` | Lecture complète | `PosixAccountRead` |
| `*Update` | Mise à jour partielle | `PosixAccountUpdate` |
| `*ListItem` | Item dans une liste | `PosixGroupListItem` |
| `*ListResponse` | Réponse paginée | `PosixGroupListResponse` |

### 3.2 Schémas Réels (POSIX Plugin)

```python
# heracles_plugins/posix/schemas.py

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, model_validator


class TrustMode(str, Enum):
    """System trust mode for host-based access control."""
    FULL_ACCESS = "fullaccess"  # Allow access to all systems
    BY_HOST = "byhost"          # Restrict access to specific hosts


class AccountStatus(str, Enum):
    """Computed account status based on shadow attributes."""
    ACTIVE = "active"
    EXPIRED = "expired"
    PASSWORD_EXPIRED = "password_expired"
    GRACE_TIME = "grace_time"
    LOCKED = "locked"


class PosixAccountCreate(BaseModel):
    """Schéma pour activer POSIX sur un utilisateur."""
    
    gid_number: int = Field(
        ...,
        ge=1000,
        le=65534,
        alias="gidNumber",
        description="Primary group GID number",
    )
    home_directory: str = Field(
        ...,
        alias="homeDirectory",
        description="Home directory path (e.g., /home/jdoe)",
    )
    login_shell: str = Field(
        default="/bin/bash",
        alias="loginShell",
    )
    gecos: Optional[str] = Field(default=None)
    
    # System trust (hostObject)
    trust_mode: Optional[TrustMode] = Field(
        default=None,
        alias="trustMode",
    )
    host: Optional[List[str]] = Field(default=None)
    
    @field_validator("home_directory")
    @classmethod
    def validate_home_directory(cls, v: str) -> str:
        if not v.startswith("/"):
            raise ValueError("Home directory must be an absolute path")
        return v
    
    @model_validator(mode="after")
    def validate_trust_config(self) -> "PosixAccountCreate":
        if self.trust_mode == TrustMode.BY_HOST and not self.host:
            raise ValueError("host list required when trustMode is byhost")
        return self
    
    class Config:
        populate_by_name = True


class PosixAccountRead(BaseModel):
    """Schéma de lecture POSIX complet."""
    
    uid_number: int = Field(..., alias="uidNumber")
    gid_number: int = Field(..., alias="gidNumber")
    home_directory: str = Field(..., alias="homeDirectory")
    login_shell: str = Field(..., alias="loginShell")
    gecos: Optional[str] = None
    
    # Shadow attributes
    shadow_last_change: Optional[int] = Field(None, alias="shadowLastChange")
    shadow_min: Optional[int] = Field(None, alias="shadowMin")
    shadow_max: Optional[int] = Field(None, alias="shadowMax")
    shadow_warning: Optional[int] = Field(None, alias="shadowWarning")
    shadow_inactive: Optional[int] = Field(None, alias="shadowInactive")
    shadow_expire: Optional[int] = Field(None, alias="shadowExpire")
    
    # System trust
    trust_mode: Optional[TrustMode] = Field(None, alias="trustMode")
    host: Optional[List[str]] = None
    
    # Computed fields
    primary_group_cn: Optional[str] = Field(None, alias="primaryGroupCn")
    group_memberships: List[str] = Field(default_factory=list, alias="groupMemberships")
    is_active: bool = True
    account_status: AccountStatus = Field(default=AccountStatus.ACTIVE, alias="accountStatus")
    
    class Config:
        populate_by_name = True


class PosixAccountUpdate(BaseModel):
    """Mise à jour partielle - tous champs optionnels."""
    
    gid_number: Optional[int] = Field(None, alias="gidNumber")
    home_directory: Optional[str] = Field(None, alias="homeDirectory")
    login_shell: Optional[str] = Field(None, alias="loginShell")
    gecos: Optional[str] = None
    trust_mode: Optional[TrustMode] = Field(None, alias="trustMode")
    host: Optional[List[str]] = None
    
    class Config:
        populate_by_name = True


# === POSIX Group ===

class PosixGroupCreate(BaseModel):
    """Création d'un groupe POSIX."""
    
    cn: str = Field(..., min_length=1, max_length=64)
    gid_number: Optional[int] = Field(None, alias="gidNumber")
    force_gid: bool = Field(default=False, alias="forceGid")
    description: Optional[str] = None
    member_uid: Optional[List[str]] = Field(None, alias="memberUid")
    trust_mode: Optional[TrustMode] = Field(None, alias="trustMode")
    host: Optional[List[str]] = None
    
    class Config:
        populate_by_name = True


class PosixGroupRead(BaseModel):
    """Lecture d'un groupe POSIX."""
    
    cn: str
    gid_number: int = Field(..., alias="gidNumber")
    description: Optional[str] = None
    member_uid: List[str] = Field(default_factory=list, alias="memberUid")
    trust_mode: Optional[TrustMode] = Field(None, alias="trustMode")
    host: Optional[List[str]] = None
    is_active: bool = True
    
    class Config:
        populate_by_name = True


# === Mixed Group (groupOfNames + posixGroupAux) ===

class MixedGroupCreate(BaseModel):
    """
    Création d'un MixedGroup (LDAP + POSIX combinés).
    
    Utilise: groupOfNames (structural) + posixGroupAux (auxiliary)
    """
    
    cn: str = Field(..., min_length=1, max_length=64)
    gid_number: Optional[int] = Field(None, alias="gidNumber")
    force_gid: bool = Field(default=False, alias="forceGid")
    description: Optional[str] = None
    
    # LDAP members (DNs) - accepts UIDs, resolved to DNs automatically
    member: Optional[List[str]] = None
    
    # POSIX members (UIDs)
    member_uid: Optional[List[str]] = Field(None, alias="memberUid")
    
    # System trust
    trust_mode: Optional[TrustMode] = Field(None, alias="trustMode")
    host: Optional[List[str]] = None
    
    class Config:
        populate_by_name = True


class MixedGroupRead(BaseModel):
    """Lecture d'un MixedGroup."""
    
    cn: str
    gid_number: int = Field(..., alias="gidNumber")
    description: Optional[str] = None
    member: List[str] = Field(default_factory=list)
    member_uid: List[str] = Field(default_factory=list, alias="memberUid")
    trust_mode: Optional[TrustMode] = Field(None, alias="trustMode")
    host: Optional[List[str]] = None
    is_mixed_group: bool = Field(True, alias="isMixedGroup")
    
    class Config:
        populate_by_name = True
```

### 3.3 Bonnes Pratiques Pydantic v2

1. **Utiliser `Field(alias="camelCase")`** pour l'API JSON tout en gardant snake_case en Python
2. **`populate_by_name = True`** dans Config pour accepter les deux formats
3. **`@field_validator`** pour validation de champs individuels
4. **`@model_validator(mode="after")`** pour validation cross-field
5. **Enums** pour les valeurs contraintes (TrustMode, AccountStatus)
6. **`Optional[T]`** avec `default=None` pour champs facultatifs

---

## 4. Service du Plugin

### 4.1 Architecture des Services

Un plugin peut avoir plusieurs services selon les types d'objets gérés:

| Service | Responsabilité | Exemple |
|---------|----------------|---------|
| `PosixService` | Comptes POSIX sur users | activate, deactivate, update |
| `PosixGroupService` | Groupes POSIX purs | create, read, update, delete |
| `MixedGroupService` | Groupes hybrides LDAP+POSIX | create, read, update, delete |

### 4.2 Structure d'un Service (Pattern Réel)

```python
# heracles_plugins/posix/service.py

from typing import Optional, List, Dict, Any
from ldap3 import MODIFY_ADD, MODIFY_DELETE, MODIFY_REPLACE

from heracles_api.services.ldap_service import LdapService, LdapOperationError

from .schemas import (
    PosixAccountCreate, 
    PosixAccountRead, 
    PosixAccountUpdate,
    TrustMode,
    AccountStatus,
)


class PosixValidationError(Exception):
    """Erreur de validation spécifique au plugin."""
    pass


class PosixService:
    """
    Service de gestion des comptes POSIX.
    
    Gère l'activation/désactivation des attributs POSIX sur les users.
    """
    
    # ObjectClasses ajoutés lors de l'activation
    OBJECT_CLASSES = ["posixAccount", "shadowAccount"]
    
    # Attributs gérés par ce service
    MANAGED_ATTRIBUTES = [
        "uidNumber", "gidNumber", "homeDirectory", "loginShell", "gecos",
        "shadowLastChange", "shadowMin", "shadowMax", "shadowWarning",
        "shadowInactive", "shadowExpire",
        "host",  # System trust
    ]
    
    def __init__(self, ldap_service: LdapService, config: Dict[str, Any]):
        self._ldap = ldap_service
        self._config = config
        
        # Configuration avec valeurs par défaut
        self._uid_min = config.get("uid_min", 10000)
        self._uid_max = config.get("uid_max", 60000)
        self._default_shell = config.get("default_shell", "/bin/bash")
    
    # =========================================================================
    # Méthodes publiques
    # =========================================================================
    
    async def is_active(self, dn: str) -> bool:
        """Vérifie si POSIX est activé sur l'objet."""
        entry = await self._ldap.get_by_dn(dn, attributes=["objectClass"])
        if entry is None:
            return False
        
        object_classes = entry.get("objectClass", [])
        return "posixAccount" in object_classes
    
    async def get(self, dn: str) -> Optional[PosixAccountRead]:
        """Lit les attributs POSIX d'un utilisateur."""
        if not await self.is_active(dn):
            return None
        
        entry = await self._ldap.get_by_dn(dn, attributes=self.MANAGED_ATTRIBUTES)
        if entry is None:
            return None
        
        # Calcul du statut du compte
        account_status = self._compute_account_status(entry)
        
        return PosixAccountRead(
            uidNumber=self._get_int(entry, "uidNumber"),
            gidNumber=self._get_int(entry, "gidNumber"),
            homeDirectory=entry.get_first("homeDirectory"),
            loginShell=entry.get_first("loginShell", self._default_shell),
            gecos=entry.get_first("gecos"),
            shadowLastChange=self._get_int_optional(entry, "shadowLastChange"),
            shadowMax=self._get_int_optional(entry, "shadowMax"),
            # ... autres attributs shadow
            accountStatus=account_status,
            is_active=True,
        )
    
    async def activate(
        self, 
        dn: str, 
        data: PosixAccountCreate,
        uid: Optional[str] = None,
        group_service: Optional["PosixGroupService"] = None,
    ) -> PosixAccountRead:
        """
        Active POSIX sur un utilisateur.
        
        Étapes:
        1. Vérifier que POSIX n'est pas déjà actif
        2. Allouer un UID si non fourni
        3. Vérifier que le GID existe
        4. Ajouter les objectClasses et attributs
        5. Initialiser les attributs shadow
        """
        if await self.is_active(dn):
            raise PosixValidationError("POSIX is already active on this user")
        
        # Allocation UID
        uid_number = await self._allocate_next_uid()
        
        # Vérification GID
        if not await self._gid_exists(data.gid_number):
            raise PosixValidationError(f"GID {data.gid_number} does not exist")
        
        # Construction des modifications LDAP
        object_classes = list(self.OBJECT_CLASSES)
        if data.trust_mode is not None:
            object_classes.append("hostObject")
        
        import time
        shadow_last_change = int(time.time() / 86400)
        
        changes = {
            "objectClass": [(MODIFY_ADD, object_classes)],
            "uidNumber": [(MODIFY_ADD, [str(uid_number)])],
            "gidNumber": [(MODIFY_ADD, [str(data.gid_number)])],
            "homeDirectory": [(MODIFY_ADD, [data.home_directory])],
            "loginShell": [(MODIFY_ADD, [data.login_shell])],
            "shadowLastChange": [(MODIFY_ADD, [str(shadow_last_change)])],
            "shadowMax": [(MODIFY_ADD, ["99999"])],
        }
        
        if data.gecos:
            changes["gecos"] = [(MODIFY_ADD, [data.gecos])]
        
        # System trust
        if data.trust_mode == TrustMode.FULL_ACCESS:
            changes["host"] = [(MODIFY_ADD, ["*"])]
        elif data.trust_mode == TrustMode.BY_HOST and data.host:
            changes["host"] = [(MODIFY_ADD, data.host)]
        
        try:
            await self._ldap.modify(dn, changes)
        except LdapOperationError as e:
            raise PosixValidationError(f"Failed to activate POSIX: {e}")
        
        return await self.get(dn)
    
    async def deactivate(
        self,
        dn: str,
        delete_personal_group: bool = True,
        group_service: Optional["PosixGroupService"] = None,
    ) -> None:
        """
        Désactive POSIX sur un utilisateur.
        
        Optionnellement supprime le groupe personnel de l'utilisateur.
        """
        if not await self.is_active(dn):
            raise PosixValidationError("POSIX is not active on this user")
        
        # Suppression des objectClasses et attributs
        entry = await self._ldap.get_by_dn(dn, attributes=["objectClass"] + self.MANAGED_ATTRIBUTES)
        
        changes = {}
        
        # Supprimer les objectClasses POSIX
        current_classes = entry.get("objectClass", [])
        classes_to_remove = [c for c in self.OBJECT_CLASSES if c in current_classes]
        if "hostObject" in current_classes:
            classes_to_remove.append("hostObject")
        
        if classes_to_remove:
            changes["objectClass"] = [(MODIFY_DELETE, classes_to_remove)]
        
        # Supprimer les attributs gérés
        for attr in self.MANAGED_ATTRIBUTES:
            if entry.get(attr) is not None:
                changes[attr] = [(MODIFY_DELETE, [])]
        
        await self._ldap.modify(dn, changes)
    
    # =========================================================================
    # Méthodes privées
    # =========================================================================
    
    async def _allocate_next_uid(self) -> int:
        """Alloue le prochain UID disponible."""
        entries = await self._ldap.search(
            search_filter="(uidNumber=*)",
            attributes=["uidNumber"],
        )
        
        used_uids = set()
        for entry in entries:
            uid = self._get_int_optional(entry, "uidNumber")
            if uid is not None:
                used_uids.add(uid)
        
        for uid in range(self._uid_min, self._uid_max + 1):
            if uid not in used_uids:
                return uid
        
        raise PosixValidationError(f"No available UIDs in range {self._uid_min}-{self._uid_max}")
    
    async def _gid_exists(self, gid_number: int) -> bool:
        """Vérifie si un GID existe."""
        entries = await self._ldap.search(
            search_filter=f"(gidNumber={gid_number})",
            attributes=["gidNumber"],
        )
        return len(entries) > 0
    
    def _compute_account_status(self, entry) -> AccountStatus:
        """Calcule le statut du compte basé sur les attributs shadow."""
        import time
        today = int(time.time() / 86400)
        
        shadow_expire = self._get_int_optional(entry, "shadowExpire")
        if shadow_expire and shadow_expire < today:
            return AccountStatus.EXPIRED
        
        shadow_last_change = self._get_int_optional(entry, "shadowLastChange")
        shadow_max = self._get_int_optional(entry, "shadowMax")
        
        if shadow_last_change and shadow_max:
            password_expires = shadow_last_change + shadow_max
            if today > password_expires:
                return AccountStatus.PASSWORD_EXPIRED
        
        return AccountStatus.ACTIVE
    
    def _get_int(self, entry, attr: str) -> int:
        """Extrait un entier obligatoire."""
        val = entry.get_first(attr)
        if val is None:
            raise PosixValidationError(f"Missing required attribute: {attr}")
        return int(val)
    
    def _get_int_optional(self, entry, attr: str) -> Optional[int]:
        """Extrait un entier optionnel."""
        val = entry.get_first(attr) if hasattr(entry, 'get_first') else None
        return int(val) if val is not None else None
```

### 4.3 Service pour les Groupes (Management)

```python
class PosixGroupService:
    """Service pour les groupes POSIX purs (objectClass=posixGroup)."""
    
    OBJECT_CLASSES = ["posixGroup"]
    
    async def create(self, data: PosixGroupCreate) -> PosixGroupRead:
        """Crée un nouveau groupe POSIX."""
        # 1. Vérifier que le groupe n'existe pas
        # 2. Allouer un GID si non fourni (sauf si force_gid)
        # 3. Créer l'entrée LDAP
        pass
    
    async def list_all(self) -> List[PosixGroupListItem]:
        """Liste tous les groupes POSIX."""
        pass


class MixedGroupService:
    """
    Service pour les MixedGroups (groupOfNames + posixGroupAux).
    
    IMPORTANT: Utilise posixGroupAux (AUXILIARY) au lieu de posixGroup (STRUCTURAL)
    car LDAP n'autorise qu'une seule classe structurelle par entrée.
    
    Schéma custom requis (00-heracles-aux.ldif):
    
        dn: cn=heracles-aux,cn=schema,cn=config
        objectClass: olcSchemaConfig
        cn: heracles-aux
        olcObjectClasses: ( 1.3.6.1.4.1.99999.1.2.1 
          NAME 'posixGroupAux' 
          SUP top AUXILIARY 
          MUST gidNumber 
          MAY ( cn $ userPassword $ memberUid $ description ) )
    """
    
    OBJECT_CLASSES = ["groupOfNames", "posixGroupAux"]
    
    async def create(self, data: MixedGroupCreate) -> MixedGroupRead:
        """
        Crée un MixedGroup.
        
        Note: Le champ 'member' accepte des UIDs qui sont automatiquement
        résolus en DNs complets (uid=xxx,ou=people,...).
        """
        pass
```

### 4.4 Bonnes Pratiques Services

1. **Injection de dépendances**: Recevoir `LdapService` et config dans `__init__`
2. **Validation métier**: Lever des exceptions spécifiques (`PosixValidationError`)
3. **Attributs gérés**: Déclarer `MANAGED_ATTRIBUTES` pour cleanup propre
4. **Allocation atomique**: Chercher tous les UIDs/GIDs existants, trouver le premier libre
5. **Support force_gid**: Permettre de forcer un GID même s'il semble utilisé
6. **Résolution de membres**: Convertir UIDs en DNs automatiquement

---

## 5. Interface Utilisateur (UI)

### 5.1 Architecture UI des Plugins

Le plugin POSIX expose ses fonctionnalités à travers:

1. **Onglet dans User Detail** - Activation/config compte POSIX
2. **Page de Liste des Groupes** - Affichage de tous types de groupes
3. **Dialogue de Création** - Formulaire dynamique selon type

```
src/components/plugins/posix/
├── posix-user-tab.tsx           # Onglet Unix (User Detail)
└── groups/
  ├── posix-groups-table.tsx   # Liste POSIX
  ├── mixed-groups-table.tsx   # Liste Mixed
  ├── create-posix-group-dialog.tsx
  └── create-mixed-group-dialog.tsx

src/pages/posix/
├── groups.tsx                   # Page listes POSIX
└── mixed-groups.tsx             # Page listes Mixed
```

### 5.2 Composant Onglet (Tab) - Pattern Réel

```tsx
// src/components/plugins/posix/posix-user-tab.tsx

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Terminal, Shield, Check, AlertCircle } from "lucide-react";

import { useUserPosix, useActivateUserPosix, useDeactivateUserPosix } from "@/hooks/use-posix";

interface PosixUserTabProps {
  userDn: string;
  uid: string;
}

export function PosixUserTab({ userDn, uid }: PosixUserTabProps) {
  // Hooks pour l'état et mutations
  const { data: posixData, isLoading, error } = useUserPosix(uid);
  const activateMutation = useActivateUserPosix(uid);
  const deactivateMutation = useDeactivateUserPosix(uid);
  
  // État local
  const [isActivating, setIsActivating] = useState(false);
  
  if (isLoading) {
    return <LoadingState />;
  }
  
  // POSIX pas encore activé
  if (!posixData?.is_active) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Terminal className="h-5 w-5" />
            Unix Account
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground mb-4">
            POSIX is not enabled for this user.
          </p>
          <Button 
            onClick={() => setIsActivating(true)}
            variant="default"
          >
            Enable Unix Account
          </Button>
          
          {isActivating && (
            <PosixActivationForm 
              userDn={userDn}
              uid={uid}
              onActivate={(data) => activateMutation.mutate({ dn: userDn, data })}
              onCancel={() => setIsActivating(false)}
            />
          )}
        </CardContent>
      </Card>
    );
  }
  
  // POSIX activé - affichage des données
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Terminal className="h-5 w-5" />
            Unix Account
            <Badge variant="success">Active</Badge>
          </CardTitle>
          <AccountStatusBadge status={posixData.accountStatus} />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Informations compte */}
        <div className="grid grid-cols-2 gap-4">
          <InfoRow label="UID Number" value={posixData.uidNumber} />
          <InfoRow label="GID Number" value={posixData.gidNumber} />
          <InfoRow label="Home Directory" value={posixData.homeDirectory} />
          <InfoRow label="Login Shell" value={posixData.loginShell} />
        </div>
        
        {/* System Trust */}
        {posixData.trustMode && (
          <TrustModeCard 
            mode={posixData.trustMode} 
            hosts={posixData.host} 
          />
        )}
        
        {/* Actions */}
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => /* edit mode */}>
            Edit
          </Button>
          <Button 
            variant="destructive" 
            onClick={() => deactivateMutation.mutate(userDn)}
          >
            Disable Unix Account
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// Composant Badge pour le statut du compte
function AccountStatusBadge({ status }: { status: string }) {
  // Ne pas afficher "Active" deux fois (déjà un badge Active)
  if (status === "active") return null;
  
  const variants = {
    expired: { variant: "destructive", icon: AlertCircle, label: "Expired" },
    password_expired: { variant: "warning", icon: AlertCircle, label: "Password Expired" },
  };
  
  const config = variants[status as keyof typeof variants];
  if (!config) return null;
  
  return (
    <Badge variant={config.variant as any}>
      <config.icon className="h-3 w-3 mr-1" />
      {config.label}
    </Badge>
  );
}
```

### 5.3 Hooks React Query

```tsx
// src/hooks/use-posix.ts

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { posixApi } from "@/lib/api";

export function useUserPosix(uid: string) {
  return useQuery({
    queryKey: ["posix", "user", uid],
    queryFn: () => posixApi.getUserPosix(uid),
    enabled: !!uid,
  });
}

export function useActivateUserPosix(uid: string) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: PosixAccountCreate) => posixApi.activateUserPosix(uid, data),
    onSuccess: () => {
      // Invalider le cache pour rafraîchir
      queryClient.invalidateQueries({ queryKey: ["posix", "user", uid] });
    },
  });
}

export function usePosixGroups(type?: "posix" | "mixed") {
  return useQuery({
    queryKey: ["posix-groups", type],
    queryFn: () => api.posix.getGroups(type),
  });
}
```

### 5.4 Formulaire de Création de Groupe

```tsx
// src/components/plugins/posix/groups/create-posix-group-dialog.tsx

export function GroupCreateDialog({ open, onOpenChange }: Props) {
  const [groupType, setGroupType] = useState<"ldap" | "posix" | "mixed">("ldap");
  
  const form = useForm<GroupCreateForm>({
    resolver: zodResolver(groupCreateSchema),
    defaultValues: {
      cn: "",
      description: "",
      gidNumber: undefined,
      members: [],
    },
  });
  
  // Schéma dynamique selon le type
  const schema = useMemo(() => {
    switch (groupType) {
      case "posix":
        return posixGroupSchema;  // gidNumber requis
      case "mixed":
        return mixedGroupSchema;  // gidNumber + members
      default:
        return ldapGroupSchema;   // members seulement
    }
  }, [groupType]);
  
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Group</DialogTitle>
        </DialogHeader>
        
        {/* Sélecteur de type */}
        <div className="flex gap-2 mb-4">
          <TypeButton 
            type="ldap" 
            active={groupType === "ldap"}
            onClick={() => setGroupType("ldap")}
            label="LDAP Group"
            description="Standard organizational group"
          />
          <TypeButton 
            type="posix" 
            active={groupType === "posix"}
            onClick={() => setGroupType("posix")}
            label="POSIX Group"
            description="Unix/Linux group with GID"
          />
          <TypeButton 
            type="mixed" 
            active={groupType === "mixed"}
            onClick={() => setGroupType("mixed")}
            label="Mixed Group"
            description="LDAP + POSIX combined"
          />
        </div>
        
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)}>
            {/* Champs communs */}
            <FormField
              control={form.control}
              name="cn"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Group Name</FormLabel>
                  <FormControl>
                    <Input {...field} placeholder="developers" />
                  </FormControl>
                </FormItem>
              )}
            />
            
            {/* Champs conditionnels */}
            {(groupType === "posix" || groupType === "mixed") && (
              <FormField
                control={form.control}
                name="gidNumber"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>GID Number</FormLabel>
                    <FormControl>
                      <Input 
                        type="number" 
                        {...field} 
                        placeholder="Auto-assigned" 
                      />
                    </FormControl>
                    <FormDescription>
                      Leave empty for automatic allocation
                    </FormDescription>
                  </FormItem>
                )}
              />
            )}
            
            {(groupType === "ldap" || groupType === "mixed") && (
              <MemberSelector 
                control={form.control}
                name="members"
              />
            )}
            
            <DialogFooter>
              <Button type="submit">Create Group</Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
```

### 5.5 Bonnes Pratiques UI

1. **Composants shadcn/ui** - Utiliser Card, Badge, Button, Dialog, Form
2. **React Query** - Pour état serveur (useQuery, useMutation, invalidation)
3. **Zod** - Validation côté client avec `zodResolver`
4. **Hooks personnalisés** - Encapsuler la logique dans des hooks réutilisables
5. **Badges de statut** - Colorer selon le type (success=Active, warning=Expired...)
6. **Formulaires conditionnels** - Afficher/masquer champs selon le contexte

---

## 6. Enregistrement et Chargement du Plugin

### 6.1 Structure Package Python

Le plugin est un package Python installable:

```
heracles_plugins/
├── pyproject.toml      # Config build/dependencies
├── README.md
└── heracles_plugins/
    ├── __init__.py     # Export des plugins
    └── posix/
        ├── __init__.py
        ├── schemas.py  # Pydantic models
        ├── service.py  # Business logic
        └── router.py   # FastAPI routes
```

### 6.2 Point d'Entrée (pyproject.toml)

```toml
[project]
name = "heracles_plugins"
version = "0.1.0"
description = "Heracles LDAP Manager Plugins"

[project.entry-points."heracles.plugins"]
posix = "heracles_plugins.posix"
# Future plugins:
# ssh = "heracles_plugins.ssh"
# sudo = "heracles_plugins.sudo"
```

### 6.3 Module __init__.py

```python
# heracles_plugins/__init__.py
"""Heracles plugins package."""

__version__ = "0.1.0"
```

```python
# heracles_plugins/posix/__init__.py
"""
POSIX Plugin for Heracles.

Provides Unix account management:
- POSIX accounts (posixAccount, shadowAccount)
- POSIX groups (posixGroup)  
- Mixed groups (groupOfNames + posixGroupAux)
- System trust (hostObject)
"""

from .router import router
from .schemas import (
    PosixAccountCreate,
    PosixAccountRead,
    PosixAccountUpdate,
    PosixGroupCreate,
    PosixGroupRead,
    MixedGroupCreate,
    MixedGroupRead,
    TrustMode,
    AccountStatus,
)
from .service import PosixService, PosixGroupService, MixedGroupService

__all__ = [
    "router",
    "PosixService",
    "PosixGroupService", 
    "MixedGroupService",
    "PosixAccountCreate",
    "PosixAccountRead",
    "PosixAccountUpdate",
    "PosixGroupCreate",
    "PosixGroupRead",
    "MixedGroupCreate",
    "MixedGroupRead",
    "TrustMode",
    "AccountStatus",
]
```

### 6.4 Enregistrement du Router (API)

```python
# heracles_api/plugins/__init__.py

from fastapi import APIRouter
from heracles_plugins import posix

def register_plugin_routers(app_router: APIRouter):
    """Enregistre les routers de tous les plugins."""
    
    # POSIX plugin - préfixe /posix
    app_router.include_router(
        posix.router,
        prefix="/posix",
        tags=["posix"],
    )
    
    # Future plugins...
    # app_router.include_router(ssh.router, prefix="/ssh", tags=["ssh"])
```

```python
# heracles_api/main.py

from fastapi import FastAPI
from heracles_api.api.router import api_router
from heracles_api.plugins import register_plugin_routers

app = FastAPI(title="Heracles API")

# Core routes
app.include_router(api_router, prefix="/api/v1")

# Plugin routes
register_plugin_routers(api_router)
```

### 6.5 Router du Plugin

```python
# heracles_plugins/posix/router.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List

from heracles_api.core.deps import get_ldap_service, get_current_user
from heracles_api.services.ldap_service import LdapService

from .schemas import (
    PosixAccountCreate,
    PosixAccountRead,
    PosixGroupCreate,
    PosixGroupRead,
    PosixGroupListItem,
    MixedGroupCreate,
    MixedGroupRead,
)
from .service import PosixService, PosixGroupService, MixedGroupService

router = APIRouter()


# === Comptes POSIX ===

@router.get("/users/{user_dn}/posix", response_model=PosixAccountRead | None)
async def get_posix_account(
    user_dn: str,
    ldap: LdapService = Depends(get_ldap_service),
    _user=Depends(get_current_user),
):
    """Lit les attributs POSIX d'un utilisateur."""
    service = PosixService(ldap, {})
    return await service.get(user_dn)


@router.post("/users/{user_dn}/posix/activate", response_model=PosixAccountRead)
async def activate_posix(
    user_dn: str,
    data: PosixAccountCreate,
    ldap: LdapService = Depends(get_ldap_service),
    _user=Depends(get_current_user),
):
    """Active POSIX sur un utilisateur."""
    service = PosixService(ldap, {})
    group_service = PosixGroupService(ldap, {})
    
    # Récupérer l'UID de l'utilisateur
    entry = await ldap.get_by_dn(user_dn, attributes=["uid"])
    uid = entry.get_first("uid") if entry else None
    
    return await service.activate(user_dn, data, uid=uid, group_service=group_service)


@router.delete("/users/{user_dn}/posix")
async def deactivate_posix(
    user_dn: str,
    delete_personal_group: bool = True,
    ldap: LdapService = Depends(get_ldap_service),
    _user=Depends(get_current_user),
):
    """Désactive POSIX sur un utilisateur."""
    service = PosixService(ldap, {})
    group_service = PosixGroupService(ldap, {})
    await service.deactivate(user_dn, delete_personal_group, group_service)
    return {"message": "POSIX deactivated"}


# === Groupes POSIX ===

@router.get("/groups/posix", response_model=List[PosixGroupListItem])
async def list_posix_groups(
    ldap: LdapService = Depends(get_ldap_service),
    _user=Depends(get_current_user),
):
    """Liste tous les groupes POSIX."""
    service = PosixGroupService(ldap, {})
    return await service.list_all()


@router.post("/groups/posix", response_model=PosixGroupRead)
async def create_posix_group(
    data: PosixGroupCreate,
    ldap: LdapService = Depends(get_ldap_service),
    _user=Depends(get_current_user),
):
    """Crée un groupe POSIX."""
    service = PosixGroupService(ldap, {})
    return await service.create(data)


# === Groupes Mixtes ===

@router.get("/groups/mixed", response_model=List[MixedGroupRead])
async def list_mixed_groups(
    ldap: LdapService = Depends(get_ldap_service),
    _user=Depends(get_current_user),
):
    """Liste tous les MixedGroups."""
    service = MixedGroupService(ldap, {})
    return await service.list_all()


@router.post("/groups/mixed", response_model=MixedGroupRead)
async def create_mixed_group(
    data: MixedGroupCreate,
    ldap: LdapService = Depends(get_ldap_service),
    _user=Depends(get_current_user),
):
    """Crée un MixedGroup (groupOfNames + posixGroupAux)."""
    service = MixedGroupService(ldap, {})
    return await service.create(data)
```

### 6.6 Schéma LDAP Personnalisé

Pour les fonctionnalités avancées (posixGroupAux), un schéma custom est requis:

```ldif
# docker/ldap/schemas/00-heracles-aux.ldif

dn: cn=heracles-aux,cn=schema,cn=config
objectClass: olcSchemaConfig
cn: heracles-aux
olcObjectClasses: ( 1.3.6.1.4.1.99999.1.2.1 
  NAME 'posixGroupAux' 
  DESC 'Auxiliary POSIX group - can be combined with groupOfNames' 
  SUP top AUXILIARY 
  MUST gidNumber 
  MAY ( cn $ userPassword $ memberUid $ description ) )
```

**Important**: Le volume Docker ne doit PAS être `:ro` (read-only) pour permettre le chargement du schéma au démarrage.

---

## 7. Plugins Essentiels - Spécifications

### 7.1 Plugin Core (Référence)

| Aspect | Valeur |
|--------|--------|
| **Nom** | `core` |
| **Statut** | ✅ Implémenté |
| **ObjectClasses** | `inetOrgPerson`, `organizationalUnit`, `groupOfNames` |
| **Dépendances** | Aucune |
| **Onglets** | Gestion de base users/groups |

### 7.2 Plugin POSIX (Implémenté)

| Aspect | Valeur |
|--------|--------|
| **Nom** | `posix` |
| **Statut** | ✅ **IMPLÉMENTÉ** (Sprint 11-12) |
| **Package** | `heracles_plugins.posix` |
| **ObjectClasses** | Voir tableau ci-dessous |
| **Dépendances** | `core` |
| **API Prefix** | `/api/v1/posix` |

#### ObjectClasses Supportés

| ObjectClass | Type | Usage |
|-------------|------|-------|
| `posixAccount` | AUXILIARY | Compte Unix sur user |
| `shadowAccount` | AUXILIARY | Attributs shadow password |
| `posixGroup` | STRUCTURAL | Groupe Unix pur |
| `posixGroupAux` | AUXILIARY (custom) | Groupe mixte LDAP+Unix |
| `hostObject` | AUXILIARY | System Trust (accès hosts) |

#### Endpoints API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/posix/users/{dn}/posix` | Lire compte POSIX |
| POST | `/posix/users/{dn}/posix/activate` | Activer POSIX |
| PATCH | `/posix/users/{dn}/posix` | Modifier compte POSIX |
| DELETE | `/posix/users/{dn}/posix` | Désactiver POSIX |
| GET | `/posix/groups/posix` | Lister groupes POSIX |
| POST | `/posix/groups/posix` | Créer groupe POSIX |
| GET | `/posix/groups/mixed` | Lister MixedGroups |
| POST | `/posix/groups/mixed` | Créer MixedGroup |

#### Fonctionnalités Implémentées

- ✅ Activation/désactivation POSIX sur users
- ✅ Allocation automatique UID/GID
- ✅ Support `force_gid` pour forcer un GID existant
- ✅ Trois types de groupes (LDAP, POSIX, Mixed)
- ✅ System Trust (hostObject avec `*` ou liste de hosts)
- ✅ Attributs Shadow (expiration, warning, etc.)
- ✅ Calcul automatique AccountStatus (active/expired/password_expired)
- ✅ Résolution automatique UIDs → DNs pour membres

#### Schéma Custom Requis

```ldif
# Schéma posixGroupAux (OID 1.3.6.1.4.1.99999.1.2.1)
# Permet de combiner groupOfNames + attributs POSIX
```

### 7.3 Plugin Sudo (Planifié)

| Aspect | Valeur |
|--------|--------|
| **Nom** | `sudo` |
| **Statut** | 📋 Planifié (Sprint 13-14) |
| **ObjectClasses** | `sudoRole` |
| **Dépendances** | `core`, `posix` |
| **Type** | Management (nouveau type d'objet) |

### 7.4 Plugin SSH (Planifié)

| Aspect | Valeur |
|--------|--------|
| **Nom** | `ssh` |
| **Statut** | 📋 Planifié (Sprint 15-16) |
| **ObjectClasses** | `ldapPublicKey` |
| **Dépendances** | `core` |
| **Onglets** | `ssh` (user) |

### 7.5 Plugin Systems (Planifié)

| Aspect | Valeur |
|--------|--------|
| **Nom** | `systems` |
| **Statut** | 📋 Planifié (Sprint 17-18) |
| **ObjectClasses** | `hrcServer`, `hrcWorkstation`, `ipHost`, `ieee802Device` |
| **Dépendances** | `core` |
| **Type** | Management |

> **Note**: Une fois le plugin Systems implémenté, le plugin POSIX pourra
> valider les noms de hosts dans le System Trust contre les objets Systems réels.

---

## 8. Leçons Apprises (POSIX Implementation)

### 8.1 Contraintes LDAP

1. **Une seule classe STRUCTURAL par entrée**
   - Problème: `posixGroup` et `groupOfNames` sont tous deux STRUCTURAL
   - Solution: Créer `posixGroupAux` comme AUXILIARY

2. **Les schémas custom doivent être chargés au boot**
   - Le volume Docker ne doit pas être `:ro` (read-only)
   - Chemin: `/container/service/slapd/assets/config/bootstrap/ldif/custom/`

3. **OID pour schémas privés**
   - Utiliser un OID privé (ex: 1.3.6.1.4.1.99999.x.x.x)
   - Documenter l'allocation des OID

### 8.2 Bonnes Pratiques Backend

1. **Services séparés par type d'objet**
   - `PosixService` pour les comptes users
   - `PosixGroupService` pour les groupes purs
   - `MixedGroupService` pour les groupes hybrides

2. **Résolution de membres**
   - L'API accepte des UIDs courts (`testuser`)
   - Le service résout en DNs complets (`uid=testuser,ou=people,dc=example,dc=org`)

3. **Force flags**
   - `force_gid=True` pour contourner les vérifications de conflit

### 8.3 Bonnes Pratiques UI

1. **Éviter les badges dupliqués**
   - Vérifier `status !== 'active'` avant d'afficher un badge de statut

2. **Formulaires conditionnels**
   - Afficher/masquer champs selon le type sélectionné

3. **Invalidation de cache**
   - `queryClient.invalidateQueries()` après chaque mutation
