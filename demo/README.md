# Heracles Demo Environment

Environnement de test Vagrant pour valider les plugins SSH, Sudo, POSIX et Systems.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  HOST: Docker (LDAP:389, API:8000, PostgreSQL, Redis)       │
│                          │                                   │
│                   192.168.56.1                               │
│                          │                                   │
├──────────────────────────┼───────────────────────────────────┤
│              VirtualBox Private Network                      │
│         ┌────────────────┴────────────────┐                  │
│         ▼                                 ▼                  │
│  ┌─────────────┐                  ┌─────────────┐           │
│  │   server1   │                  │ workstation1│           │
│  │ .56.10      │                  │ .56.11      │           │
│  └─────────────┘                  └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# 1. Infrastructure Docker (depuis la racine du projet)
make dev-infra && make ldap-schemas && make bootstrap

# 2. Réseau VirtualBox
VBoxManage hostonlyif create
VBoxManage hostonlyif ipconfig vboxnet0 --ip 192.168.56.1

# 3. VMs et utilisateurs
cd demo
./scripts/generate-keys.sh
vagrant up
./scripts/setup-demo-users.sh

# 4. Test
ssh -i keys/testuser testuser@192.168.56.10 'whoami && sudo whoami'
```

> **Note** : Si votre utilisateur appartient au groupe `docker`, les commandes `make` ne nécessitent pas `sudo`. Sinon, utilisez `sudo make dev-infra`, `sudo make clean`, etc.

## Utilisateurs de test

| Utilisateur | Mot de passe | Clé SSH | Sudo |
|-------------|--------------|---------|------|
| testuser | testpassword123 | keys/testuser | ALL NOPASSWD |
| devuser | devpassword123 | keys/devuser | apt, systemctl, journalctl |
| opsuser | opspassword123 | keys/opsuser | ALL (mot de passe) |

## Commandes Vagrant

```bash
vagrant status          # Statut des VMs
vagrant up              # Démarrer les VMs
vagrant halt            # Arrêter les VMs
vagrant destroy -f      # Supprimer les VMs
vagrant ssh server1     # Connexion SSH locale
```

## Documentation détaillée

Voir le dossier [setup-docs/](setup-docs/) :

- [Installation](setup-docs/01-INSTALLATION.md)
- [Configuration](setup-docs/02-CONFIGURATION.md)
- [Guide API](setup-docs/03-API-GUIDE.md)
- [Tests](setup-docs/04-TESTS.md)
- [Dépannage](setup-docs/05-DEPANNAGE.md)
