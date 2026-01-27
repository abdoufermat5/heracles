# HERACLES - Project Charter

> **Version**: 1.0.0
> **Date**: 2026-01-17
> **Status**: ACTIVE - Ce document est la source de vérité pour le projet

---

## 1. Vision du Projet

**Heracles** est un système moderne de gestion d'identités LDAP. L'objectif est de créer une solution performante, maintenable et extensible tout en **garantissant une compatibilité totale** avec les déploiements LDAP existants.

### 1.1 Principes Fondamentaux

| Principe | Description | Priorité |
|----------|-------------|----------|
| **Compatibilité LDAP** | Les schémas LDAP standards doivent fonctionner sans modification | CRITIQUE |
| **API-First** | Toute fonctionnalité expose une API REST avant toute UI | HAUTE |
| **Simplicité** | Single-tenant, pas de sur-ingénierie | HAUTE |
| **Testabilité** | Code testable, coverage > 80% | HAUTE |
| **Documentation** | Tout code doit être documenté | MOYENNE |

### 1.2 Ce que Heracles N'EST PAS

- ❌ Une solution multi-tenant/SaaS (pour le moment)
- ❌ Un remplacement des 60+ plugins existants (seulement les essentiels)
- ❌ Un système de base de données relationnelle (LDAP reste la source de vérité)

---

## 2. Stack Technologique

### 2.1 Stack Obligatoire

| Composant | Technologie | Version Min | Justification |
|-----------|-------------|-------------|---------------|
| **Core Library** | Rust | 1.75+ | Performance, sécurité mémoire |
| **API Backend** | Python + FastAPI | 3.11+ / 0.100+ | Productivité, écosystème |
| **Frontend** | React + TypeScript | 18+ / 5+ | Composants, typage |
| **Base de données** | PostgreSQL | 15+ | Config, audit, jobs |
| **Cache/Sessions** | Redis | 7+ | Performance |
| **Directory** | LDAP (OpenLDAP/389DS) | - | Compatibilité FD |

### 2.2 Dépendances Autorisées

#### Rust
- `ldap3` - Client LDAP
- `argon2`, `bcrypt`, `sha2` - Hashing
- `pyo3` - Bindings Python
- `serde`, `serde_json` - Serialization
- `tokio` - Async runtime

#### Python
- `fastapi`, `uvicorn` - API
- `pydantic` - Validation
- `sqlalchemy` - ORM PostgreSQL
- `redis`, `aioredis` - Cache
- `celery` - Tasks async
- `python-jose` - JWT
- `passlib` - Passwords
- `strawberry-graphql` - GraphQL (optionnel)

#### React
- `@tanstack/react-query` - Data fetching
- `zustand` - State management
- `react-hook-form` - Forms
- `zod` - Validation
- `@radix-ui/*` ou `shadcn/ui` - Components
- `tailwindcss` - Styling

### 2.3 Dépendances INTERDITES

- ❌ Django, Flask (utiliser FastAPI)
- ❌ Redux (utiliser Zustand)
- ❌ Axios (utiliser fetch natif ou @tanstack/query)
- ❌ MongoDB, MySQL (utiliser PostgreSQL)
- ❌ Electron, Tauri (web only)

---

## 3. Contraintes Architecturales

### 3.1 Règle d'Or: Compatibilité LDAP

```
TOUTE entrée LDAP créée/modifiée par Heracles DOIT être lisible 
et modifiable par les outils LDAP standards, et vice-versa.
```

Implications:
- Utiliser les mêmes objectClasses que FD
- Utiliser les mêmes attributs LDAP
- Respecter les DNs et la structure d'arbre
- Ne pas créer de nouveaux schémas LDAP propriétaires

### 3.2 Architecture en Couches

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                      │
│         Ne communique QU'avec l'API Gateway              │
└─────────────────────────────────────────────────────────┘
                           │ HTTP/WS
                           ▼
┌─────────────────────────────────────────────────────────┐
│                  API GATEWAY (FastAPI)                   │
│    - Authentification/Autorisation                       │
│    - Validation des entrées                              │
│    - Rate limiting                                       │
│    - Logging des requêtes                                │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                 SERVICES (Python)                        │
│    - Logique métier                                      │
│    - Orchestration                                       │
│    - Plugins                                             │
└─────────────────────────────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │  LDAP    │ │PostgreSQL│ │  Redis   │
        │(identité)│ │ (config) │ │ (cache)  │
        └──────────┘ └──────────┘ └──────────┘
```

### 3.3 Règles de Communication

| Source | Destination | Autorisé | Méthode |
|--------|-------------|----------|---------|
| Frontend | API Gateway | ✅ | HTTP REST, WebSocket |
| Frontend | Services | ❌ | - |
| Frontend | LDAP/DB | ❌ | - |
| API Gateway | Services | ✅ | Appel direct Python |
| Services | LDAP | ✅ | Via heracles-core (Rust) |
| Services | PostgreSQL | ✅ | Via SQLAlchemy |
| Services | Redis | ✅ | Via aioredis |

---

## 4. Plugins Essentiels (Scope Initial)

### 4.1 Plugins à Implémenter (Phase 1-3)

| Plugin | Priorité | Dépendances | ObjectClasses |
|--------|----------|-------------|---------------|
| **core** | P0 | - | inetOrgPerson, organizationalUnit |
| **posix** | P0 | core | posixAccount, shadowAccount, posixGroup |
| **personal** | P1 | core | - (attributs inetOrgPerson) |
| **password** | P0 | core | - (userPassword) |
| **groups** | P0 | core | groupOfNames, posixGroup |
| **acl** | P0 | core | gosaAcl, gosaRole |
| **sudo** | P1 | posix | sudoRole |
| **ssh** | P1 | posix | ldapPublicKey |
| **systems** | P2 | core | hrcServer, hrcWorkstation |
| **dns** | P2 | systems | dNSZone, dNSRRset |
| **dhcp** | P2 | systems | dhcpServer, dhcpSubnet |

### 4.2 Plugins HORS SCOPE (v1.0)

Les plugins suivants ne seront PAS implémentés dans la version initiale:
- mail, postfix, dovecot, cyrus, zimbra, sogo
- samba
- supann, schac, renater-partage
- freeradius, kerberos
- certificates, ejbca, gpg
- webauthn (2FA)
- nextcloud
- Tous les plugins "workflow" (invitations, lifecycle, etc.)

---

## 5. Références Documentaires

| Document | Chemin | Description |
|----------|--------|-------------|
| Architecture | `docs/01-ARCHITECTURE.md` | Détails techniques de l'architecture |
| API Spec | `docs/02-API-SPECIFICATION.md` | Contrat d'API REST |
| Data Model | `docs/03-DATA-MODEL.md` | Schémas LDAP et PostgreSQL |
| Coding Rules | `docs/04-CODING-RULES.md` | Standards de code |
| Plugin Spec | `docs/05-PLUGIN-SPECIFICATION.md` | Comment créer un plugin |
| Security | `docs/06-SECURITY.md` | Règles de sécurité |
| Roadmap | `docs/07-ROADMAP.md` | Planning détaillé |

---

## 6. Définition de "Done"

Une fonctionnalité est considérée comme terminée si:

- [ ] Tests unitaires écrits et passants (coverage > 80%)
- [ ] Tests d'intégration avec LDAP réel
- [ ] Documentation API (OpenAPI/Swagger)
- [ ] Documentation utilisateur si UI
- [ ] Revue de code effectuée
- [ ] Pas de régression sur les tests existants
- [ ] Compatible avec les déploiements LDAP existants (test de coexistence)
