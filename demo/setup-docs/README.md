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

# 2. Générer les clés SSH de test
cd demo
./scripts/generate-keys.sh

# 3. Démarrer les VMs
vagrant up

# 4. Configurer les utilisateurs de démo
./scripts/setup-demo-users.sh

# 5. Tester
ssh -i keys/testuser testuser@192.168.56.10 'whoami && sudo whoami'
```

## Utilisateurs de test

| Utilisateur | Mot de passe | Permissions sudo |
|-------------|--------------|------------------|
| testuser | testpassword123 | ALL (sans mot de passe) |
| devuser | devpassword123 | apt, systemctl, journalctl |
| opsuser | opspassword123 | ALL (avec mot de passe) |

## Structure du dossier demo

```
demo/
├── Vagrantfile           # Configuration Vagrant
├── README.md             # Documentation rapide
├── .gitignore            # Exclusions Git
├── keys/                 # Clés SSH (générées, non versionnées)
├── provision/            # Scripts de provisioning VM
│   ├── setup-sssd.sh
│   ├── setup-ssh.sh
│   └── setup-sudo.sh
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
