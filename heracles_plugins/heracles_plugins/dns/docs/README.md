# Plugin DNS - Documentation

## Vue d'ensemble

Le plugin DNS gère les zones et enregistrements DNS via LDAP. Il s'intègre avec BIND9 via le backend DLZ (Dynamically Loadable Zones).

## Architecture

```
┌─────────────────┐      REST API       ┌─────────────────┐
│   Heracles UI   │ ──────────────────▶ │   DNS Plugin    │
│  (Page DNS)     │                     │   (FastAPI)     │
└─────────────────┘                     └────────┬────────┘
                                                 │ LDAP
                                                 ▼
┌─────────────────┐      DLZ LDAP       ┌─────────────────┐
│     BIND9       │ ◀─────────────────▶ │    OpenLDAP     │
│                 │                     │   (dNSZone)     │
└────────┬────────┘                     └─────────────────┘
         │
         │ DNS Protocol
         ▼
┌─────────────────┐
│    Clients      │
│  (dig, nslookup)│
└─────────────────┘
```

BIND9 lit directement les zones depuis LDAP via le module DLZ. Toute modification dans LDAP est immédiatement visible.

## Types de zones

| Type | Usage | Exemple |
|------|-------|---------|
| `forward` | Nom → IP | `example.com` |
| `reverse-ipv4` | IP → Nom | `1.168.192.in-addr.arpa` |
| `reverse-ipv6` | IPv6 → Nom | `8.b.d.0.1.0.0.2.ip6.arpa` |

## Types d'enregistrements

| Type | Usage | Exemple |
|------|-------|---------|
| `A` | IPv4 | `192.168.1.10` |
| `AAAA` | IPv6 | `2001:db8::1` |
| `CNAME` | Alias | `www.example.com.` |
| `MX` | Mail | `10 mail.example.com.` |
| `NS` | Nameserver | `ns1.example.com.` |
| `PTR` | Reverse | `server.example.com.` |
| `TXT` | Texte | `v=spf1 mx -all` |
| `SRV` | Service | `10 5 389 ldap.example.com.` |

## ObjectClasses LDAP

| ObjectClass | Usage |
|-------------|-------|
| `dNSZone` | Zone DNS |
| `dNSRRset` | Resource Record Set |

## Schémas de données

### DnsZoneCreate
Création d'une zone.

```python
{
    "zoneName": "example.com",
    "soaPrimaryNs": "ns1.example.com.",
    "soaAdminEmail": "admin.example.com.",
    "defaultTtl": 3600,
    "soaRefresh": 10800,
    "soaRetry": 3600,
    "soaExpire": 604800,
    "soaMinimum": 86400
}
```

### DnsZoneRead
Lecture d'une zone.

```python
{
    "dn": "ou=example.com,ou=dns,dc=heracles,dc=local",
    "zoneName": "example.com",
    "zoneType": "forward",
    "soa": {
        "primaryNs": "ns1.example.com.",
        "adminEmail": "admin.example.com.",
        "serial": 2026013001,
        "refresh": 10800,
        "retry": 3600,
        "expire": 604800,
        "minimum": 86400
    },
    "defaultTtl": 3600,
    "recordCount": 15
}
```

### DnsRecordCreate
Création d'un enregistrement.

```python
{
    "name": "www",
    "recordType": "A",
    "value": "192.168.1.10",
    "ttl": 3600,
    "priority": null  # Requis pour MX et SRV
}
```

## Endpoints API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/dns/zones` | Lister les zones |
| GET | `/dns/zones/{name}` | Lire une zone |
| POST | `/dns/zones` | Créer une zone |
| PUT | `/dns/zones/{name}` | Modifier une zone |
| DELETE | `/dns/zones/{name}` | Supprimer une zone |
| GET | `/dns/zones/{name}/records` | Lister les enregistrements |
| POST | `/dns/zones/{name}/records` | Créer un enregistrement |
| PUT | `/dns/zones/{name}/records/{record}` | Modifier un enregistrement |
| DELETE | `/dns/zones/{name}/records/{record}` | Supprimer un enregistrement |

## SOA (Start of Authority)

Chaque zone a un enregistrement SOA obligatoire :

| Champ | Description | Valeur typique |
|-------|-------------|----------------|
| `primaryNs` | Nameserver primaire | `ns1.example.com.` |
| `adminEmail` | Email admin (@ → .) | `admin.example.com.` |
| `serial` | Numéro de série | `2026013001` (YYYYMMDDNN) |
| `refresh` | Intervalle refresh | `10800` (3h) |
| `retry` | Intervalle retry | `3600` (1h) |
| `expire` | Expiration | `604800` (1 semaine) |
| `minimum` | TTL négatif | `86400` (1 jour) |

Le serial est auto-incrémenté à chaque modification.

## Configuration BIND9 DLZ

```
# /etc/bind/named.conf.local
dlz "ldap zone" {
    database "ldap 2
        v3 simple {cn=admin,dc=example,dc=com} {password}
        ldap://127.0.0.1/ou=dns,dc=example,dc=com???
        (objectClass=dNSZone)";
};
```

## Structure LDAP

```
ou=dns,dc=example,dc=com
├── ou=example.com                    # Zone forward
│   ├── objectClass: dNSZone
│   ├── zoneName: example.com
│   ├── sOARecord: ns1.example.com. admin.example.com. 2026013001 ...
│   ├── relativeDomainName: @
│   │   ├── aRecord: 192.168.1.1      # @ = apex
│   │   ├── mXRecord: 10 mail.example.com.
│   │   └── nSRecord: ns1.example.com.
│   ├── relativeDomainName: www
│   │   └── aRecord: 192.168.1.10
│   ├── relativeDomainName: mail
│   │   └── aRecord: 192.168.1.20
│   └── relativeDomainName: ns1
│       └── aRecord: 192.168.1.2
│
└── ou=1.168.192.in-addr.arpa         # Zone reverse
    ├── objectClass: dNSZone
    ├── relativeDomainName: 10
    │   └── pTRRecord: www.example.com.
    └── relativeDomainName: 20
        └── pTRRecord: mail.example.com.
```

## Workflow typique

1. **Créer une zone**
   ```bash
   POST /dns/zones {
     "zoneName": "example.com",
     "soaPrimaryNs": "ns1.example.com.",
     "soaAdminEmail": "admin.example.com."
   }
   ```

2. **Ajouter des enregistrements**
   ```bash
   POST /dns/zones/example.com/records {
     "name": "www",
     "recordType": "A",
     "value": "192.168.1.10"
   }
   ```

3. **Tester la résolution**
   ```bash
   dig @ns1.example.com www.example.com
   ```

## Validation

- **Noms** : Format DNS valide (labels, longueur max 253)
- **TTL** : Entier positif
- **Priority** : Requis pour MX et SRV
- **FQDN** : Doit se terminer par `.` pour les valeurs absolues
