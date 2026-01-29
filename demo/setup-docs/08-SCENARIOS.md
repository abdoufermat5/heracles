# Scénarios de démonstration

Ce document présente des scénarios pas-à-pas pour démontrer les capacités de Heracles.

## Scénario 1 : Onboarding d'un nouveau développeur

**Objectif** : Créer un compte développeur avec accès SSH et permissions sudo limitées.

### Étape 1 : Authentification API

```bash
# Obtenir un token JWT
export TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "hrc-admin", "password": "hrc-admin-secret"}' | jq -r '.access_token')

echo "Token obtenu: ${TOKEN:0:20}..."
```

### Étape 2 : Créer l'utilisateur

```bash
curl -X POST "http://localhost:8000/api/v1/users" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "jdupont",
    "givenName": "Jean",
    "sn": "Dupont",
    "mail": "jean.dupont@heracles.local",
    "userPassword": "Welcome2024!"
  }' | jq .
```

### Étape 3 : Activer POSIX

```bash
curl -X POST "http://localhost:8000/api/v1/users/jdupont/posix" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "uidNumber": 10010,
    "gidNumber": 10000,
    "homeDirectory": "/home/jdupont",
    "loginShell": "/bin/bash"
  }' | jq .
```

### Étape 4 : Ajouter au groupe developers

```bash
# Ajouter au groupe
curl -X POST "http://localhost:8000/api/v1/groups/developers/members" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"uid": "jdupont"}' | jq .
```

### Étape 5 : Configurer SSH

```bash
# Générer une clé SSH pour le nouvel utilisateur
ssh-keygen -t ed25519 -f /tmp/jdupont -N "" -C "jdupont@heracles.local"

# Activer SSH et ajouter la clé
curl -X POST "http://localhost:8000/api/v1/users/jdupont/ssh" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"sshPublicKey\": \"$(cat /tmp/jdupont.pub)\"
  }" | jq .
```

### Étape 6 : Créer une règle sudo

```bash
curl -X POST "http://localhost:8000/api/v1/sudo/rules" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cn": "jdupont_dev_sudo",
    "sudoUser": ["jdupont"],
    "sudoHost": ["ALL"],
    "sudoCommand": ["/usr/bin/docker", "/usr/bin/docker-compose", "/usr/bin/npm"],
    "sudoOption": ["!authenticate"]
  }' | jq .
```

### Étape 7 : Tester l'accès

```bash
# Attendre la propagation SSSD (environ 5 secondes)
sleep 5

# Test SSH
ssh -i /tmp/jdupont jdupont@192.168.56.10 'whoami && id'

# Test sudo
ssh -i /tmp/jdupont jdupont@192.168.56.10 'sudo docker --version'
ssh -i /tmp/jdupont jdupont@192.168.56.10 'sudo npm --version'

# Vérifier que sudo est limité
ssh -i /tmp/jdupont jdupont@192.168.56.10 'sudo cat /etc/shadow'
# Attendu: permission refusée
```

---

## Scénario 2 : Déploiement d'un nouveau serveur

**Objectif** : Ajouter un nouveau serveur à l'infrastructure avec DNS et DHCP.

### Étape 1 : Obtenir l'adresse MAC

```bash
# Simuler l'adresse MAC du nouveau serveur
export NEW_MAC="AA:BB:CC:DD:EE:01"
export NEW_IP="192.168.56.30"
export NEW_NAME="webserver1"
```

### Étape 2 : Créer l'enregistrement DNS

```bash
# Enregistrement A
curl -X POST "http://localhost:8000/api/v1/dns/zones/heracles.local/records" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"$NEW_NAME\",
    \"type\": \"A\",
    \"content\": \"$NEW_IP\",
    \"ttl\": 3600
  }" | jq .

# Enregistrement PTR
curl -X POST "http://localhost:8000/api/v1/dns/zones/56.168.192.in-addr.arpa/records" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"30\",
    \"type\": \"PTR\",
    \"content\": \"$NEW_NAME.heracles.local.\"
  }" | jq .
```

### Étape 3 : Créer la réservation DHCP

```bash
curl -X POST "http://localhost:8000/api/v1/dhcp/demo-dhcp/hosts" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"cn\": \"$NEW_NAME\",
    \"dhcpHWAddress\": \"ethernet $NEW_MAC\",
    \"fixedAddress\": \"$NEW_IP\",
    \"comments\": \"Serveur web de production\",
    \"dhcpOptions\": [
      \"host-name \\\"$NEW_NAME\\\"\"
    ]
  }" | jq .
```

### Étape 4 : Enregistrer dans l'inventaire

```bash
curl -X POST "http://localhost:8000/api/v1/systems/workstations" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"cn\": \"$NEW_NAME\",
    \"description\": \"Serveur web Apache\",
    \"ipHostNumber\": \"$NEW_IP\",
    \"macAddress\": \"$NEW_MAC\",
    \"l\": \"Datacenter Paris\"
  }" | jq .
```

### Étape 5 : Synchroniser DHCP

```bash
vagrant ssh dhcp1 -c "sudo /etc/dhcp/ldap-dhcp-sync.sh"
```

### Étape 6 : Vérifier

```bash
# Test DNS
dig @192.168.56.20 $NEW_NAME.heracles.local +short
dig @192.168.56.20 -x $NEW_IP +short

# Vérifier la config DHCP
vagrant ssh dhcp1 -c "grep -A5 '$NEW_NAME' /etc/dhcp/dhcpd.conf"
```

---

## Scénario 3 : Audit des accès sudo

**Objectif** : Examiner et modifier les règles sudo existantes.

### Étape 1 : Lister toutes les règles

```bash
curl -s "http://localhost:8000/api/v1/sudo/rules" \
  -H "Authorization: Bearer $TOKEN" | jq '.items[] | {cn, sudoUser, sudoCommand}'
```

### Étape 2 : Examiner une règle spécifique

```bash
curl -s "http://localhost:8000/api/v1/sudo/rules/devuser_sudo" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

### Étape 3 : Identifier les accès trop permissifs

```bash
# Trouver les règles avec "ALL" dans sudoCommand
curl -s "http://localhost:8000/api/v1/sudo/rules" \
  -H "Authorization: Bearer $TOKEN" | \
  jq '.items[] | select(.sudoCommand[] == "ALL") | .cn'
```

### Étape 4 : Restreindre une règle

```bash
# Modifier la règle opsuser pour limiter les commandes
curl -X PUT "http://localhost:8000/api/v1/sudo/rules/opsuser_sudo" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sudoCommand": [
      "/usr/bin/systemctl restart *",
      "/usr/bin/journalctl",
      "/usr/bin/docker logs *",
      "!/usr/bin/systemctl stop sshd"
    ],
    "sudoOption": ["authenticate", "log_output"]
  }' | jq .
```

### Étape 5 : Ajouter une règle temporaire

```bash
# Règle d'urgence avec expiration
EXPIRE_DATE=$(date -d "+1 day" +%Y%m%d%H%M%SZ)

curl -X POST "http://localhost:8000/api/v1/sudo/rules" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"cn\": \"emergency_access\",
    \"sudoUser\": [\"jdupont\"],
    \"sudoHost\": [\"server1\"],
    \"sudoCommand\": [\"ALL\"],
    \"sudoOption\": [\"authenticate\"],
    \"sudoNotBefore\": \"$(date +%Y%m%d%H%M%SZ)\",
    \"sudoNotAfter\": \"$EXPIRE_DATE\"
  }" | jq .
```

---

## Scénario 4 : Rotation des clés SSH

**Objectif** : Mettre à jour les clés SSH d'un utilisateur.

### Étape 1 : Générer une nouvelle clé

```bash
ssh-keygen -t ed25519 -f /tmp/devuser_new -N "" -C "devuser-2024@heracles.local"
```

### Étape 2 : Vérifier les clés actuelles

```bash
curl -s "http://localhost:8000/api/v1/users/devuser/ssh" \
  -H "Authorization: Bearer $TOKEN" | jq '.sshPublicKey'
```

### Étape 3 : Ajouter la nouvelle clé (période de transition)

```bash
# Récupérer les clés existantes
EXISTING_KEYS=$(curl -s "http://localhost:8000/api/v1/users/devuser/ssh" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.sshPublicKey | join("\n")')

# Ajouter la nouvelle clé
curl -X PUT "http://localhost:8000/api/v1/users/devuser/ssh" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"sshPublicKey\": [
      $(echo "$EXISTING_KEYS" | jq -R -s 'split("\n") | map(select(. != "")) | .[]'),
      \"$(cat /tmp/devuser_new.pub)\"
    ]
  }" | jq .
```

### Étape 4 : Tester les deux clés

```bash
# Ancienne clé (doit fonctionner)
ssh -i demo/keys/devuser devuser@192.168.56.10 'echo "Ancienne clé OK"'

# Nouvelle clé (doit fonctionner)
ssh -i /tmp/devuser_new devuser@192.168.56.10 'echo "Nouvelle clé OK"'
```

### Étape 5 : Retirer l'ancienne clé

```bash
curl -X PUT "http://localhost:8000/api/v1/users/devuser/ssh" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"sshPublicKey\": [\"$(cat /tmp/devuser_new.pub)\"]
  }" | jq .
```

### Étape 6 : Vérifier

```bash
# Ancienne clé (ne doit plus fonctionner après cache SSSD expiration)
sleep 10  # Attendre l'invalidation du cache
ssh -i demo/keys/devuser devuser@192.168.56.10 'echo "Test"'
# Attendu: Permission denied

# Nouvelle clé (doit fonctionner)
ssh -i /tmp/devuser_new devuser@192.168.56.10 'echo "Nouvelle clé OK"'
```

---

## Scénario 5 : Création d'une zone DNS complète

**Objectif** : Créer une nouvelle zone DNS avec tous les enregistrements nécessaires.

### Étape 1 : Créer la zone forward

```bash
curl -X POST "http://localhost:8000/api/v1/dns/zones" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "zoneName": "prod.heracles.local",
    "zoneType": "master",
    "soa": {
      "primaryNs": "ns1.heracles.local.",
      "adminEmail": "admin.heracles.local.",
      "refresh": 3600,
      "retry": 600,
      "expire": 86400,
      "minimum": 3600
    }
  }' | jq .
```

### Étape 2 : Créer la zone reverse

```bash
curl -X POST "http://localhost:8000/api/v1/dns/zones" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "zoneName": "100.168.192.in-addr.arpa",
    "zoneType": "master",
    "soa": {
      "primaryNs": "ns1.heracles.local.",
      "adminEmail": "admin.heracles.local."
    }
  }' | jq .
```

### Étape 3 : Ajouter les enregistrements de base

```bash
# Enregistrement NS
curl -X POST "http://localhost:8000/api/v1/dns/zones/prod.heracles.local/records" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "@",
    "type": "NS",
    "content": "ns1.heracles.local."
  }'

# Serveur web
curl -X POST "http://localhost:8000/api/v1/dns/zones/prod.heracles.local/records" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "www",
    "type": "A",
    "content": "192.168.100.10"
  }'

# Alias
curl -X POST "http://localhost:8000/api/v1/dns/zones/prod.heracles.local/records" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "app",
    "type": "CNAME",
    "content": "www.prod.heracles.local."
  }'

# Mail
curl -X POST "http://localhost:8000/api/v1/dns/zones/prod.heracles.local/records" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "@",
    "type": "MX",
    "content": "10 mail.prod.heracles.local."
  }'

curl -X POST "http://localhost:8000/api/v1/dns/zones/prod.heracles.local/records" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "mail",
    "type": "A",
    "content": "192.168.100.20"
  }'

# SPF
curl -X POST "http://localhost:8000/api/v1/dns/zones/prod.heracles.local/records" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "@",
    "type": "TXT",
    "content": "\"v=spf1 mx -all\""
  }'
```

### Étape 4 : Ajouter les PTR

```bash
curl -X POST "http://localhost:8000/api/v1/dns/zones/100.168.192.in-addr.arpa/records" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "10",
    "type": "PTR",
    "content": "www.prod.heracles.local."
  }'

curl -X POST "http://localhost:8000/api/v1/dns/zones/100.168.192.in-addr.arpa/records" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "20",
    "type": "PTR",
    "content": "mail.prod.heracles.local."
  }'
```

### Étape 5 : Vérifier

```bash
dig @192.168.56.20 www.prod.heracles.local
dig @192.168.56.20 app.prod.heracles.local
dig @192.168.56.20 prod.heracles.local MX
dig @192.168.56.20 prod.heracles.local TXT
dig @192.168.56.20 -x 192.168.100.10
```

---

## Scénario 6 : Dépannage d'un problème d'authentification

**Objectif** : Diagnostiquer pourquoi un utilisateur ne peut pas se connecter.

### Étape 1 : Vérifier l'utilisateur existe

```bash
curl -s "http://localhost:8000/api/v1/users/jdupont" \
  -H "Authorization: Bearer $TOKEN" | jq '{uid, posixEnabled: .uidNumber != null}'
```

### Étape 2 : Vérifier POSIX est activé

```bash
curl -s "http://localhost:8000/api/v1/users/jdupont" \
  -H "Authorization: Bearer $TOKEN" | jq '{uidNumber, gidNumber, homeDirectory, loginShell}'
```

### Étape 3 : Vérifier SSH est activé

```bash
curl -s "http://localhost:8000/api/v1/users/jdupont/ssh" \
  -H "Authorization: Bearer $TOKEN" | jq '.sshPublicKey | length'
```

### Étape 4 : Vérifier côté serveur

```bash
# Vérifier SSSD
vagrant ssh server1 -c "id jdupont"
vagrant ssh server1 -c "getent passwd jdupont"

# Vérifier le cache SSSD
vagrant ssh server1 -c "sudo sss_cache -u jdupont"

# Vérifier les logs SSSD
vagrant ssh server1 -c "sudo journalctl -u sssd -n 50"

# Vérifier la recherche de clés SSH
vagrant ssh server1 -c "sudo /usr/local/bin/ldap-ssh-keys.sh jdupont"
```

### Étape 5 : Vérifier la connectivité LDAP

```bash
vagrant ssh server1 -c "ldapsearch -x -H ldap://192.168.56.1 \
  -b 'dc=heracles,dc=local' '(uid=jdupont)' uid sshPublicKey"
```

### Étape 6 : Forcer la mise à jour du cache

```bash
vagrant ssh server1 -c "sudo sss_cache -E"
vagrant ssh server1 -c "sudo systemctl restart sssd"
```

---

## Scripts utilitaires

### Script de démonstration complète

```bash
#!/bin/bash
# demo-full.sh - Exécute tous les scénarios de démonstration

set -e

echo "=== Heracles Demo ==="
echo ""

# Authentification
export TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "hrc-admin", "password": "hrc-admin-secret"}' | jq -r '.access_token')

echo "✓ Authentification réussie"

# Lister les ressources
echo ""
echo "=== État actuel ==="
echo "Utilisateurs: $(curl -s "http://localhost:8000/api/v1/users" -H "Authorization: Bearer $TOKEN" | jq '.total')"
echo "Groupes: $(curl -s "http://localhost:8000/api/v1/groups" -H "Authorization: Bearer $TOKEN" | jq '.total')"
echo "Règles sudo: $(curl -s "http://localhost:8000/api/v1/sudo/rules" -H "Authorization: Bearer $TOKEN" | jq '.total')"
echo "Zones DNS: $(curl -s "http://localhost:8000/api/v1/dns/zones" -H "Authorization: Bearer $TOKEN" | jq '.total')"
echo "Services DHCP: $(curl -s "http://localhost:8000/api/v1/dhcp" -H "Authorization: Bearer $TOKEN" | jq '.total')"

echo ""
echo "=== Tests de connectivité ==="
echo -n "SSH testuser: "
ssh -i demo/keys/testuser -o ConnectTimeout=5 -o StrictHostKeyChecking=no testuser@192.168.56.10 'echo OK' 2>/dev/null || echo "FAILED"

echo -n "DNS ns1: "
dig @192.168.56.20 server1.heracles.local +short +time=2 || echo "FAILED"

echo ""
echo "=== Démonstration terminée ==="
```

Enregistrer dans `demo/scripts/demo-full.sh` et exécuter :
```bash
chmod +x demo/scripts/demo-full.sh
./demo/scripts/demo-full.sh
```
