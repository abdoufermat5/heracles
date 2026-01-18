# HERACLES - Spécification des Plugins

> **Référence**: Ce document définit comment créer et intégrer un plugin dans Heracles.
> **Scope**: Uniquement les plugins essentiels listés dans le Project Charter.

---

## 1. Architecture des Plugins

### 1.1 Vue d'Ensemble

```
┌─────────────────────────────────────────────────────────────────┐
│                     PLUGIN ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌───────────────┐      ┌───────────────┐      ┌─────────────┐ │
│  │    Plugin     │      │   Plugin      │      │  Frontend   │ │
│  │   Backend     │─────▶│   Schema      │◀─────│  Components │ │
│  │   (Python)    │      │   (JSON)      │      │   (React)   │ │
│  └───────────────┘      └───────────────┘      └─────────────┘ │
│         │                      │                      │         │
│         └──────────────────────┼──────────────────────┘         │
│                                ▼                                 │
│                    ┌───────────────────┐                        │
│                    │  Plugin Registry  │                        │
│                    │   - Activation    │                        │
│                    │   - Dependencies  │                        │
│                    │   - Hooks         │                        │
│                    └───────────────────┘                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Types de Plugins

| Type | Description | Exemple |
|------|-------------|---------|
| **Tab Plugin** | Ajoute un onglet à un type d'objet | posix (onglet sur user) |
| **Management Plugin** | Nouveau type d'objet à gérer | systems |
| **Service Plugin** | Intégration service externe | (future) |

---

## 2. Structure d'un Plugin

### 2.1 Arborescence

```
heracles-plugins/
└── posix/
    ├── __init__.py           # Export du plugin
    ├── plugin.py             # Définition du plugin
    ├── service.py            # Logique métier
    ├── schemas.py            # Modèles Pydantic
    ├── routes.py             # Endpoints API (optionnel)
    ├── schema.json           # Schéma de formulaire UI
    └── tests/
        ├── __init__.py
        ├── test_service.py
        └── test_schemas.py
```

### 2.2 Fichier Plugin Principal

```python
# heracles-plugins/posix/plugin.py

from typing import List, Type
from heracles_api.plugins.base import Plugin, PluginInfo, TabDefinition

from .service import PosixService
from .schemas import PosixAccountCreate, PosixAccountRead, PosixAccountUpdate


class PosixPlugin(Plugin):
    """Plugin de gestion des comptes POSIX."""
    
    @staticmethod
    def info() -> PluginInfo:
        """Retourne les métadonnées du plugin."""
        return PluginInfo(
            name="posix",
            version="1.0.0",
            description="POSIX account management (Unix accounts)",
            author="Heracles Team",
            
            # Types d'objets auxquels ce plugin s'attache
            object_types=["user", "group"],
            
            # ObjectClasses LDAP gérés
            object_classes=["posixAccount", "shadowAccount", "posixGroup"],
            
            # Dépendances (autres plugins requis)
            dependencies=["core"],
            
            # Configuration requise
            required_config=[],
            
            # Priorité d'affichage (ordre des onglets)
            priority=10,
        )
    
    @staticmethod
    def tabs() -> List[TabDefinition]:
        """Définit les onglets fournis par ce plugin."""
        return [
            TabDefinition(
                id="posix",
                label="Unix",
                icon="terminal",
                object_type="user",
                activation_filter="(objectClass=posixAccount)",
                schema_file="schema.json",
                service_class=PosixService,
                create_schema=PosixAccountCreate,
                read_schema=PosixAccountRead,
                update_schema=PosixAccountUpdate,
            ),
            TabDefinition(
                id="posix-group",
                label="POSIX",
                icon="users",
                object_type="group",
                activation_filter="(objectClass=posixGroup)",
                schema_file="schema_group.json",
                service_class=PosixGroupService,
                create_schema=PosixGroupCreate,
                read_schema=PosixGroupRead,
                update_schema=PosixGroupUpdate,
            ),
        ]
    
    def on_activate(self) -> None:
        """Hook appelé à l'activation du plugin."""
        self.logger.info("POSIX plugin activated")
    
    def on_deactivate(self) -> None:
        """Hook appelé à la désactivation du plugin."""
        self.logger.info("POSIX plugin deactivated")
```

---

## 3. Modèles Pydantic du Plugin

### 3.1 Schémas

```python
# heracles-plugins/posix/schemas.py

from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator


class PosixAccountBase(BaseModel):
    """Attributs communs POSIX."""
    
    gid_number: int = Field(
        ...,
        ge=1000,
        le=65534,
        alias="gidNumber",
        description="Primary group GID",
    )
    home_directory: str = Field(
        ...,
        pattern=r"^/[\w/.-]+$",
        alias="homeDirectory",
        description="Home directory path",
    )
    login_shell: str = Field(
        default="/bin/bash",
        alias="loginShell",
        description="Login shell",
    )
    gecos: Optional[str] = Field(
        default=None,
        description="GECOS field (usually full name)",
    )


class PosixAccountCreate(PosixAccountBase):
    """Schéma pour activer POSIX sur un utilisateur."""
    
    uid_number: Optional[int] = Field(
        default=None,
        ge=1000,
        le=65534,
        alias="uidNumber",
        description="UID number (auto-allocated if null)",
    )
    
    @field_validator("home_directory", mode="before")
    @classmethod
    def default_home_directory(cls, v, info):
        """Génère le home directory par défaut si non fourni."""
        if v is None and "uid" in info.data:
            return f"/home/{info.data['uid']}"
        return v


class PosixAccountRead(PosixAccountBase):
    """Schéma de lecture POSIX."""
    
    uid_number: int = Field(..., alias="uidNumber")
    shadow_last_change: Optional[int] = Field(None, alias="shadowLastChange")
    shadow_min: Optional[int] = Field(None, alias="shadowMin")
    shadow_max: Optional[int] = Field(None, alias="shadowMax")
    shadow_warning: Optional[int] = Field(None, alias="shadowWarning")
    shadow_inactive: Optional[int] = Field(None, alias="shadowInactive")
    shadow_expire: Optional[int] = Field(None, alias="shadowExpire")
    
    class Config:
        populate_by_name = True


class PosixAccountUpdate(BaseModel):
    """Schéma de mise à jour (tous champs optionnels)."""
    
    gid_number: Optional[int] = Field(None, alias="gidNumber")
    home_directory: Optional[str] = Field(None, alias="homeDirectory")
    login_shell: Optional[str] = Field(None, alias="loginShell")
    gecos: Optional[str] = None


# === POSIX Group ===

class PosixGroupCreate(BaseModel):
    """Schéma pour activer POSIX sur un groupe."""
    
    gid_number: Optional[int] = Field(
        default=None,
        ge=1000,
        le=65534,
        alias="gidNumber",
        description="GID number (auto-allocated if null)",
    )


class PosixGroupRead(BaseModel):
    """Schéma de lecture POSIX groupe."""
    
    gid_number: int = Field(..., alias="gidNumber")
    member_uid: list[str] = Field(default_factory=list, alias="memberUid")
    
    class Config:
        populate_by_name = True


class PosixGroupUpdate(BaseModel):
    """Mise à jour POSIX groupe."""
    
    member_uid: Optional[list[str]] = Field(None, alias="memberUid")
```

---

## 4. Service du Plugin

### 4.1 Structure

```python
# heracles-plugins/posix/service.py

from typing import Optional
from heracles_api.plugins.base import TabService
from heracles_api.services.ldap_service import LdapService
from heracles_api.core.exceptions import ValidationError

from .schemas import PosixAccountCreate, PosixAccountRead, PosixAccountUpdate


class PosixService(TabService):
    """Service de gestion des comptes POSIX."""
    
    # ObjectClasses à ajouter lors de l'activation
    OBJECT_CLASSES = ["posixAccount", "shadowAccount"]
    
    # Attributs gérés par ce plugin
    MANAGED_ATTRIBUTES = [
        "uidNumber", "gidNumber", "homeDirectory", "loginShell", "gecos",
        "shadowLastChange", "shadowMin", "shadowMax", "shadowWarning",
        "shadowInactive", "shadowExpire",
    ]
    
    def __init__(self, ldap_service: LdapService, config: dict):
        super().__init__(ldap_service, config)
        self._uid_min = config.get("posix_uid_min", 10000)
        self._uid_max = config.get("posix_uid_max", 60000)
    
    async def is_active(self, dn: str) -> bool:
        """Vérifie si POSIX est activé sur l'objet."""
        entry = await self._ldap.get_entry(dn, ["objectClass"])
        return "posixAccount" in entry.get("objectClass", [])
    
    async def read(self, dn: str) -> Optional[PosixAccountRead]:
        """Lit les attributs POSIX d'un utilisateur."""
        if not await self.is_active(dn):
            return None
        
        entry = await self._ldap.get_entry(dn, self.MANAGED_ATTRIBUTES)
        return PosixAccountRead(
            uidNumber=int(entry["uidNumber"][0]),
            gidNumber=int(entry["gidNumber"][0]),
            homeDirectory=entry["homeDirectory"][0],
            loginShell=entry.get("loginShell", ["/bin/bash"])[0],
            gecos=entry.get("gecos", [None])[0],
            shadowLastChange=self._get_int(entry, "shadowLastChange"),
            shadowMin=self._get_int(entry, "shadowMin"),
            shadowMax=self._get_int(entry, "shadowMax"),
            shadowWarning=self._get_int(entry, "shadowWarning"),
            shadowInactive=self._get_int(entry, "shadowInactive"),
            shadowExpire=self._get_int(entry, "shadowExpire"),
        )
    
    async def activate(self, dn: str, data: PosixAccountCreate) -> PosixAccountRead:
        """Active POSIX sur un utilisateur."""
        if await self.is_active(dn):
            raise ValidationError("POSIX is already active on this user")
        
        # Allocation automatique de l'UID si non fourni
        uid_number = data.uid_number
        if uid_number is None:
            uid_number = await self._allocate_uid_number()
        
        # Vérification unicité
        if await self._uid_exists(uid_number):
            raise ValidationError(f"UID {uid_number} is already in use")
        
        # Vérification que le GID existe
        if not await self._gid_exists(data.gid_number):
            raise ValidationError(f"GID {data.gid_number} does not exist")
        
        # Construction des modifications LDAP
        changes = [
            ("add", "objectClass", self.OBJECT_CLASSES),
            ("add", "uidNumber", [str(uid_number)]),
            ("add", "gidNumber", [str(data.gid_number)]),
            ("add", "homeDirectory", [data.home_directory]),
            ("add", "loginShell", [data.login_shell]),
        ]
        
        if data.gecos:
            changes.append(("add", "gecos", [data.gecos]))
        
        # Initialisation shadow
        import time
        shadow_last_change = int(time.time() / 86400)
        changes.append(("add", "shadowLastChange", [str(shadow_last_change)]))
        changes.append(("add", "shadowMax", ["99999"]))
        
        await self._ldap.modify(dn, changes)
        
        return await self.read(dn)
    
    async def update(self, dn: str, data: PosixAccountUpdate) -> PosixAccountRead:
        """Met à jour les attributs POSIX."""
        if not await self.is_active(dn):
            raise ValidationError("POSIX is not active on this user")
        
        changes = []
        
        if data.gid_number is not None:
            if not await self._gid_exists(data.gid_number):
                raise ValidationError(f"GID {data.gid_number} does not exist")
            changes.append(("replace", "gidNumber", [str(data.gid_number)]))
        
        if data.home_directory is not None:
            changes.append(("replace", "homeDirectory", [data.home_directory]))
        
        if data.login_shell is not None:
            changes.append(("replace", "loginShell", [data.login_shell]))
        
        if data.gecos is not None:
            changes.append(("replace", "gecos", [data.gecos]))
        
        if changes:
            await self._ldap.modify(dn, changes)
        
        return await self.read(dn)
    
    async def deactivate(self, dn: str) -> None:
        """Désactive POSIX sur un utilisateur."""
        if not await self.is_active(dn):
            raise ValidationError("POSIX is not active on this user")
        
        # Suppression des objectClasses et attributs
        changes = [
            ("delete", "objectClass", self.OBJECT_CLASSES),
        ]
        
        # Suppression des attributs gérés
        for attr in self.MANAGED_ATTRIBUTES:
            changes.append(("delete", attr, []))
        
        await self._ldap.modify(dn, changes)
    
    # === Méthodes privées ===
    
    async def _allocate_uid_number(self) -> int:
        """Alloue un nouveau UID number."""
        # Utilise PostgreSQL pour allocation atomique
        async with self._db.transaction():
            result = await self._db.execute(
                """
                UPDATE heracles_uid_allocations 
                SET next_value = next_value + 1 
                WHERE type = 'uid' AND next_value < max_value
                RETURNING next_value - 1
                """
            )
            row = await result.fetchone()
            if not row:
                raise ValidationError("No available UID numbers")
            return row[0]
    
    async def _uid_exists(self, uid_number: int) -> bool:
        """Vérifie si un UID est déjà utilisé."""
        result = await self._ldap.search(
            f"(uidNumber={uid_number})",
            attributes=["dn"],
            size_limit=1,
        )
        return len(result) > 0
    
    async def _gid_exists(self, gid_number: int) -> bool:
        """Vérifie si un GID existe."""
        result = await self._ldap.search(
            f"(gidNumber={gid_number})",
            base_dn=self._config["group_base_dn"],
            attributes=["dn"],
            size_limit=1,
        )
        return len(result) > 0
    
    def _get_int(self, entry: dict, attr: str) -> Optional[int]:
        """Extrait un entier d'une entrée LDAP."""
        val = entry.get(attr, [None])[0]
        return int(val) if val is not None else None
```

---

## 5. Schéma de Formulaire UI

### 5.1 Format JSON Schema

```json
{
  "$schema": "https://heracles.example.com/schemas/form-schema-v1.json",
  "id": "posix",
  "version": "1.0.0",
  "title": "Unix Account",
  "description": "POSIX/Unix account settings",
  "icon": "terminal",
  
  "activation": {
    "label": "Enable Unix account",
    "description": "Add POSIX attributes to this user for Unix/Linux access"
  },
  
  "sections": [
    {
      "id": "main",
      "title": "Account Settings",
      "fields": [
        {
          "name": "uidNumber",
          "type": "number",
          "label": "UID Number",
          "description": "Unix user ID (auto-allocated if empty)",
          "required": false,
          "readonly_after_create": true,
          "min": 1000,
          "max": 65534,
          "placeholder": "Auto"
        },
        {
          "name": "gidNumber",
          "type": "group_select",
          "label": "Primary Group",
          "description": "Primary Unix group",
          "required": true,
          "filter": "(objectClass=posixGroup)"
        },
        {
          "name": "homeDirectory",
          "type": "string",
          "label": "Home Directory",
          "description": "User home directory path",
          "required": true,
          "pattern": "^/[\\w/.-]+$",
          "default_template": "/home/{uid}"
        },
        {
          "name": "loginShell",
          "type": "select",
          "label": "Login Shell",
          "description": "Default shell for the user",
          "required": false,
          "default": "/bin/bash",
          "options": [
            {"value": "/bin/bash", "label": "Bash"},
            {"value": "/bin/zsh", "label": "Zsh"},
            {"value": "/bin/sh", "label": "Sh"},
            {"value": "/usr/sbin/nologin", "label": "No Login"},
            {"value": "/bin/false", "label": "False (disabled)"}
          ]
        }
      ]
    },
    {
      "id": "gecos",
      "title": "Additional Info",
      "collapsed": true,
      "fields": [
        {
          "name": "gecos",
          "type": "string",
          "label": "GECOS",
          "description": "General information (usually full name)",
          "required": false,
          "default_template": "{cn}"
        }
      ]
    }
  ],
  
  "validation": {
    "rules": [
      {
        "type": "unique",
        "field": "uidNumber",
        "scope": "global",
        "message": "This UID is already in use"
      }
    ]
  }
}
```

### 5.2 Types de Champs Supportés

| Type | Description | Props spécifiques |
|------|-------------|-------------------|
| `string` | Texte simple | `pattern`, `minLength`, `maxLength` |
| `number` | Nombre entier | `min`, `max`, `step` |
| `boolean` | Case à cocher | - |
| `select` | Liste déroulante | `options`, `multiple` |
| `textarea` | Texte multiligne | `rows` |
| `password` | Mot de passe | `strength_meter` |
| `email` | Email | - |
| `date` | Date | `format` |
| `group_select` | Sélection de groupe LDAP | `filter` |
| `user_select` | Sélection d'utilisateur LDAP | `filter` |
| `dn_select` | Sélection de DN | `base_dn`, `filter` |
| `ssh_key` | Clé SSH publique | `multiple` |

---

## 6. Enregistrement du Plugin

### 6.1 Point d'Entrée

```python
# heracles-plugins/posix/__init__.py

from .plugin import PosixPlugin

# Le plugin est automatiquement découvert par ce export
__plugin__ = PosixPlugin
```

### 6.2 Configuration (heracles.yaml)

```yaml
plugins:
  enabled:
    - core
    - posix
    - sudo
    - ssh
  
  config:
    posix:
      uid_min: 10000
      uid_max: 60000
      default_shell: /bin/bash
      default_home_base: /home
```

### 6.3 Découverte Automatique

```python
# heracles-api/app/plugins/loader.py

import importlib
import pkgutil
from pathlib import Path
from typing import List, Type

from .base import Plugin


def discover_plugins(plugins_path: Path) -> List[Type[Plugin]]:
    """
    Découvre tous les plugins disponibles.
    
    Args:
        plugins_path: Chemin vers le dossier des plugins
        
    Returns:
        Liste des classes de plugins trouvées
    """
    plugins = []
    
    for finder, name, ispkg in pkgutil.iter_modules([str(plugins_path)]):
        if not ispkg:
            continue
        
        try:
            module = importlib.import_module(f"heracles_plugins.{name}")
            if hasattr(module, "__plugin__"):
                plugin_class = module.__plugin__
                if issubclass(plugin_class, Plugin):
                    plugins.append(plugin_class)
        except ImportError as e:
            logger.warning(f"Failed to load plugin {name}: {e}")
    
    return plugins


def load_enabled_plugins(
    config: dict,
    plugins_path: Path,
) -> List[Plugin]:
    """
    Charge et instancie les plugins activés.
    
    Args:
        config: Configuration de l'application
        plugins_path: Chemin vers les plugins
        
    Returns:
        Liste des instances de plugins activés
    """
    enabled = config.get("plugins", {}).get("enabled", [])
    plugin_configs = config.get("plugins", {}).get("config", {})
    
    available = {p.info().name: p for p in discover_plugins(plugins_path)}
    loaded = []
    
    for name in enabled:
        if name not in available:
            raise ValueError(f"Plugin '{name}' not found")
        
        plugin_class = available[name]
        info = plugin_class.info()
        
        # Vérification des dépendances
        for dep in info.dependencies:
            if dep not in enabled:
                raise ValueError(
                    f"Plugin '{name}' requires '{dep}' which is not enabled"
                )
        
        # Instanciation
        plugin_config = plugin_configs.get(name, {})
        instance = plugin_class(plugin_config)
        instance.on_activate()
        loaded.append(instance)
    
    return loaded
```

---

## 7. Plugins Essentiels - Spécifications

### 7.1 Plugin Core

| Aspect | Valeur |
|--------|--------|
| **Nom** | `core` |
| **ObjectClasses** | `inetOrgPerson`, `organizationalUnit`, `groupOfNames` |
| **Dépendances** | Aucune |
| **Onglets** | `personal` (user), `info` (group) |

### 7.2 Plugin POSIX

| Aspect | Valeur |
|--------|--------|
| **Nom** | `posix` |
| **ObjectClasses** | `posixAccount`, `shadowAccount`, `posixGroup` |
| **Dépendances** | `core` |
| **Onglets** | `posix` (user), `posix` (group) |

### 7.3 Plugin Sudo

| Aspect | Valeur |
|--------|--------|
| **Nom** | `sudo` |
| **ObjectClasses** | `sudoRole` |
| **Dépendances** | `core`, `posix` |
| **Type** | Management (nouveau type d'objet) |

### 7.4 Plugin SSH

| Aspect | Valeur |
|--------|--------|
| **Nom** | `ssh` |
| **ObjectClasses** | `ldapPublicKey` |
| **Dépendances** | `core` |
| **Onglets** | `ssh` (user) |

### 7.5 Plugin Systems

| Aspect | Valeur |
|--------|--------|
| **Nom** | `systems` |
| **ObjectClasses** | `fdServer`, `fdWorkstation`, `fdTerminal`, `ipHost`, `ieee802Device` |
| **Dépendances** | `core` |
| **Type** | Management |

### 7.6 Plugin DNS

| Aspect | Valeur |
|--------|--------|
| **Nom** | `dns` |
| **ObjectClasses** | `dNSZone`, `dNSRRset` |
| **Dépendances** | `core`, `systems` |
| **Type** | Management |

### 7.7 Plugin DHCP

| Aspect | Valeur |
|--------|--------|
| **Nom** | `dhcp` |
| **ObjectClasses** | `dhcpServer`, `dhcpSubnet`, `dhcpHost` |
| **Dépendances** | `core`, `systems` |
| **Type** | Management |
