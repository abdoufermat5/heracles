# Tests de charge Heracles

Suite de tests de charge de niveau entreprise utilisant [Locust](https://locust.io/).

## Structure

```
tests/load/
├── locustfile.py          # Point d'entrée — hooks d'événements, mode debug, imports
├── locust.conf            # Configuration par défaut (modifiable via CLI/env)
├── common/
│   ├── __init__.py
│   ├── auth.py            # Mixin auth JWT (renouvellement auto, catch_response)
│   └── helpers.py         # Générateurs de données aléatoires
├── users/
│   ├── __init__.py
│   ├── admin.py           # Utilisateur admin — CRUD complet (poids 2)
│   ├── readonly.py        # Utilisateur lecture seule (poids 5)
│   └── api_consumer.py    # Automatisation / scripts (poids 1)
├── shapes/
│   ├── __init__.py
│   └── enterprise.py      # Profils de charge personnalisés (montée, pic, endurance)
└── README.md
```

## Personas utilisateurs

| Persona | Poids | Attente | Description |
|---------|-------|---------|-------------|
| **ReadOnlyUser** | 5 | 1-4s | Personnel typique naviguant dans l'interface |
| **AdminUser** | 2 | 1-3s | Administrateur IT effectuant des opérations CRUD |
| **APIConsumer** | 1 | 0.3-1s | Scripts CI/CD ou d'automatisation |

Avec 200 utilisateurs : ~125 lecteurs, ~50 admins, ~25 consommateurs API.

## Profils de charge

| Profil | Durée | Description |
|--------|-------|-------------|
| **EnterpriseRampShape** | ~22 min | Journée de travail : connexion matinale → pic → baisse l'après-midi |
| **SpikeTestShape** | ~8 min | Double pic de trafic pour tester la résilience |
| **SoakTestShape** | ~65 min | 100 utilisateurs soutenus pour détecter les fuites mémoire |

Sélectionnez les profils depuis l'interface Web via le menu déroulant du sélecteur de classes.

## Démarrage rapide

### Interface Web (recommandé)

```bash
# Démarrer Locust avec l'interface Web — ouvrir http://localhost:8089
cd tests/load && locust

# Avec le sélecteur de classes (choisir les personas et profils depuis l'interface)
cd tests/load && locust --class-picker

# Démarrage automatique avec interface Web (démarre immédiatement, l'interface reste ouverte pour le suivi)
cd tests/load && locust --autostart --autoquit 10
```

### Mode sans interface (headless)

```bash
# Test rapide (50 utilisateurs, 2 min — valeurs par défaut de locust.conf)
cd tests/load && locust --headless

# Échelle entreprise (200 utilisateurs, 5 min)
cd tests/load && locust --headless -u 200 -r 10 -t 5m

# Exécuter uniquement certains tags
cd tests/load && locust --headless -u 50 -t 1m --tags users posix

# Sélectionner des classes d'utilisateurs spécifiques
cd tests/load && locust --headless -u 100 -t 2m HeraclesReadOnlyUser HeraclesAdminUser
```

### Mode debug

```bash
# Exécuter un seul utilisateur avec journalisation des requêtes (sans runtime Locust)
cd tests/load && python locustfile.py
```

## Configuration

Les paramètres sont chargés depuis `locust.conf` (ce répertoire). Toute valeur peut être surchargée :

```bash
# Via les options CLI
cd tests/load && locust --users 100 --spawn-rate 10 --run-time 5m

# Via les variables d'environnement
LOCUST_USERS=100 LOCUST_SPAWN_RATE=10 locust
```

Ordre de priorité : `locust.conf` → variables d'env → options CLI

## Rapports et sorties

| Fichier | Description |
|---------|-------------|
| `results_stats.csv` | Statistiques agrégées par endpoint |
| `results_stats_history.csv` | Statistiques temporelles (pour les graphiques) |
| `results_failures.csv` | Détails des erreurs |
| `results_exceptions.csv` | Exceptions Python |
| `report_*.html` | Rapport HTML complet (généré automatiquement) |
| `locust.log` | Journal du processus Locust |

## Tags

Filtrer les tâches par tag pour cibler des domaines spécifiques :

```
users, groups, roles, departments, auth, health, acl, audit,
templates, import-export, config, plugins, write,
posix, ssh, sudo, systems, dns, dhcp, mail
```

Exemple : `locust --headless -u 50 -t 1m --tags users posix ssh`
