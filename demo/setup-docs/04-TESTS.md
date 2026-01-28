# Tests des plugins

## Prérequis

```bash
cd demo
./scripts/generate-keys.sh   # Générer les clés SSH
./scripts/setup-demo-users.sh  # Configurer les utilisateurs
```

## Test SSH

```bash
# testuser
ssh -i keys/testuser testuser@192.168.56.10 'whoami && id'

# devuser
ssh -i keys/devuser devuser@192.168.56.10 'whoami && id'

# opsuser
ssh -i keys/opsuser opsuser@192.168.56.10 'whoami && id'
```

**Résultat attendu :** Connexion réussie avec affichage du nom d'utilisateur et des groupes.

## Test Sudo

### testuser - ALL sans mot de passe

```bash
ssh -i keys/testuser testuser@192.168.56.10 'sudo whoami'
ssh -i keys/testuser testuser@192.168.56.10 'sudo cat /etc/shadow | head -2'
```

**Résultat attendu :** `root` et contenu de /etc/shadow.

### devuser - Commandes limitées

```bash
# Commandes autorisées
ssh -i keys/devuser devuser@192.168.56.10 'sudo /usr/bin/apt --version'
ssh -i keys/devuser devuser@192.168.56.10 'sudo /usr/bin/systemctl status sshd | head -5'
ssh -i keys/devuser devuser@192.168.56.10 'sudo /usr/bin/journalctl -n 3 --no-pager'

# Commande interdite
ssh -i keys/devuser devuser@192.168.56.10 'sudo cat /etc/shadow'
```

**Résultat attendu :** Les 3 premières commandes réussissent, la dernière échoue avec "password required".

### opsuser - ALL avec mot de passe

```bash
ssh -i keys/opsuser opsuser@192.168.56.10 'sudo -n whoami'
```

**Résultat attendu :** `sudo: a password is required`

## Test POSIX

```bash
vagrant ssh server1 -c 'getent passwd testuser'
vagrant ssh server1 -c 'getent passwd devuser'
vagrant ssh server1 -c 'getent group developers'
vagrant ssh server1 -c 'getent group ops'
```

**Résultat attendu :** Informations utilisateur/groupe depuis LDAP.

## Rafraîchir le cache SSSD

Si les utilisateurs n'apparaissent pas :

```bash
vagrant ssh server1 -c 'sudo sss_cache -E && sudo systemctl restart sssd'
```

## Résumé des permissions

| Utilisateur | SSH | Sudo |
|-------------|-----|------|
| testuser | keys/testuser | ALL NOPASSWD |
| devuser | keys/devuser | apt, systemctl, journalctl |
| opsuser | keys/opsuser | ALL (mot de passe requis) |

## Test DNS

### Prérequis DNS

```bash
# S'assurer que les zones DNS sont créées
make dns-bootstrap

# Démarrer la VM ns1 (serveur DNS)
cd demo && vagrant up ns1
```

### Test de résolution DNS

```bash
# Résolution forward (depuis l'hôte)
dig @192.168.56.20 server1.heracles.local
dig @192.168.56.20 ns1.heracles.local
dig @192.168.56.20 ldap.heracles.local

# Résolution CNAME
dig @192.168.56.20 api.heracles.local
dig @192.168.56.20 dns.heracles.local

# Enregistrement MX
dig @192.168.56.20 MX heracles.local

# Résolution inverse
dig @192.168.56.20 -x 192.168.56.10
dig @192.168.56.20 -x 192.168.56.20
```

**Résultat attendu :**
- `server1.heracles.local` → 192.168.56.10
- `ns1.heracles.local` → 192.168.56.20
- `api.heracles.local` → CNAME vers ldap.heracles.local
- PTR pour 192.168.56.10 → server1.heracles.local

### Test API DNS

```bash
# Obtenir un token
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "hrc-admin", "password": "hrc-admin-secret"}' | jq -r '.access_token')

# Lister les zones
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/dns/zones | jq .

# Détails d'une zone
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/dns/zones/heracles.local | jq .

# Lister les enregistrements
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/dns/zones/heracles.local/records | jq .
```

### Test CRUD enregistrements

```bash
# Créer un enregistrement
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  http://localhost:8000/api/v1/dns/zones/heracles.local/records \
  -d '{"name":"test","record_type":"A","value":"192.168.56.99","ttl":3600}' | jq .

# Vérifier (après sync)
vagrant ssh ns1 -c 'sudo /usr/local/bin/ldap-dns-sync.sh'
dig @192.168.56.20 test.heracles.local

# Supprimer l'enregistrement
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/dns/zones/heracles.local/records/test/A?value=192.168.56.99"
```

### Test modification SOA

```bash
# Modifier le SOA (serial auto-incrémenté)
curl -s -X PUT -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  http://localhost:8000/api/v1/dns/zones/heracles.local \
  -d '{"soa_refresh":7200}' | jq '.soa.serial, .soa.refresh'
```

**Résultat attendu :** Le serial est incrémenté et refresh=7200.

### Synchronisation LDAP → BIND

Le serveur ns1 synchronise périodiquement les zones depuis LDAP. Pour forcer la synchronisation :

```bash
vagrant ssh ns1 -c 'sudo /usr/local/bin/ldap-dns-sync.sh'
vagrant ssh ns1 -c 'sudo systemctl reload named'
```
