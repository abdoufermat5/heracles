# Plugin SSH - Documentation

## Vue d'ensemble

Le plugin SSH gère les clés publiques SSH des utilisateurs. Il permet l'authentification par clé SSH via LDAP.

## Architecture

```
┌─────────────────┐      REST API       ┌─────────────────┐
│   Heracles UI   │ ──────────────────▶ │   SSH Plugin    │
│  (Onglet SSH)   │                     │   (FastAPI)     │
└─────────────────┘                     └────────┬────────┘
                                                 │ LDAP
                                                 ▼
┌─────────────────┐    AuthorizedKeys   ┌─────────────────┐
│   Client SSH    │ ◀─────────────────▶ │    OpenLDAP     │
│   (sshd)        │   via LDAP lookup   │ (ldapPublicKey) │
└─────────────────┘                     └─────────────────┘
```

Le serveur SSH interroge LDAP pour récupérer les clés autorisées via la directive `AuthorizedKeysCommand` dans `sshd_config`.

## ObjectClass LDAP

| ObjectClass | Type | Usage |
|-------------|------|-------|
| `ldapPublicKey` | Auxiliary | Stockage des clés SSH |

Attribut: `sshPublicKey` (multi-valué)

## Types de clés supportés

| Type | Bits | Recommandation |
|------|------|----------------|
| `ssh-ed25519` | 256 | Recommandé |
| `ssh-rsa` | 2048-4096 | Acceptable |
| `ecdsa-sha2-nistp256` | 256 | Acceptable |
| `ecdsa-sha2-nistp384` | 384 | Acceptable |
| `ecdsa-sha2-nistp521` | 521 | Acceptable |
| `sk-ssh-ed25519` | - | Clé FIDO2 |
| `sk-ecdsa-sha2-nistp256` | - | Clé FIDO2 |

## Schémas de données

### SSHKeyCreate
Ajout d'une clé SSH.

```python
{
    "key": "ssh-ed25519 AAAAC3Nz... user@laptop",
    "comment": "Laptop personnel"  # Optionnel
}
```

### SSHKeyRead
Lecture d'une clé SSH avec métadonnées.

```python
{
    "key": "ssh-ed25519 AAAAC3Nz... user@laptop",
    "keyType": "ssh-ed25519",
    "fingerprint": "SHA256:abcd1234...",
    "comment": "user@laptop",
    "bits": null,  # Null pour ed25519
    "addedAt": "2026-01-15T10:30:00Z"
}
```

### UserSSHStatus
Statut SSH complet d'un utilisateur.

```python
{
    "uid": "jdoe",
    "dn": "uid=jdoe,ou=people,dc=example,dc=com",
    "hasSsh": true,
    "keys": [...],
    "keyCount": 2
}
```

## Endpoints API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/ssh/users/{uid}` | Statut SSH d'un user |
| POST | `/ssh/users/{uid}/activate` | Activer SSH (ajoute objectClass) |
| DELETE | `/ssh/users/{uid}/deactivate` | Désactiver SSH |
| POST | `/ssh/users/{uid}/keys` | Ajouter une clé |
| DELETE | `/ssh/users/{uid}/keys/{fingerprint}` | Supprimer une clé |
| PUT | `/ssh/users/{uid}/keys` | Remplacer toutes les clés |

## Validation des clés

Le plugin valide :
1. **Format** : `type base64-key [comment]`
2. **Type** : Doit être dans la liste supportée
3. **Base64** : Décodage valide
4. **Unicité** : Pas de doublon (par fingerprint)

## Configuration sshd

Pour que le serveur SSH utilise les clés LDAP :

```bash
# /etc/ssh/sshd_config
AuthorizedKeysCommand /usr/local/bin/ldap-ssh-keys %u
AuthorizedKeysCommandUser nobody
```

Script `/usr/local/bin/ldap-ssh-keys` :
```bash
#!/bin/bash
ldapsearch -x -H ldap://ldap.example.com \
  -b "ou=people,dc=example,dc=com" \
  "(uid=$1)" sshPublicKey | grep "^sshPublicKey:" | cut -d' ' -f2-
```

## Workflow typique

1. **Générer une clé SSH (côté client)**
   ```bash
   ssh-keygen -t ed25519 -C "jdoe@laptop"
   ```

2. **Activer SSH sur l'utilisateur**
   ```bash
   POST /ssh/users/jdoe/activate
   ```

3. **Ajouter la clé publique**
   ```bash
   POST /ssh/users/jdoe/keys {
     "key": "ssh-ed25519 AAAAC3Nz... jdoe@laptop"
   }
   ```

4. **Se connecter**
   ```bash
   ssh jdoe@server.example.com
   ```

## Fingerprint

Le fingerprint SHA256 est calculé sur les données base64 de la clé :

```python
fingerprint = base64(sha256(base64_decode(key_data)))
# Exemple: SHA256:uNiVztksCsDhcc0u9e8BujQXVUpKZIDTMczCvj3tD2s
```

## Structure LDAP résultante

```
uid=jdoe,ou=people,dc=example,dc=com
├── objectClass: inetOrgPerson
├── objectClass: ldapPublicKey
├── uid: jdoe
├── sshPublicKey: ssh-ed25519 AAAAC3Nz... laptop
└── sshPublicKey: ssh-rsa AAAAB3Nz... workstation
```
