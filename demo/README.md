# Heracles Demo Environment

Environnement de test Vagrant pour valider les plugins SSH, Sudo, POSIX, Systems et DNS.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  HOST: Docker (LDAP:389, API:8000, PostgreSQL, Redis)       │
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
| testuser | testpassword123 | keys/testuser | ALL NOPASSWD | Tous (fullaccess) |
| devuser | devpassword123 | keys/devuser | apt, systemctl, journalctl | server1 uniquement |
| opsuser | opspassword123 | keys/opsuser | ALL (mot de passe) | Tous (fullaccess) |

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
