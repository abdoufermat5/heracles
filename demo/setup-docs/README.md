# Documentation Heracles Demo

Ce dossier contient la documentation complète pour l'environnement de démonstration Heracles.

## Sommaire

1. [Installation](01-INSTALLATION.md) - Prérequis et installation de l'environnement
2. [Configuration](02-CONFIGURATION.md) - Configuration des VMs et services
3. [Guide API](03-API-GUIDE.md) - Utilisation de l'API Heracles
4. [Tests](04-TESTS.md) - Procédures de test des plugins
5. [Dépannage](05-DEPANNAGE.md) - Résolution des problèmes courants

## Démarrage rapide

```bash
# 1. Démarrer l'infrastructure Docker
cd /chemin/vers/heracles
make dev-infra
make ldap-schemas
make bootstrap
make dns-bootstrap    # Zones DNS de démo

# 2. Générer les clés SSH de test
cd demo
./scripts/generate-keys.sh

# 3. Démarrer les VMs
vagrant up

# 4. Configurer les utilisateurs de démo
./scripts/setup-demo-users.sh

# 5. Test SSH
ssh -i keys/testuser testuser@192.168.56.10 'whoami && sudo whoami'

# 6. Test DNS
dig @192.168.56.20 server1.heracles.local
```

## VMs de l'environnement

| VM | IP | Rôle |
|----|-------|------|
| ns1 | 192.168.56.20 | Serveur DNS BIND9 (zones depuis LDAP) |
| server1 | 192.168.56.10 | Serveur de test SSSD |
| workstation1 | 192.168.56.11 | Workstation de test SSSD |

## Utilisateurs de test

| Utilisateur | Mot de passe | Permissions sudo |
|-------------|--------------|------------------|
| testuser | testpassword123 | ALL (sans mot de passe) |
| devuser | devpassword123 | apt, systemctl, journalctl |
| opsuser | opspassword123 | ALL (avec mot de passe) |

## Zones DNS de démo

| Zone | Type | Description |
|------|------|-------------|
| heracles.local | Forward | Zone principale de démo |
| 56.168.192.in-addr.arpa | Reverse | Zone inverse pour 192.168.56.0/24 |

Enregistrements pré-configurés :
- `ns1.heracles.local` → 192.168.56.20
- `server1.heracles.local` → 192.168.56.10
- `workstation1.heracles.local` → 192.168.56.11
- `ldap.heracles.local` → 192.168.56.1

## Structure du dossier demo

```
demo/
├── Vagrantfile           # Configuration Vagrant (ns1, server1, workstation1)
├── README.md             # Documentation rapide
├── .gitignore            # Exclusions Git
├── keys/                 # Clés SSH (générées, non versionnées)
├── provision/            # Scripts de provisioning VM
│   ├── setup-sssd.sh     # Configuration SSSD
│   ├── setup-ssh.sh      # Configuration SSH LDAP
│   ├── setup-sudo.sh     # Configuration sudo LDAP
│   └── setup-bind.sh     # Configuration BIND9 DNS
├── scripts/              # Scripts utilitaires
│   ├── generate-keys.sh
│   └── setup-demo-users.sh
└── setup-docs/           # Documentation détaillée
    ├── README.md
    ├── 01-INSTALLATION.md
    ├── 02-CONFIGURATION.md
    ├── 03-API-GUIDE.md
    ├── 04-TESTS.md
    └── 05-DEPANNAGE.md
```
