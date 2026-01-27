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
