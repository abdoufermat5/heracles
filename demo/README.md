# Heracles Demo Environment

Environnement de test Vagrant pour valider les plugins SSH, Sudo, POSIX, Systems et DNS.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  HOST: Docker (LDAPS:636, API:8000, PostgreSQL, Redis)      │
│                          │                                   │
│                   192.168.56.1                               │
│                          │                                   │
├──────────────────────────┼───────────────────────────────────┤
│              VirtualBox Private Network                      │
│         ┌────────────────┼────────────────┐                  │
│         ▼                ▼                ▼                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │    ns1      │  │   server1   │  │ workstation1│          │
│  │ .56.20 DNS  │  │ .56.10      │  │ .56.11      │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# 1. Infrastructure Docker (depuis la racine du projet)
make dev-infra && make ldap-schemas && make bootstrap

# 2. Charger les zones DNS de démo
make dns-bootstrap

# 2.1 Copier la PKI pour les VMs
mkdir -p config/ca config/certs
cp ../pki/dev/ca/heracles-dev-ca.crt config/ca/
cp ../pki/dev/server/heracles.local.crt config/certs/
cp ../pki/dev/server/heracles.local.key config/certs/

# 3. Réseau VirtualBox
VBoxManage hostonlyif create
VBoxManage hostonlyif ipconfig vboxnet0 --ip 192.168.56.1

# 4. VMs et utilisateurs
cd demo
./scripts/generate-keys.sh
vagrant up
./scripts/setup-demo-users.sh

# 5. Test SSH
ssh -i keys/testuser testuser@192.168.56.10 'whoami && sudo whoami'

# 6. Test DNS
dig @192.168.56.20 server1.heracles.local
dig @192.168.56.20 -x 192.168.56.10
```

> **Note** : Si votre utilisateur appartient au groupe `docker`, les commandes `make` ne nécessitent pas `sudo`. Sinon, utilisez `sudo make dev-infra`, `sudo make clean`, etc.

## Utilisateurs de test

| Utilisateur | Mot de passe | Clé SSH | Sudo | Accès Hôtes |
|-------------|--------------|---------|------|-------------|
| testuser | Testpassword123 | keys/testuser | ALL NOPASSWD | Tous (fullaccess) |
| devuser | Devpassword123 | keys/devuser | apt, systemctl, journalctl | server1 uniquement |
| opsuser | Opspassword123 | keys/opsuser | ALL (mot de passe) | Tous (fullaccess) |

### Host-based Access Control

Le plugin POSIX permet de restreindre l'accès des utilisateurs à certains systèmes via l'attribut `host` et le `trustMode` :

- **fullaccess** : L'utilisateur peut accéder à tous les systèmes (`host: *`)
- **byhost** : L'utilisateur ne peut accéder qu'aux systèmes listés dans `host`

Exemple de test :

```bash
# testuser peut accéder partout
ssh -i keys/testuser testuser@192.168.56.10  # ✓ server1
ssh -i keys/testuser testuser@192.168.56.11  # ✓ workstation1

# devuser ne peut accéder qu'à server1
ssh -i keys/devuser devuser@192.168.56.10    # ✓ server1
ssh -i keys/devuser devuser@192.168.56.11    # ✗ REFUSÉ
```

## Serveur DNS (ns1)

La VM `ns1` exécute BIND9 et sert les zones DNS depuis LDAP :

```bash
# Démarrer uniquement ns1
vagrant up ns1

# Test DNS
dig @192.168.56.20 server1.heracles.local
dig @192.168.56.20 -x 192.168.56.10

# Connexion à ns1
vagrant ssh ns1

# Forcer synchronisation LDAP → zone files
vagrant ssh ns1 -c 'sudo /usr/local/bin/ldap-dns-sync.sh && sudo systemctl reload named'
```

### Zones DNS de démo

| Zone | Type | Description |
|------|------|-------------|
| heracles.local | Forward | Zone principale |
| 56.168.192.in-addr.arpa | Reverse | Résolution inverse |

## Accès aux services Docker via DNS

Les services Docker (API, UI, LDAP, PostgreSQL, Redis, phpLDAPadmin) sont accessibles via des noms DNS dans la zone `heracles.local` :

| Service         | URL d'accès (depuis l'hôte ou les VMs)         |
|----------------|-----------------------------------------------|
| UI             | https://ui.heracles.local                       |
| API            | https://api.heracles.local/api/v1/health        |
| phpLDAPadmin   | http://phpldapadmin.heracles.local:8080         |
| LDAP           | ldaps://ldap.heracles.local:636                 |
| PostgreSQL     | postgres.heracles.local:5432                   |
| Redis          | redis.heracles.local:6379                      |

> **Note** : Les enregistrements DNS sont générés automatiquement par le script `scripts/ldap-dns-bootstrap.sh` (A records pointant vers 192.168.56.1).

### Configuration Vite (UI)

Le fichier `heracles-ui/vite.config.ts` autorise les accès via les domaines `.heracles.local` et configure le proxy API :

```js
server: {
  port: 3000,
  host: true,
  allowedHosts: [
    'localhost',
    'ui.heracles.local',
    '.heracles.local',
  ],
  proxy: {
    '/api': {
      target: process.env.VITE_API_URL || 'http://api.heracles.local:8000',
      changeOrigin: true,
    },
  },
},
```

### Synchronisation DNS

- Les enregistrements DNS sont stockés dans LDAP et synchronisés automatiquement sur la VM `ns1` (BIND9) via le script `/usr/local/bin/ldap-dns-sync.sh`.
- Pour forcer une synchronisation :

```bash
vagrant ssh ns1 -c 'sudo /usr/local/bin/ldap-dns-sync.sh && sudo systemctl reload named'
```

- Les enregistrements A pour `ui`, `api`, `phpldapadmin`, `postgres`, `redis` pointent tous vers l’IP de l’hôte Docker (`192.168.56.1`).

## Commandes Vagrant

```bash
vagrant status          # Statut des VMs
vagrant up              # Démarrer toutes les VMs
vagrant up ns1          # Démarrer uniquement ns1
vagrant up server1      # Démarrer uniquement server1
vagrant halt            # Arrêter les VMs
vagrant destroy -f      # Supprimer les VMs
vagrant ssh server1     # Connexion SSH locale
vagrant ssh ns1         # Connexion au serveur DNS
```

## Commandes Make (depuis la racine du projet)

```bash
make dns-bootstrap      # Créer les zones DNS de démo dans LDAP
make demo-ssh-ns1       # SSH vers ns1
make demo-up            # vagrant up
make demo-halt          # vagrant halt
make demo-destroy       # vagrant destroy -f
```

## Documentation détaillée

Voir le dossier [setup-docs/](setup-docs/) :

- [Installation](setup-docs/01-INSTALLATION.md)
- [Configuration](setup-docs/02-CONFIGURATION.md)
- [Guide API](setup-docs/03-API-GUIDE.md) - Inclut les endpoints DNS
- [Tests](setup-docs/04-TESTS.md) - Inclut les tests DNS
- [Dépannage](setup-docs/05-DEPANNAGE.md)
