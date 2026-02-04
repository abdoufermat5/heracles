# Versioning Strategy

> **Référence**: Ce document définit la stratégie de versioning pour tous les composants Heracles.
> **Mise à jour**: 4 Février 2026
> **Statut**: Actif

---

## 1. Vue d'Ensemble

Heracles utilise un système de **versioning indépendant par composant** suivant [Semantic Versioning 2.0.0](https://semver.org/). Chaque composant majeur a son propre cycle de version tout en maintenant une matrice de compatibilité documentée.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        COMPOSANTS HERACLES                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   heracles-core (Rust)         heracles-api (Python)                        │
│   ├── Version: 0.1.0           ├── Version: 0.8.0-beta                      │
│   ├── Cycle: Stable            ├── Cycle: Fast                              │
│   └── PyO3: __version__        └── __init__.py: __version__                 │
│                                                                              │
│   heracles-ui (TypeScript)     heracles-plugins (Python)                    │
│   ├── Version: 0.8.0-beta      ├── Package: 0.8.0-beta                      │
│   ├── Cycle: Fast              └── Plugins: 1.0.0 (individuels)             │
│   └── package.json: version                                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Format de Version

### 2.1 Schema SemVer

```
MAJOR.MINOR.PATCH[-PRERELEASE]

Exemples:
  0.8.0-alpha    # Alpha release
  0.8.0-beta     # Beta release  
  0.8.0-rc.1     # Release candidate 1
  0.8.0          # Stable release
  1.0.0          # First major stable
```

### 2.2 Signification des Numéros

| Segment | Incrémenté quand... | Exemple |
|---------|---------------------|---------|
| **MAJOR** | Changements cassants (breaking changes) | `0.x.x` → `1.0.0` |
| **MINOR** | Nouvelles fonctionnalités rétrocompatibles | `0.8.0` → `0.9.0` |
| **PATCH** | Corrections de bugs rétrocompatibles | `0.8.0` → `0.8.1` |
| **PRERELEASE** | Indique la stabilité | `-alpha`, `-beta`, `-rc.1` |

### 2.3 Suffixes Pre-release

| Suffixe | Signification | Critères |
|---------|---------------|----------|
| `-alpha` | Fonctionnalité basique, instable | Tests unitaires passent |
| `-beta` | Fonctionnalité complète, tests OK | Tests d'intégration passent |
| `-rc.N` | Release candidate N | E2E tests, audit sécurité |
| *(aucun)* | Stable | RC validé, aucun bug critique |

---

## 3. Versions par Composant

### 3.1 heracles-core (Rust)

**Fichier**: `heracles-core/Cargo.toml`  
**Export Python**: `heracles_core.__version__`

```toml
[package]
version = "0.1.0"
```

**Politique**:
- Version **stable et lente** - la bibliothèque core change rarement
- MAJOR bump = changement dans l'API PyO3 exposée
- MINOR bump = nouvelles fonctions exportées
- PATCH bump = corrections internes

### 3.2 heracles-api (Python/FastAPI)

**Fichier**: `heracles-api/heracles_api/__init__.py`  
**Export**: `heracles_api.__version__`

```python
__version__ = "0.8.0-beta"
```

**Politique**:
- Version **rapide** - suit les sprints de développement
- MAJOR bump = changement cassant dans l'API REST
- MINOR bump = nouveaux endpoints, fonctionnalités
- PATCH bump = corrections de bugs

### 3.3 heracles-ui (React/TypeScript)

**Fichier**: `heracles-ui/package.json`

```json
{
  "version": "0.8.0-beta"
}
```

**Politique**:
- Version **alignée avec l'API** (même MAJOR.MINOR recommandé)
- Vérification de compatibilité au démarrage

### 3.4 heracles-plugins (Package Python)

**Fichier**: `heracles_plugins/pyproject.toml`

```toml
[project]
version = "0.8.0-beta"
```

**Plugins individuels**: Chaque plugin déclare sa propre version dans `PluginInfo`:

```python
PluginInfo(
    name="posix",
    version="1.0.0",  # Version du plugin
    minimum_api_version="0.8.0",  # API minimum requise
)
```

---

## 4. Matrice de Compatibilité

### 4.1 Tableau de Compatibilité

| heracles-api | heracles-core | heracles-ui | heracles-plugins |
|--------------|---------------|-------------|------------------|
| 0.8.x-beta   | ≥ 0.1.0       | 0.8.x-beta  | ≥ 0.8.0-beta     |
| 0.9.x-beta   | ≥ 0.1.0       | 0.9.x-beta  | ≥ 0.8.0-beta     |
| 1.0.x        | ≥ 0.2.0       | 1.0.x       | ≥ 1.0.0          |

### 4.2 Contraintes Inter-Composants

```
heracles-core ──────┐
    │               │ (dépendance compilée)
    ▼               │
heracles-api ◀──────┘
    │
    ├──── heracles-ui (HTTP REST, vérifie /api/v1/version)
    │
    └──── heracles-plugins
              │
              └── PluginInfo.minimum_api_version
```

### 4.3 Endpoint de Version

L'API expose `/api/v1/version` pour permettre la vérification de compatibilité:

```json
{
  "api": "0.8.0-beta",
  "core": "0.1.0",
  "plugins_package": "0.8.0-beta",
  "plugins": [
    {"name": "posix", "version": "1.0.0", "minimum_api_version": "0.8.0"},
    {"name": "sudo", "version": "1.0.0", "minimum_api_version": "0.8.0"}
  ],
  "supported_api_versions": ["v1"]
}
```

---

## 5. Commandes Make

### 5.1 Affichage des Versions

```bash
make version        # Affiche toutes les versions
make version-api    # Affiche uniquement la version API
make version-ui     # Affiche uniquement la version UI
```

### 5.2 Bump de Version

```bash
# Composant individuel
make bump-api-patch      # 0.8.0-beta → 0.8.1-beta
make bump-api-minor      # 0.8.0-beta → 0.9.0-beta
make bump-api-major      # 0.8.0-beta → 1.0.0

# Tous les composants
make bump-all-patch      # Bump patch sur api, ui, plugins
make bump-all-minor      # Bump minor sur api, ui, plugins
make bump-all-major      # Bump major sur tous (retire -beta)
```

### 5.3 Release

```bash
make release-validate    # Vérifie que les versions sont valides
make release-prep        # Prépare la release (met à jour dates CHANGELOG)
make tag-release         # Crée les tags Git pour tous les composants
```

---

## 6. Tags Git

### 6.1 Format des Tags

```
<composant>/v<version>

Exemples:
  heracles-api/v0.8.0-beta
  heracles-ui/v0.8.0-beta
  heracles-core/v0.1.0
  heracles-plugins/v0.8.0-beta
```

### 6.2 Création des Tags

```bash
# Tag automatique pour tous les composants
make tag-release

# Tag manuel pour un composant
git tag -a "heracles-api/v0.8.1-beta" -m "Release heracles-api v0.8.1-beta"
git push origin "heracles-api/v0.8.1-beta"
```

---

## 7. CHANGELOG

Chaque composant maintient son propre CHANGELOG au format [Keep a Changelog](https://keepachangelog.com/):

```
heracles-core/CHANGELOG.md
heracles-api/CHANGELOG.md
heracles-ui/CHANGELOG.md
heracles_plugins/CHANGELOG.md
```

### 7.1 Format des Entrées

```markdown
## [0.8.1-beta] - 2026-02-15

### Added
- Nouvelle fonctionnalité X

### Changed
- Modification du comportement Y

### Fixed
- Correction du bug Z

### Security
- Correctif de sécurité W
```

### 7.2 Catégories

| Catégorie | Usage |
|-----------|-------|
| **Added** | Nouvelles fonctionnalités |
| **Changed** | Changements de fonctionnalités existantes |
| **Deprecated** | Fonctionnalités qui seront supprimées |
| **Removed** | Fonctionnalités supprimées |
| **Fixed** | Corrections de bugs |
| **Security** | Corrections de sécurité |

---

## 8. Processus de Release

### 8.1 Pre-release (alpha/beta)

1. Développement dans une branche feature
2. Tests passants
3. Merge vers `main`
4. Bump de version: `make bump-api-patch`
5. Commit: `git commit -am "chore(api): bump version to 0.8.1-beta"`
6. Tag: `make tag-release`
7. Push: `git push && git push --tags`

### 8.2 Release Stable

1. Vérifier que tous les tests passent
2. Audit de sécurité
3. Retirer le suffixe beta: `make bump-all-major`
4. Mettre à jour CHANGELOGs: `make release-prep`
5. Commit: `git commit -am "chore: release v1.0.0"`
6. Tag: `make tag-release`
7. Push: `git push && git push --tags`
8. Créer les releases GitHub

---

## 9. Vérification de Compatibilité

### 9.1 Côté API (Plugin Loading)

```python
# heracles_api/plugins/loader.py
def validate_plugin_compatibility(plugin: Plugin) -> bool:
    from packaging import version
    from heracles_api import __version__
    
    info = plugin.info()
    if info.minimum_api_version:
        api_ver = version.parse(__version__.split("-")[0])
        min_ver = version.parse(info.minimum_api_version)
        if api_ver < min_ver:
            logger.warning(
                "plugin_incompatible",
                plugin=info.name,
                requires=info.minimum_api_version,
                current=__version__,
            )
            return False
    return True
```

### 9.2 Côté UI (Startup Check)

L'UI vérifie la compatibilité au démarrage via `/api/v1/version/compatibility`:

```typescript
// src/hooks/useVersionCheck.ts
const checkCompatibility = async () => {
  const response = await fetch(`${API_BASE}/version/compatibility?client_version=${APP_VERSION}&client_type=ui`);
  const data = await response.json();
  
  if (!data.compatible) {
    showWarning(`Version mismatch: UI ${APP_VERSION} may not be compatible with API ${data.api_version}`);
  }
};
```

---

## 10. FAQ

### Q: Quand bumper la version MAJOR ?
**R**: Uniquement lors de changements cassants (breaking changes) comme la suppression d'endpoints API ou la modification de la structure des réponses.

### Q: Les plugins doivent-ils suivre la version de l'API ?
**R**: Non. Les plugins ont leur propre versioning (actuellement tous à 1.0.0 car feature-complete). Ils déclarent `minimum_api_version` pour la compatibilité.

### Q: Comment gérer une correction de bug urgente ?
**R**: Bump patch, commit, tag, push. Exemple: `make bump-api-patch && git commit -am "fix(api): critical bug" && make tag-release && git push --tags`

### Q: Quelle version pour une nouvelle fonctionnalité ?
**R**: Bump minor. Exemple: `make bump-api-minor`
