# Installation de l'environnement de démonstration

## Prérequis

### Logiciels requis

| Logiciel | Version | Installation |
|----------|---------|--------------|
| VirtualBox | 7.x+ | [virtualbox.org/wiki/Downloads](https://www.virtualbox.org/wiki/Downloads) |
| Vagrant | 2.4+ | [developer.hashicorp.com/vagrant/install](https://developer.hashicorp.com/vagrant/install) |
| Docker | 20.x+ | [docs.docker.com/engine/install](https://docs.docker.com/engine/install/) |
| curl, jq | - | `sudo apt install curl jq ldap-utils` |

### Vérification

```bash
VBoxManage --version
vagrant --version
docker --version
```

## Étape 1 : Infrastructure Docker

> **Note** : Si votre utilisateur appartient au groupe `docker`, les commandes `make` ne nécessitent pas `sudo`.
> Pour ajouter votre utilisateur au groupe docker : `sudo usermod -aG docker $USER` (déconnexion/reconnexion requise).

### Démarrer les services

```bash
cd /chemin/vers/heracles

# Démarrer LDAP, PostgreSQL, Redis, phpLDAPadmin
make dev-infra

# Vérifier que les conteneurs sont en cours d'exécution
docker ps | grep heracles
```

### Services exposés

| Service | Port | Description |
|---------|------|-------------|
| OpenLDAP | 389 | Annuaire LDAP |
| OpenLDAP (SSL) | 636 | LDAP sécurisé |
| PostgreSQL | 5432 | Base de données |
| Redis | 6379 | Cache |
| phpLDAPadmin | 8080 | Interface web LDAP |
| API Heracles | 8000 | API REST |

### Charger les schémas LDAP

```bash
# Charger les schémas personnalisés (sudo, openssh-lpk, systems)
make ldap-schemas

# Vérifier que les schémas sont chargés
ldapsearch -x -H ldap://localhost:389 -b "cn=schema,cn=config" \
  -D "cn=admin,cn=config" -w config_secret "(cn=*sudo*)" cn
```

### Initialiser la structure LDAP

```bash
# Créer les OUs et l'utilisateur admin
make bootstrap

# Vérifier la structure
ldapsearch -x -H ldap://localhost:389 -b "dc=heracles,dc=local" \
  -D "cn=admin,dc=heracles,dc=local" -w admin_secret "(objectClass=*)" dn
```

## Étape 2 : Configuration réseau VirtualBox

### Créer le réseau host-only

```bash
# Lister les réseaux existants
VBoxManage list hostonlyifs

# Si vboxnet0 n'existe pas, le créer
VBoxManage hostonlyif create

# Configurer l'IP
VBoxManage hostonlyif ipconfig vboxnet0 --ip 192.168.56.1 --netmask 255.255.255.0
```

### Vérifier la connectivité

```bash
# Vérifier que l'interface existe
ip addr show vboxnet0

# Tester l'accès LDAP depuis le réseau host-only
nc -zv 192.168.56.1 389
```

## Étape 3 : Machines virtuelles

### Générer les clés SSH

```bash
cd demo
./scripts/generate-keys.sh
```

Cela crée les clés dans `demo/keys/` :
- `testuser` / `testuser.pub`
- `devuser` / `devuser.pub`
- `opsuser` / `opsuser.pub`

### Démarrer les VMs

```bash
# Démarrer toutes les VMs
vagrant up

# Ou démarrer une VM spécifique
vagrant up server1
vagrant up workstation1
```

Le provisioning automatique :
1. Configure SSSD pour l'authentification LDAP
2. Configure SSH avec `AuthorizedKeysCommand`
3. Configure Sudo pour les règles LDAP
4. Installe les certificats CA si nécessaire

### Vérifier l'état

```bash
vagrant status
```

Sortie attendue :
```
Current machine states:

server1                   running (virtualbox)
workstation1              running (virtualbox)
```

## Étape 4 : Configuration des utilisateurs

### Exécuter le script de configuration

```bash
./scripts/setup-demo-users.sh
```

Ce script effectue via l'API :
1. Création des utilisateurs (devuser, opsuser)
2. Activation POSIX pour tous les utilisateurs
3. Création des groupes (developers, ops)
4. Activation SSH et ajout des clés
5. Création des règles sudo

### Vérification manuelle

```bash
# Tester l'authentification API
curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "hrc-admin", "password": "hrc-admin-secret"}' | jq .

# Lister les utilisateurs
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "hrc-admin", "password": "hrc-admin-secret"}' | jq -r '.access_token')

curl -s "http://localhost:8000/api/v1/users" \
  -H "Authorization: Bearer $TOKEN" | jq '.items[].uid'
```

## Étape 5 : Validation

### Test SSH

```bash
# testuser
ssh -i keys/testuser -o StrictHostKeyChecking=no testuser@192.168.56.10 'whoami'

# devuser
ssh -i keys/devuser -o StrictHostKeyChecking=no devuser@192.168.56.10 'whoami'

# opsuser
ssh -i keys/opsuser -o StrictHostKeyChecking=no opsuser@192.168.56.10 'whoami'
```

### Test Sudo

```bash
# testuser - ALL sans mot de passe
ssh -i keys/testuser testuser@192.168.56.10 'sudo whoami'

# devuser - commandes limitées
ssh -i keys/devuser devuser@192.168.56.10 'sudo /usr/bin/apt --version'

# opsuser - requiert mot de passe
ssh -i keys/opsuser opsuser@192.168.56.10 'sudo -n whoami'
# Attendu: "sudo: a password is required"
```

## Nettoyage

### Arrêter les VMs

```bash
vagrant halt
```

### Supprimer les VMs

```bash
vagrant destroy -f
```

### Arrêter l'infrastructure Docker

```bash
cd /chemin/vers/heracles
make dev-down
```

### Supprimer les clés générées

```bash
rm -rf demo/keys/
```
