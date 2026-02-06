# Guide du Serveur de Messagerie (Postfix + Dovecot + Roundcube)

Ce guide détaille l'installation et l'utilisation du serveur de messagerie dans l'environnement de démonstration Heracles.

## Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture](#architecture)
3. [Réseau et ports](#réseau-et-ports)
4. [Installation](#installation)
5. [Activation de la messagerie](#activation-de-la-messagerie)
6. [Webmail Roundcube](#webmail-roundcube)
7. [Tests et validation](#tests-et-validation)
8. [Intégration LDAP](#intégration-ldap)
9. [Dépannage](#dépannage)
10. [Référence des fichiers](#référence-des-fichiers)

---

## Vue d'ensemble

La VM `mail1` fournit un serveur de messagerie d'entreprise complet :

| Composant | Rôle | Version |
|-----------|------|---------|
| **Postfix** | Serveur SMTP (envoi/réception) | 3.7+ |
| **Dovecot** | Serveur IMAP + livraison LMTP + Sieve | 2.3+ |
| **Roundcube** | Webmail (interface web) | 1.6+ |
| **Nginx** | Serveur web frontal (HTTPS) | 1.22+ |
| **OpenLDAP** | Annuaire des utilisateurs (sur l'hôte Docker) | 1.5.0 |

**Authentification :** Bind LDAP direct — Dovecot se connecte à OpenLDAP avec l'`uid` et le mot de passe de l'utilisateur. Aucune dépendance à SSSD sur cette VM.

**Prérequis :** Les utilisateurs doivent avoir l'objectClass `hrcMailAccount` activé via l'API Heracles avant de pouvoir s'authentifier sur IMAP ou envoyer du courrier authentifié.

## Architecture

```
                                    ┌──────────────────────────────────────────────────┐
                                    │  mail1  (192.168.56.22)                          │
                                    │                                                  │
  Client mail (Thunderbird, etc.)   │  ┌──────────┐       ┌──────────┐                │
  ─── SMTP (587/STARTTLS) ─────────▶│  │ Postfix  │──LMTP─▶│ Dovecot  │               │
  ─── SMTPS (465/TLS) ─────────────▶│  │          │       │          │                │
                                    │  │  Requêtes │       │  Auth    │                │
  ─── IMAP (143/STARTTLS) ─────────▶│  │  LDAP    │       │  LDAP    │                │
  ─── IMAPS (993/TLS) ─────────────▶│  └────┬─────┘       └────┬─────┘                │
                                    │       │                   │                      │
  Navigateur web                    │  ┌────────────┐    ┌──────────┐                  │
  ─── HTTPS (443) ─────────────────▶│  │   Nginx    │───▶│Roundcube │                  │
                                    │  │  (frontal  │    │ (PHP-FPM)│                  │
                                    │  │   HTTPS)   │    └──────────┘                  │
                                    │  └────────────┘                                  │
                                    └──────────┬───────────────────┬───────────────────┘
                                               │                   │
                                               ▼                   ▼
                                    ┌───────────────────────────────────────┐
                                    │  Hôte Docker (192.168.56.1)           │
                                    │  OpenLDAP (:389)                      │
                                    │                                       │
                                    │  ou=people  → hrcMailAccount          │
                                    │  ou=groups  → hrcGroupMail            │
                                    └───────────────────────────────────────┘
```

### Flux de données

1. **Réception de courrier (SMTP :25) :** Postfix reçoit → interroge LDAP pour `hrcMailAccount` → livre via LMTP à Dovecot → stocké en Maildir sous `/var/mail/vhosts/`
2. **Envoi authentifié (Submission :587 / SMTPS :465) :** Le client se connecte avec STARTTLS/TLS → Postfix délègue SASL à Dovecot → Dovecot fait un bind LDAP → le courrier est relayé
3. **Accès IMAP (:143 / :993) :** Le client se connecte → Dovecot fait un bind LDAP avec les identifiants → sert le contenu Maildir
4. **Webmail (:443) :** Le navigateur accède à Roundcube via Nginx → Roundcube se connecte en IMAP/SMTP à Dovecot/Postfix en local → l'authentification passe par LDAP (via Dovecot)
5. **Réponse automatique vacances :** Un cron synchronise `hrcVacationMessage` depuis LDAP → génère des scripts Sieve par utilisateur → Dovecot les applique à la livraison
6. **Alias/redirection :** Postfix interroge LDAP pour `hrcMailAlternateAddress` et `hrcMailForwardingAddress` → redistribue en conséquence
7. **Listes de diffusion :** Postfix interroge LDAP pour `hrcGroupMail` → développe les `memberUid` en `utilisateur@domaine` → livre à chaque membre

## Réseau et ports

| Service | Port | Protocole | Authentification |
|---------|------|-----------|------------------|
| SMTP | 25 | STARTTLS | Aucune (réseau local) |
| Submission | 587 | STARTTLS requis | SASL (bind LDAP) |
| SMTPS | 465 | TLS implicite | SASL (bind LDAP) |
| IMAP | 143 | STARTTLS | Bind LDAP |
| IMAPS | 993 | TLS implicite | Bind LDAP |
| HTTP | 80 | Redirection → HTTPS | — |
| HTTPS | 443 | TLS (auto-signé) | Via Roundcube → IMAP |

Le certificat TLS est **auto-signé**, généré lors du provisioning avec les SANs : `mail1.heracles.local`, `mail.heracles.local`, `smtp.heracles.local`, `imap.heracles.local`.

### Enregistrements DNS

Les enregistrements suivants sont créés automatiquement par le script `setup-demo-users.sh` via l'API DNS :

| Nom | Type | Valeur |
|-----|------|--------|
| `mail1` | A | 192.168.56.22 |
| `mail` | CNAME | mail1.heracles.local. |
| `@` | MX | 10 mail1.heracles.local. |
| `22` (zone reverse) | PTR | mail1.heracles.local. |

## Installation

### Prérequis

1. Infrastructure Docker démarrée (`make up-infra`)
2. LDAP initialisé avec les schémas (dont `hrc-mail.schema`)
3. Serveur DNS (`ns1`) opérationnel
4. Utilisateurs de démo créés via l'API avec le plugin mail activé

### Démarrer la VM

```bash
cd demo

# Démarrer uniquement mail1
vagrant up mail1 --provider=libvirt

# Ou démarrer toutes les VMs
vagrant up
```

Le provisioning exécute 11 étapes automatiquement :

1. Installation des paquets (Postfix, Dovecot, Nginx, PHP-FPM, Roundcube...)
2. Création de l'utilisateur `vmail` et du répertoire des boîtes aux lettres
3. Génération du certificat TLS auto-signé
4. Configuration de Postfix (SMTP, Submission, SMTPS, requêtes LDAP)
5. Configuration de Dovecot (IMAP, LMTP, authentification LDAP, Sieve)
6. Mise en place des répertoires et scripts Sieve
7. Installation du cron de synchronisation vacances LDAP
8. Démarrage des services de messagerie
9. Configuration de Roundcube Webmail (SQLite, plugins)
10. Configuration de Nginx (frontal HTTPS, PHP-FPM)
11. Vérification de tous les services

## Activation de la messagerie

L'activation est réalisée automatiquement par `setup-demo-users.sh`, mais peut aussi être faite manuellement :

### Obtenir un token API

```bash
export TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "hrc-admin", "password": "hrc-admin-secret"}' | jq -r '.access_token')
```

### Activer la messagerie pour un utilisateur

```bash
curl -X POST "http://localhost:8000/api/v1/mail/users/testuser/activate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mail": "testuser@heracles.local",
    "mailServer": "mail1.heracles.local",
    "quotaMb": 1024,
    "alternateAddresses": ["tuser@heracles.local"]
  }'
```

### Activer une liste de diffusion

```bash
# Créer un groupe groupOfNames
curl -X POST "http://localhost:8000/api/v1/groups" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"cn": "developers-ml", "description": "Liste de diffusion développeurs"}'

# Ajouter des membres
curl -X POST "http://localhost:8000/api/v1/groups/developers-ml/members" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"uid": "testuser"}'

# Activer la messagerie sur le groupe
curl -X POST "http://localhost:8000/api/v1/mail/groups/developers-ml/activate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mail": "developers@heracles.local",
    "mailServer": "mail1.heracles.local",
    "alternateAddresses": ["dev-team@heracles.local"]
  }'
```

### Comptes de démo préconfigurés

| Utilisateur | Email | Alias | Quota |
|-------------|-------|-------|-------|
| testuser | testuser@heracles.local | tuser@heracles.local | 1 Go |
| devuser | devuser@heracles.local | dev@heracles.local | 512 Mo |
| opsuser | opsuser@heracles.local | ops@heracles.local | 1 Go |

| Liste | Email | Alias | Membres |
|-------|-------|-------|---------|
| developers-ml | developers@heracles.local | dev-team@heracles.local | testuser, devuser |

## Webmail Roundcube

### Accès

- **URL :** `https://mail.heracles.local`
- **Résolution DNS :** `mail.heracles.local` → CNAME → `mail1.heracles.local` → 192.168.56.22

> ⚠️ Le certificat est auto-signé : acceptez l'exception de sécurité dans votre navigateur.

### Connexion

Utilisez le nom d'utilisateur (sans le domaine) et le mot de passe LDAP :

| Utilisateur | Mot de passe |
|-------------|--------------|
| testuser | Testpassword123 |
| devuser | Devpassword123 |
| opsuser | Opspassword123 |

### Fonctionnalités

- **Thème :** Elastic (responsive, compatible mobile)
- **Plugins activés :** Archive, Téléchargement ZIP, ManageSieve (filtres côté serveur)
- **Stockage :** SQLite (local à la VM)
- **Pièces jointes :** jusqu'à 25 Mo
- **Session :** expiration après 30 minutes d'inactivité

### Chaîne d'authentification

```
Navigateur → Roundcube → IMAP (localhost:143) → Dovecot → Bind LDAP (192.168.56.1:389)
```

Roundcube ne gère aucun mot de passe — il délègue entièrement l'authentification à Dovecot, qui effectue un bind LDAP direct avec les identifiants de l'utilisateur.

## Tests et validation

### Depuis la VM mail1

```bash
vagrant ssh mail1

# 1. Envoyer un email de test (non authentifié, réseau local)
swaks --to testuser@heracles.local \
      --from admin@heracles.local \
      --server localhost \
      --body "Bonjour depuis le serveur Heracles !"

# 2. Envoyer via submission (authentifié avec STARTTLS)
swaks --to devuser@heracles.local \
      --from testuser@heracles.local \
      --server localhost:587 --tls \
      --auth-user testuser --auth-password Testpassword123 \
      --body "Test d'envoi authentifié"

# 3. Envoyer à la liste de diffusion
swaks --to developers@heracles.local \
      --from testuser@heracles.local \
      --server localhost:587 --tls \
      --auth-user testuser --auth-password Testpassword123 \
      --body "Message à tous les développeurs"

# 4. Vérifier la boîte aux lettres via doveadm
sudo doveadm mailbox list -u testuser
sudo doveadm fetch -u testuser "subject" mailbox INBOX

# 5. Tester la connexion IMAP
openssl s_client -connect localhost:993 -quiet <<< "a LOGIN testuser Testpassword123
b SELECT INBOX
c FETCH 1 BODY[HEADER.FIELDS (Subject From)]
d LOGOUT"

# 6. Vérifier les lookups LDAP de Postfix
postmap -q "testuser@heracles.local" ldap:/etc/postfix/ldap-virtual-mailbox.cf
postmap -q "tuser@heracles.local" ldap:/etc/postfix/ldap-virtual-alias.cf

# 7. Consulter les logs
sudo tail -f /var/log/mail.log
```

### Depuis server1 ou workstation1

```bash
vagrant ssh server1

# Installer un client mail
sudo apt-get install -y mutt swaks

# Envoyer un email via le serveur de messagerie
swaks --to testuser@heracles.local \
      --from devuser@heracles.local \
      --server mail1.heracles.local:587 --tls \
      --auth-user devuser --auth-password Devpassword123

# Lire le courrier avec mutt (IMAP)
mutt -f imaps://devuser:Devpassword123@mail1.heracles.local/INBOX
```

### Tester le webmail

1. Ouvrir `https://mail.heracles.local` dans un navigateur
2. Accepter le certificat auto-signé
3. Se connecter avec `testuser` / `Testpassword123`
4. Vérifier la présence des emails de test dans la boîte de réception
5. Envoyer un email à `devuser@heracles.local` et vérifier la réception

### Vérifier la résolution DNS

```bash
# Depuis l'hôte ou une VM avec le résolveur configuré
dig @192.168.56.20 mail.heracles.local +short
# Attendu : mail1.heracles.local. → 192.168.56.22

dig @192.168.56.20 heracles.local MX +short
# Attendu : 10 mail1.heracles.local.

dig @192.168.56.20 -x 192.168.56.22 +short
# Attendu : mail1.heracles.local.
```

## Intégration LDAP

Le serveur de messagerie utilise deux objectClasses LDAP personnalisés gérés par le plugin mail de Heracles :

### hrcMailAccount (utilisateur)

| Attribut | Utilisation |
|----------|-------------|
| `mail` (OBLIGATOIRE) | Email principal, utilisé pour le virtual mailbox map |
| `hrcMailServer` | Nom d'hôte du serveur de messagerie |
| `hrcMailQuota` | Quota en Mo |
| `hrcMailAlternateAddress` | Adresses alias → redirigées vers l'adresse principale |
| `hrcMailForwardingAddress` | Adresses de redirection externe |
| `hrcMailDeliveryMode` | `V`=vacances, `L`=local uniquement, `I`=redirection uniquement |
| `hrcVacationMessage` | Texte de réponse automatique (synchronisé vers Sieve) |
| `hrcVacationStart` / `hrcVacationStop` | Période de vacances (AAAAMMJJ) |

### hrcGroupMail (liste de diffusion)

| Attribut | Utilisation |
|----------|-------------|
| `mail` (OBLIGATOIRE) | Adresse de la liste, utilisée pour le group mail map |
| `hrcMailServer` | Nom d'hôte du serveur de messagerie |
| `hrcMailAlternateAddress` | Adresses alias pour la liste |
| `hrcMailForwardingAddress` | Redirection externe pour la liste |
| `hrcGroupMailLocalOnly` | Restreindre les expéditeurs au domaine local |

## Dépannage

### L'utilisateur ne peut pas se connecter à IMAP

1. **Vérifier que hrcMailAccount est activé :**
   ```bash
   ldapsearch -x -H ldap://192.168.56.1 -D "cn=admin,dc=heracles,dc=local" \
     -w admin_secret -b "ou=people,dc=heracles,dc=local" \
     "(uid=testuser)" objectClass mail
   ```
   L'objectClass `hrcMailAccount` doit apparaître dans la liste.

2. **Tester le bind LDAP directement :**
   ```bash
   ldapwhoami -x -H ldap://192.168.56.1 \
     -D "uid=testuser,ou=people,dc=heracles,dc=local" \
     -w Testpassword123
   ```

3. **Vérifier les logs d'authentification Dovecot :**
   ```bash
   sudo journalctl -u dovecot -f
   # Ou activer le mode debug :
   # Ajouter auth_debug=yes dans /etc/dovecot/dovecot.conf et redémarrer
   ```

### Le courrier n'est pas livré

1. **Vérifier le lookup LDAP de Postfix :**
   ```bash
   postmap -q "testuser@heracles.local" ldap:/etc/postfix/ldap-virtual-mailbox.cf
   # Attendu : heracles.local/testuser/Maildir/
   ```

2. **Consulter les logs mail :**
   ```bash
   sudo tail -50 /var/log/mail.log | grep -E "status=|reject|error"
   ```

3. **Vérifier la boîte aux lettres sur le disque :**
   ```bash
   sudo ls -la /var/mail/vhosts/heracles.local/testuser/Maildir/new/
   ```

### Avertissements de certificat TLS

C'est normal — le certificat est auto-signé. Les clients doivent être configurés pour l'accepter dans le cadre de la démo. Pour inspecter le certificat :

```bash
openssl s_client -connect 192.168.56.22:993 -showcerts </dev/null 2>/dev/null | \
  openssl x509 -noout -subject -issuer -dates
```

### La réponse automatique vacances ne fonctionne pas

1. **Vérifier les attributs LDAP de vacances :**
   ```bash
   ldapsearch -x -H ldap://192.168.56.1 -D "cn=admin,dc=heracles,dc=local" \
     -w admin_secret -b "ou=people,dc=heracles,dc=local" \
     "(uid=testuser)" hrcMailDeliveryMode hrcVacationMessage
   ```
   `hrcMailDeliveryMode` doit contenir `V` et `hrcVacationMessage` ne doit pas être vide.

2. **Vérifier que le script Sieve a été synchronisé :**
   ```bash
   sudo ls -la /var/mail/vhosts/heracles.local/testuser/sieve/
   sudo cat /var/mail/vhosts/heracles.local/testuser/.dovecot.sieve
   ```

3. **Forcer la synchronisation :**
   ```bash
   sudo /usr/local/bin/ldap-vacation-sync.sh
   ```

### Le webmail ne charge pas

1. **Vérifier que Nginx et PHP-FPM sont actifs :**
   ```bash
   systemctl status nginx php8.2-fpm
   ```

2. **Vérifier les logs Nginx :**
   ```bash
   sudo tail -20 /var/log/nginx/roundcube-error.log
   ```

3. **Vérifier les logs Roundcube :**
   ```bash
   sudo tail -20 /var/lib/roundcube/logs/errors.log
   ```

4. **Vérifier la résolution DNS :**
   ```bash
   dig @192.168.56.20 mail.heracles.local +short
   # Doit résoudre vers 192.168.56.22
   ```

## Référence des fichiers

| Fichier | Rôle |
|---------|------|
| `/etc/postfix/main.cf` | Configuration principale de Postfix |
| `/etc/postfix/master.cf` | Définitions des services Postfix |
| `/etc/postfix/ldap-virtual-mailbox.cf` | Lookup LDAP : email → chemin de boîte |
| `/etc/postfix/ldap-virtual-alias.cf` | Lookup LDAP : alias → email principal |
| `/etc/postfix/ldap-virtual-forward.cf` | Lookup LDAP : email → adresses de redirection |
| `/etc/postfix/ldap-group-mail.cf` | Lookup LDAP : email de groupe → expansion des membres |
| `/etc/dovecot/dovecot.conf` | Configuration principale de Dovecot |
| `/etc/dovecot/dovecot-ldap.conf.ext` | Auth LDAP Dovecot (bind direct) |
| `/etc/dovecot/sieve/` | Scripts Sieve globaux |
| `/var/mail/vhosts/heracles.local/` | Stockage des boîtes aux lettres virtuelles |
| `/usr/local/bin/ldap-vacation-sync.sh` | Synchronisation LDAP → Sieve (vacances) |
| `/etc/ssl/certs/mail-heracles.local.pem` | Certificat TLS |
| `/etc/ssl/private/mail-heracles.local.key` | Clé privée TLS |
| `/etc/nginx/sites-available/roundcube` | Configuration Nginx pour le webmail |
| `/etc/roundcube/config.inc.php` | Configuration de Roundcube |
| `/var/lib/roundcube/db/roundcube.db` | Base de données SQLite de Roundcube |
