# Architecture de l'environnement de démonstration

## Vue d'ensemble

L'environnement de démonstration Heracles est composé de plusieurs couches qui simulent un environnement de production pour la gestion centralisée d'identités et de services réseau.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HÔTE PHYSIQUE                                   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    DOCKER (Infrastructure centrale)                   │   │
│  │                                                                       │   │
│  │   ┌───────────┐  ┌──────────┐  ┌─────────┐  ┌─────────────────────┐  │   │
│  │   │  OpenLDAP │  │PostgreSQL│  │  Redis  │  │     phpLDAPadmin    │  │   │
│  │   │  :389/636 │  │  :5432   │  │  :6379  │  │       :8080         │  │   │
│  │   └─────┬─────┘  └────┬─────┘  └────┬────┘  └─────────────────────┘  │   │
│  │         │             │             │                                 │   │
│  │   ┌─────┴─────────────┴─────────────┴───────────────────────────┐    │   │
│  │   │                    HERACLES API (:8000)                      │    │   │
│  │   │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────┐  │    │   │
│  │   │  │  Users  │ │ Groups  │ │  Sudo   │ │   SSH   │ │  DNS  │  │    │   │
│  │   │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └───────┘  │    │   │
│  │   │  ┌─────────┐ ┌─────────┐ ┌─────────┐                        │    │   │
│  │   │  │  DHCP   │ │ Systems │ │   ...   │                        │    │   │
│  │   │  └─────────┘ └─────────┘ └─────────┘                        │    │   │
│  │   └─────────────────────────────────────────────────────────────┘    │   │
│  │                                                                       │   │
│  └───────────────────────────────┬───────────────────────────────────────┘   │
│                                  │                                           │
│  ┌───────────────────────────────┼───────────────────────────────────────┐   │
│  │         RÉSEAU VIRTUALBOX (vboxnet0: 192.168.56.0/24)                 │   │
│  │                               │                                        │   │
│  │   ┌──────────────┐  ┌─────────┴────────┐  ┌──────────────────────┐    │   │
│  │   │    ns1       │  │   Hôte Docker    │  │      dhcp1           │    │   │
│  │   │ 192.168.56.20│  │  192.168.56.1    │  │   192.168.56.21      │    │   │
│  │   │   BIND9      │  │    (Bridge)      │  │    ISC DHCP          │    │   │
│  │   └──────┬───────┘  └──────────────────┘  └──────────┬───────────┘    │   │
│  │          │                                           │                 │   │
│  │          │         ┌──────────────┐                  │                 │   │
│  │          └─────────┤   server1    ├──────────────────┘                 │   │
│  │                    │192.168.56.10 │                                    │   │
│  │                    │    SSSD      │                                    │   │
│  │                    └──────┬───────┘                                    │   │
│  │                           │                                            │   │
│  │                    ┌──────┴───────┐                                    │   │
│  │                    │ workstation1 │                                    │   │
│  │                    │192.168.56.11 │                                    │   │
│  │                    │    SSSD      │                                    │   │
│  │                    └──────────────┘                                    │   │
│  │                                                                        │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Flux de données

### 1. Authentification utilisateur (SSH)

```
┌──────────┐     SSH      ┌──────────┐    LDAP Query   ┌──────────┐
│  Client  │ ────────────▶│ server1  │ ───────────────▶│ OpenLDAP │
│          │              │  (SSSD)  │                  │          │
└──────────┘              └──────────┘                  └──────────┘
                               │
                               │ AuthorizedKeysCommand
                               ▼
                          ┌──────────┐
                          │   LDAP   │
                          │ (sshKey) │
                          └──────────┘
```

**Étapes détaillées :**
1. L'utilisateur initie une connexion SSH vers `server1`
2. SSHD exécute `AuthorizedKeysCommand` pour récupérer les clés
3. Le script interroge LDAP pour obtenir `sshPublicKey` de l'utilisateur
4. Si la clé correspond, l'authentification réussit
5. SSSD valide l'utilisateur via NSS/PAM

### 2. Résolution DNS

```
┌──────────┐    DNS Query    ┌──────────┐   LDAP Query   ┌──────────┐
│  Client  │ ───────────────▶│   ns1    │ ──────────────▶│ OpenLDAP │
│          │                 │ (BIND9)  │                 │          │
└──────────┘                 └──────────┘                 └──────────┘
                                  │
                                  │ DLZ (Dynamic Loadable Zone)
                                  ▼
                             ┌──────────┐
                             │   Zone   │
                             │  Records │
                             └──────────┘
```

**Configuration BIND DLZ :**
- BIND utilise le backend LDAP via `dlz_ldap_dynamic`
- Les zones sont stockées sous `ou=dns,dc=heracles,dc=local`
- Les enregistrements A, PTR, CNAME, MX, etc. sont des entrées LDAP

### 3. Attribution DHCP

```
┌──────────┐   DHCPDISCOVER   ┌──────────┐   Sync Script   ┌──────────┐
│  Client  │ ────────────────▶│  dhcp1   │ ◀──────────────▶│ OpenLDAP │
│  (eth1)  │                  │(ISC DHCP)│                  │          │
└──────────┘                  └──────────┘                  └──────────┘
     │                             │
     │      DHCPOFFER              │
     ◀─────────────────────────────┘
```

**Synchronisation LDAP → DHCP :**
1. Un cron job exécute `ldap-dhcp-sync.sh` périodiquement
2. Le script récupère la configuration DHCP depuis LDAP
3. Il génère `/etc/dhcp/dhcpd.conf`
4. Il recharge ISC DHCP si des changements sont détectés

## Détails des composants

### OpenLDAP

**Structure DIT (Directory Information Tree) :**

```
dc=heracles,dc=local
├── cn=admin                    # Administrateur LDAP
├── ou=users                    # Utilisateurs
│   ├── uid=hrc-admin           # Admin Heracles
│   ├── uid=testuser            # Utilisateur de test
│   ├── uid=devuser             # Développeur
│   └── uid=opsuser             # Opérations
├── ou=groups                   # Groupes
│   ├── cn=admins
│   ├── cn=developers
│   └── cn=ops
├── ou=sudoers                  # Règles Sudo
│   ├── cn=defaults
│   ├── cn=testuser_sudo
│   ├── cn=devuser_sudo
│   └── cn=opsuser_sudo
├── ou=dns                      # Zones DNS
│   ├── ou=heracles.local
│   │   └── [enregistrements]
│   └── ou=56.168.192.in-addr.arpa
│       └── [enregistrements PTR]
├── ou=dhcp                     # Configuration DHCP
│   └── cn=demo-dhcp
│       ├── cn=192.168.56.0     # Subnet
│       │   ├── cn=dynamic-pool # Pool
│       │   └── cn=server1      # Réservation
│       └── ...
└── ou=systems                  # Inventaire systèmes
    ├── cn=server1
    └── cn=workstation1
```

**Schémas LDAP utilisés :**

| Schéma | Objectif |
|--------|----------|
| `inetOrgPerson` | Attributs utilisateur standard |
| `posixAccount` | UID, GID, home directory, shell |
| `shadowAccount` | Expiration mot de passe |
| `ldapPublicKey` | Clés SSH (`sshPublicKey`) |
| `sudoRole` | Règles sudo |
| `dnsZone`, `dnsRRset` | Zones et enregistrements DNS |
| `dhcpService`, `dhcpSubnet`, `dhcpHost` | Configuration DHCP |

### Heracles API

**Plugins chargés :**

| Plugin | Endpoint | Description |
|--------|----------|-------------|
| Core | `/api/v1/users`, `/api/v1/groups` | Gestion identités |
| SSH | `/api/v1/users/{uid}/ssh` | Clés SSH |
| Sudo | `/api/v1/sudo/rules` | Règles sudo |
| DNS | `/api/v1/dns/zones` | Zones DNS |
| DHCP | `/api/v1/dhcp` | Services DHCP |
| Systems | `/api/v1/systems` | Inventaire |

**Authentification :**
- JWT tokens via `/api/v1/auth/login`
- Tokens de durée configurable (défaut: 30 min)
- Refresh tokens pour renouvellement

### Machines virtuelles

#### ns1 (Serveur DNS)

| Composant | Configuration |
|-----------|---------------|
| OS | Ubuntu 22.04 |
| RAM | 512 MB |
| Réseau | eth0: NAT, eth1: 192.168.56.20 |
| Services | BIND9 avec DLZ LDAP |

**Fichiers clés :**
- `/etc/bind/named.conf.local` - Configuration zones
- `/etc/bind/named.conf.options` - Options BIND
- `/var/log/named/query.log` - Logs requêtes

#### dhcp1 (Serveur DHCP)

| Composant | Configuration |
|-----------|---------------|
| OS | Ubuntu 22.04 |
| RAM | 512 MB |
| Réseau | eth0: NAT, eth1: 192.168.56.21 |
| Services | ISC DHCP Server |

**Fichiers clés :**
- `/etc/dhcp/dhcpd.conf` - Configuration (générée)
- `/etc/dhcp/ldap-dhcp-sync.sh` - Script de synchronisation
- `/var/lib/dhcp/dhcpd.leases` - Baux actifs
- `/var/log/syslog` - Logs DHCP

#### server1 / workstation1 (Clients SSSD)

| Composant | Configuration |
|-----------|---------------|
| OS | Ubuntu 22.04 |
| RAM | 1 GB |
| Réseau | eth0: NAT, eth1: 192.168.56.10/11 |
| Services | SSSD, SSH, Sudo |

**Fichiers clés :**
- `/etc/sssd/sssd.conf` - Configuration SSSD
- `/etc/ssh/sshd_config` - Configuration SSH
- `/etc/nsswitch.conf` - NSS avec sss
- `/etc/pam.d/common-*` - PAM avec pam_sss

## Ports et protocoles

| Service | Port | Protocole | Direction |
|---------|------|-----------|-----------|
| LDAP | 389 | TCP | Docker → VMs |
| LDAPS | 636 | TCP | Docker → VMs |
| DNS | 53 | UDP/TCP | VMs → ns1 |
| DHCP | 67/68 | UDP | VMs ↔ dhcp1 |
| SSH | 22 | TCP | Hôte → VMs |
| API | 8000 | TCP | Hôte → Docker |
| phpLDAPadmin | 8080 | TCP | Hôte → Docker |

## Sécurité

### Credentials par défaut (DEMO UNIQUEMENT)

| Service | Utilisateur | Mot de passe |
|---------|-------------|--------------|
| LDAP Admin | `cn=admin,dc=heracles,dc=local` | `admin_secret` |
| LDAP Config | `cn=admin,cn=config` | `config_secret` |
| PostgreSQL | `heracles` | `heracles_secret` |
| API Admin | `hrc-admin` | `hrc-admin-secret` |

> ⚠️ **ATTENTION** : Ces credentials sont destinés uniquement à la démonstration.
> En production, utilisez des secrets forts et un gestionnaire de secrets.

### Certificats TLS

Pour la démonstration, le TLS peut être désactivé. En production :
1. Générer des certificats via une CA interne
2. Configurer LDAPS (port 636)
3. Activer `ldap_id_use_start_tls = true` dans SSSD

## Extensibilité

### Ajouter une nouvelle VM

1. Modifier `Vagrantfile` :
```ruby
config.vm.define "newvm" do |node|
  node.vm.box = "ubuntu/jammy64"
  node.vm.hostname = "newvm"
  node.vm.network "private_network", ip: "192.168.56.30"
  node.vm.provision "shell", path: "provision/setup-sssd.sh"
end
```

2. Ajouter le DNS :
```bash
curl -X POST "http://localhost:8000/api/v1/dns/zones/heracles.local/records" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "newvm", "type": "A", "content": "192.168.56.30"}'
```

3. Ajouter la réservation DHCP :
```bash
curl -X POST "http://localhost:8000/api/v1/dhcp/demo-dhcp/hosts" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"cn": "newvm", "dhcpHWAddress": "ethernet AA:BB:CC:DD:EE:FF", "fixedAddress": "192.168.56.30"}'
```

### Ajouter un nouveau plugin

Voir la documentation du projet principal : `docs/05-PLUGIN-SPECIFICATION.md`
