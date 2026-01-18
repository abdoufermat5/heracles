# HERACLES - Roadmap

> **Référence**: Ce document définit le planning de développement d'Heracles.
> **Mise à jour**: 18 Janvier 2026
> **Statut**: Phase 1 Sprint 1-2 ✅ TERMINÉ

---

## 1. Vue d'Ensemble

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           HERACLES ROADMAP                                    │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  Q1 2026          Q2 2026          Q3 2026          Q4 2026          2027    │
│  ────────         ────────         ────────         ────────         ────    │
│                                                                               │
│  ┌─────────┐      ┌─────────┐      ┌─────────┐      ┌─────────┐             │
│  │ PHASE 1 │─────▶│ PHASE 2 │─────▶│ PHASE 3 │─────▶│ PHASE 4 │─────▶ ...   │
│  │Foundation│      │  Core   │      │ Plugins │      │Advanced │             │
│  │   MVP   │      │Identity │      │  Infra  │      │Features │             │
│  └─────────┘      └─────────┘      └─────────┘      └─────────┘             │
│                                                                               │
│  v0.1.0           v0.5.0           v0.8.0           v1.0.0                   │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Phase 1: Foundation (Q1 2026)

**Objectif**: Infrastructure de base et authentification fonctionnelle.

**Durée**: 12 semaines

### 2.1 Sprint 1-2: Setup & Core Rust (4 semaines) ✅ TERMINÉ

| Tâche | Priorité | Estimation | Statut |
|-------|----------|------------|--------|
| Setup monorepo | P0 | 2j | ✅ Terminé |
| heracles-core: connexion LDAP | P0 | 5j | ✅ Terminé (pool deadpool) |
| heracles-core: opérations LDAP | P0 | 5j | ✅ Terminé (search, add, modify, delete) |
| heracles-core: password hashing | P0 | 3j | ✅ Terminé (SSHA, Argon2, bcrypt, SHA-256/512, MD5) |
| heracles-core: PyO3 bindings | P0 | 3j | ✅ Terminé |
| Tests unitaires Rust | P0 | 2j | ✅ Terminé (57 tests, 100% pass) |
| Docker Compose infrastructure | P0 | 2j | ✅ Terminé (LDAP, PostgreSQL, Redis) |
| heracles-api skeleton | P1 | 2j | ✅ Terminé (FastAPI structure) |

**Livrable**: `heracles-core v0.1.0` (crate Rust) ✅

### 2.2 Sprint 3-4: API Foundation (4 semaines) 🔄 EN COURS

| Tâche | Priorité | Estimation | Statut |
|-------|----------|------------|--------|
| Setup FastAPI | P0 | 1j | ✅ Structure créée |
| Modèles Pydantic de base | P0 | 2j | ✅ User, Group schemas |
| Service LDAP (Python wrapper) | P0 | 3j | 🔲 À faire |
| Endpoint `/auth/login` | P0 | 3j | 🔲 Skeleton créé |
| Endpoint `/auth/logout` | P0 | 1j | 🔲 Skeleton créé |
| Endpoint `/auth/me` | P0 | 1j | 🔲 Skeleton créé |
| Middleware auth | P0 | 2j | 🔲 À faire |
| Setup PostgreSQL + migrations | P1 | 2j | ✅ Schema init.sql créé |
| Configuration management | P1 | 2j | ✅ pydantic-settings |
| Tests API | P0 | 3j | 🔲 À faire |

**Livrable**: `heracles-api v0.1.0` (auth fonctionnelle)

### 2.3 Sprint 5-6: UI Foundation (4 semaines)

| Tâche | Priorité | Estimation | Critères d'acceptation |
|-------|----------|------------|------------------------|
| Setup React + Vite | P0 | 1j | TypeScript strict |
| Setup TailwindCSS + shadcn/ui | P0 | 1j | Composants de base |
| Layout principal | P0 | 2j | Header, Sidebar, Content |
| Page login | P0 | 2j | Form fonctionnel |
| Auth context + hooks | P0 | 2j | Gestion JWT |
| React Query setup | P0 | 1j | Client API configuré |
| Route protection | P0 | 1j | Redirect si non auth |
| Page dashboard (placeholder) | P1 | 1j | Message de bienvenue |
| Tests React | P1 | 2j | Vitest, composants critiques |
| Docker Compose dev | P0 | 2j | LDAP + PostgreSQL + Redis |

**Livrable**: `heracles-ui v0.1.0` (login fonctionnel)

### 2.4 Milestone Phase 1

```
✓ Connexion LDAP fonctionnelle
✓ Authentification JWT
✓ Login UI
✓ CI/CD basique
✓ Documentation développeur

Version: v0.1.0-alpha
```

---

## 3. Phase 2: Core Identity (Q2 2026)

**Objectif**: Gestion complète des utilisateurs et groupes.

**Durée**: 12 semaines

### 3.1 Sprint 7-8: User Management (4 semaines)

| Tâche | Priorité | Estimation | Critères d'acceptation |
|-------|----------|------------|------------------------|
| Plugin `core` (backend) | P0 | 3j | Structure plugin, registration |
| `GET /users` | P0 | 2j | Liste paginée, filtrable |
| `GET /users/{uid}` | P0 | 1j | Détail utilisateur |
| `POST /users` | P0 | 3j | Création avec validation |
| `PUT /users/{uid}` | P0 | 2j | Modification |
| `DELETE /users/{uid}` | P0 | 1j | Suppression |
| `PUT /users/{uid}/password` | P0 | 2j | Changement mot de passe |
| Lock/Unlock endpoints | P1 | 2j | Verrouillage compte |
| UI: Liste utilisateurs | P0 | 3j | DataTable, recherche |
| UI: Formulaire utilisateur | P0 | 4j | Create/Edit, validation |
| Tests E2E users | P0 | 2j | Cypress/Playwright |

**Livrable**: CRUD utilisateurs complet

### 3.2 Sprint 9-10: Groups & ACL (4 semaines)

| Tâche | Priorité | Estimation | Critères d'acceptation |
|-------|----------|------------|------------------------|
| `GET/POST/PUT/DELETE /groups` | P0 | 4j | CRUD groupes |
| Gestion membres groupes | P0 | 2j | Add/remove members |
| Service ACL | P0 | 5j | Vérification permissions |
| Lecture ACL depuis LDAP | P0 | 3j | Compatible FD gosaAcl |
| Endpoint `/acl/check` | P0 | 2j | Vérification permission |
| UI: Liste groupes | P0 | 2j | DataTable |
| UI: Formulaire groupe | P0 | 3j | Membres sélectionnables |
| Intégration ACL dans UI | P1 | 3j | Masquage selon droits |

**Livrable**: Gestion groupes + ACL fonctionnels

### 3.3 Sprint 11-12: POSIX Plugin (4 semaines)

| Tâche | Priorité | Estimation | Critères d'acceptation |
|-------|----------|------------|------------------------|
| Plugin `posix` backend | P0 | 5j | Activation/désactivation POSIX |
| Allocation UID/GID | P0 | 3j | Automatique, atomique |
| Schéma formulaire JSON | P0 | 2j | Pour génération UI |
| UI: Onglet POSIX user | P0 | 3j | Formulaire dynamique |
| UI: POSIX group | P0 | 2j | gidNumber, memberUid |
| Shadow account support | P1 | 2j | Expiration mot de passe |
| Tests compatibilité FD | P0 | 3j | Coexistence vérifiée |

**Livrable**: Plugin POSIX complet

### 3.4 Milestone Phase 2

```
✓ CRUD Users complet
✓ CRUD Groups complet
✓ Système ACL fonctionnel
✓ Plugin POSIX activable
✓ Compatibilité FusionDirectory vérifiée

Version: v0.5.0-beta
```

---

## 4. Phase 3: Infrastructure Plugins (Q3 2026)

**Objectif**: Plugins sudo, ssh, systems, dns, dhcp.

**Durée**: 12 semaines

### 4.1 Sprint 13-14: Sudo & SSH (4 semaines)

| Tâche | Priorité | Estimation | Critères d'acceptation |
|-------|----------|------------|------------------------|
| Plugin `sudo` backend | P0 | 5j | CRUD sudoRole |
| UI: Gestion règles sudo | P0 | 4j | Liste, formulaire |
| Plugin `ssh` backend | P0 | 3j | Gestion sshPublicKey |
| UI: Onglet SSH user | P0 | 3j | Ajout/suppression clés |
| Validation clés SSH | P0 | 2j | Format, fingerprint |
| Tests | P0 | 3j | Unitaires + intégration |

**Livrable**: Plugins sudo et ssh

### 4.2 Sprint 15-16: Systems (4 semaines)

| Tâche | Priorité | Estimation | Critères d'acceptation |
|-------|----------|------------|------------------------|
| Plugin `systems` backend | P0 | 5j | Server, Workstation, Terminal |
| Modèles fdServer, etc. | P0 | 3j | Compatibilité schémas FD |
| UI: Liste systèmes | P0 | 3j | Filtrage par type |
| UI: Formulaire système | P0 | 4j | IP, MAC, description |
| Intégration DNS/DHCP (prep) | P1 | 2j | Structure pour phase suivante |
| Tests | P0 | 3j | |

**Livrable**: Plugin systems

### 4.3 Sprint 17-18: DNS & DHCP (4 semaines)

| Tâche | Priorité | Estimation | Critères d'acceptation |
|-------|----------|------------|------------------------|
| Plugin `dns` backend | P0 | 5j | Zones, records |
| UI: Gestion DNS | P0 | 4j | Zones, A, AAAA, CNAME, MX |
| Plugin `dhcp` backend | P0 | 5j | Servers, subnets, hosts |
| UI: Gestion DHCP | P0 | 4j | Subnets, réservations |
| Tests | P0 | 2j | |

**Livrable**: Plugins dns et dhcp

### 4.4 Milestone Phase 3

```
✓ Plugin sudo (règles sudoers)
✓ Plugin ssh (clés publiques)
✓ Plugin systems (serveurs, workstations)
✓ Plugin dns (zones, records)
✓ Plugin dhcp (subnets, hosts)

Version: v0.8.0-beta
```

---

## 5. Phase 4: Advanced Features (Q4 2026)

**Objectif**: Audit, templates, API complète, stabilisation.

**Durée**: 12 semaines

### 5.1 Sprint 19-20: Audit & Logging (4 semaines)

| Tâche | Priorité | Estimation | Critères d'acceptation |
|-------|----------|------------|------------------------|
| Service audit | P0 | 4j | Logging PostgreSQL |
| Audit LDAP (optionnel) | P2 | 3j | Compatible fdAudit |
| Endpoint `/audit/logs` | P0 | 2j | Recherche, filtres |
| UI: Page audit | P0 | 3j | Timeline, filtres |
| Masquage données sensibles | P0 | 2j | Configurable |
| Tests | P0 | 2j | |

**Livrable**: Système d'audit

### 5.2 Sprint 21-22: Templates & Import (4 semaines)

| Tâche | Priorité | Estimation | Critères d'acceptation |
|-------|----------|------------|------------------------|
| Système templates user | P1 | 5j | Variables, génération |
| UI: Gestion templates | P1 | 4j | Création, utilisation |
| Import CSV | P1 | 4j | Utilisateurs en masse |
| Export CSV/LDIF | P1 | 3j | Backup données |
| Tests | P0 | 2j | |

**Livrable**: Templates et import/export

### 5.3 Sprint 23-24: Polish & Release (4 semaines)

| Tâche | Priorité | Estimation | Critères d'acceptation |
|-------|----------|------------|------------------------|
| Documentation utilisateur | P0 | 5j | Guide complet |
| Documentation API (OpenAPI) | P0 | 2j | Swagger UI |
| Documentation admin | P0 | 3j | Installation, config |
| Tests de charge | P1 | 3j | Performance acceptable |
| Bug fixes | P0 | 5j | Issues critiques résolues |
| Docker images production | P0 | 2j | Multi-arch, optimisées |
| Release preparation | P0 | 2j | Changelog, tags |

**Livrable**: v1.0.0

### 5.4 Milestone Phase 4

```
✓ Système d'audit complet
✓ Templates utilisateur
✓ Import/Export CSV
✓ Documentation complète
✓ Tests de charge passés
✓ Docker images production

Version: v1.0.0
```

---

## 6. Critères de Release

### 6.1 Alpha (v0.x.0-alpha)

- [ ] Fonctionnalité de base implémentée
- [ ] Tests unitaires passants
- [ ] Pas de crashs bloquants

### 6.2 Beta (v0.x.0-beta)

- [ ] Fonctionnalité complète pour la phase
- [ ] Tests d'intégration passants
- [ ] Documentation développeur
- [ ] Pas de régressions

### 6.3 Release Candidate (v1.0.0-rc.x)

- [ ] Toutes fonctionnalités v1.0 implémentées
- [ ] Tests E2E passants
- [ ] Documentation utilisateur
- [ ] Tests de performance
- [ ] Audit sécurité passé

### 6.4 Stable (v1.0.0)

- [ ] RC validé en environnement test
- [ ] Pas de bugs critiques
- [ ] Migration path documenté
- [ ] Support établi

---

## 7. Dépendances entre Tâches

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GRAPHE DE DÉPENDANCES                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  heracles-core ─────┬─────────────────────────────────────────────────────▶ │
│                     │                                                        │
│                     ▼                                                        │
│  heracles-api ──────┼─────────────────────────────────────────────────────▶ │
│       │             │                                                        │
│       │             ▼                                                        │
│       │      Plugin core ────────────────────────────────────────────────▶  │
│       │             │                                                        │
│       │             ├─────▶ Plugin posix ───────────────────────────────▶   │
│       │             │             │                                          │
│       │             │             ├─────▶ Plugin sudo ──────────────────▶   │
│       │             │             │                                          │
│       │             │             └─────▶ Plugin ssh ───────────────────▶   │
│       │             │                                                        │
│       │             └─────▶ Plugin systems ─────┬─────▶ Plugin dns ─────▶   │
│       │                                         │                            │
│       │                                         └─────▶ Plugin dhcp ────▶   │
│       ▼                                                                      │
│  heracles-ui ───────────────────────────────────────────────────────────▶   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Risques et Mitigations

| Risque | Impact | Probabilité | Mitigation |
|--------|--------|-------------|------------|
| Incompatibilité LDAP FD | Élevé | Moyenne | Tests de coexistence précoces |
| Performance LDAP | Moyen | Moyenne | Cache Redis, pagination |
| Complexité ACL | Moyen | Haute | Simplification initiale |
| PyO3 bindings instables | Moyen | Faible | Tests exhaustifs, fallback Python |
| Manque de ressources | Élevé | Moyenne | Priorisation stricte |

---

## 9. Hors Scope v1.0

Les éléments suivants sont explicitement hors scope pour v1.0:

- ❌ Multi-tenancy
- ❌ Plugins mail (postfix, dovecot, etc.)
- ❌ Plugin Samba
- ❌ Plugins académiques (SUPANN, SCHAC)
- ❌ WebAuthn/FIDO2
- ❌ OIDC provider
- ❌ GraphQL API
- ❌ Mobile app

Ces éléments pourront être considérés pour v2.0+.
