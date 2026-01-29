# Guide DNS et DHCP

Ce guide détaille l'utilisation des plugins DNS et DHCP dans l'environnement de démonstration Heracles.

## Table des matières

1. [Plugin DNS](#plugin-dns)
   - [Architecture](#architecture-dns)
   - [Gestion des zones](#gestion-des-zones)
   - [Gestion des enregistrements](#gestion-des-enregistrements)
   - [Tests et validation](#tests-dns)
2. [Plugin DHCP](#plugin-dhcp)
   - [Architecture](#architecture-dhcp)
   - [Gestion des services](#gestion-des-services-dhcp)
   - [Subnets et pools](#subnets-et-pools)
   - [Réservations d'hôtes](#réservations-dhôtes)
   - [Synchronisation](#synchronisation-ldap-dhcp)
3. [Intégration DNS-DHCP](#intégration-dns-dhcp)

---

## Plugin DNS

### Architecture DNS

```
                                    ┌─────────────────┐
                                    │   Heracles UI   │
                                    │   (React App)   │
                                    └────────┬────────┘
                                             │ REST API
                                             ▼
┌─────────────┐                     ┌─────────────────┐
│   Client    │                     │  Heracles API   │
│  (dig, etc) │                     │   DNS Plugin    │
└──────┬──────┘                     └────────┬────────┘
       │                                      │
       │ DNS Query                           │ LDAP
       ▼                                      ▼
┌─────────────┐    DLZ LDAP          ┌─────────────────┐
│    BIND9    │◀────────────────────▶│    OpenLDAP     │
│    (ns1)    │                      │                 │
└─────────────┘                      └─────────────────┘
```

**Composants :**
- **Heracles DNS Plugin** : API REST pour gérer zones et enregistrements
- **OpenLDAP** : Stockage persistant des données DNS
- **BIND9 DLZ** : Serveur DNS avec backend LDAP dynamique

### Gestion des zones

#### Lister les zones

```bash
# Via API
curl -s "http://localhost:8000/api/v1/dns/zones" \
  -H "Authorization: Bearer $TOKEN" | jq .

# Réponse attendue
{
  "items": [
    {
      "dn": "ou=heracles.local,ou=dns,dc=heracles,dc=local",
      "zoneName": "heracles.local",
      "zoneType": "master",
      "soa": {
        "primaryNs": "ns1.heracles.local.",
        "adminEmail": "admin.heracles.local.",
        "serial": 2024010101,
        "refresh": 10800,
        "retry": 3600,
        "expire": 604800,
        "minimum": 86400
      }
    }
  ],
  "total": 1
}
```

#### Créer une zone

```bash
# Zone forward
curl -X POST "http://localhost:8000/api/v1/dns/zones" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "zoneName": "example.local",
    "zoneType": "master",
    "soa": {
      "primaryNs": "ns1.example.local.",
      "adminEmail": "admin.example.local.",
      "refresh": 10800,
      "retry": 3600,
      "expire": 604800,
      "minimum": 86400
    }
  }'

# Zone reverse
curl -X POST "http://localhost:8000/api/v1/dns/zones" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "zoneName": "100.168.192.in-addr.arpa",
    "zoneType": "master",
    "soa": {
      "primaryNs": "ns1.example.local.",
      "adminEmail": "admin.example.local."
    }
  }'
```

#### Supprimer une zone

```bash
curl -X DELETE "http://localhost:8000/api/v1/dns/zones/example.local" \
  -H "Authorization: Bearer $TOKEN"
```

### Gestion des enregistrements

#### Types d'enregistrements supportés

| Type | Description | Exemple |
|------|-------------|---------|
| A | Adresse IPv4 | `server1 → 192.168.56.10` |
| AAAA | Adresse IPv6 | `server1 → 2001:db8::1` |
| CNAME | Alias | `www → server1.heracles.local.` |
| MX | Mail exchanger | `10 mail.heracles.local.` |
| TXT | Texte | `"v=spf1 mx -all"` |
| PTR | Pointeur reverse | `10 → server1.heracles.local.` |
| NS | Serveur de noms | `ns1.heracles.local.` |
| SRV | Service | `0 5 389 ldap.heracles.local.` |

#### Lister les enregistrements

```bash
# Tous les enregistrements d'une zone
curl -s "http://localhost:8000/api/v1/dns/zones/heracles.local/records" \
  -H "Authorization: Bearer $TOKEN" | jq .

# Filtrer par type
curl -s "http://localhost:8000/api/v1/dns/zones/heracles.local/records?type=A" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

#### Créer des enregistrements

```bash
# Enregistrement A
curl -X POST "http://localhost:8000/api/v1/dns/zones/heracles.local/records" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "newserver",
    "type": "A",
    "content": "192.168.56.50",
    "ttl": 3600
  }'

# Enregistrement CNAME
curl -X POST "http://localhost:8000/api/v1/dns/zones/heracles.local/records" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "www",
    "type": "CNAME",
    "content": "server1.heracles.local."
  }'

# Enregistrement MX
curl -X POST "http://localhost:8000/api/v1/dns/zones/heracles.local/records" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "@",
    "type": "MX",
    "content": "10 mail.heracles.local.",
    "ttl": 3600
  }'

# Enregistrement PTR (zone reverse)
curl -X POST "http://localhost:8000/api/v1/dns/zones/56.168.192.in-addr.arpa/records" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "50",
    "type": "PTR",
    "content": "newserver.heracles.local."
  }'
```

#### Modifier un enregistrement

```bash
curl -X PUT "http://localhost:8000/api/v1/dns/zones/heracles.local/records/newserver" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "192.168.56.51",
    "ttl": 7200
  }'
```

#### Supprimer un enregistrement

```bash
curl -X DELETE "http://localhost:8000/api/v1/dns/zones/heracles.local/records/newserver?type=A" \
  -H "Authorization: Bearer $TOKEN"
```

### Tests DNS

#### Depuis l'hôte

```bash
# Résolution forward
dig @192.168.56.20 server1.heracles.local +short
# Attendu: 192.168.56.10

# Résolution reverse
dig @192.168.56.20 -x 192.168.56.10 +short
# Attendu: server1.heracles.local.

# Requête complète
dig @192.168.56.20 heracles.local ANY

# Test de transfert de zone (si autorisé)
dig @192.168.56.20 heracles.local AXFR
```

#### Depuis une VM

```bash
vagrant ssh server1 -c "dig ns1.heracles.local"
vagrant ssh server1 -c "nslookup dhcp1.heracles.local"
vagrant ssh server1 -c "host 192.168.56.20"
```

#### Vérifier les logs BIND

```bash
vagrant ssh ns1 -c "sudo tail -f /var/log/named/query.log"
```

---

## Plugin DHCP

### Architecture DHCP

```
                                    ┌─────────────────┐
                                    │   Heracles UI   │
                                    │   (React App)   │
                                    └────────┬────────┘
                                             │ REST API
                                             ▼
                                    ┌─────────────────┐
                                    │  Heracles API   │
                                    │   DHCP Plugin   │
                                    └────────┬────────┘
                                             │ LDAP
                                             ▼
┌─────────────┐    Sync Script       ┌─────────────────┐
│  ISC DHCP   │◀─────────────────────│    OpenLDAP     │
│   (dhcp1)   │   (ldap-dhcp-sync)   │                 │
└──────┬──────┘                      └─────────────────┘
       │
       │ DHCP Protocol
       ▼
┌─────────────┐
│   Clients   │
│(server1,etc)│
└─────────────┘
```

**Flux de données :**
1. L'administrateur modifie la configuration via l'API/UI
2. Les changements sont stockés dans LDAP
3. Un cron job ou webhook déclenche la synchronisation
4. Le script génère `dhcpd.conf` depuis LDAP
5. ISC DHCP est rechargé si nécessaire

### Gestion des services DHCP

#### Lister les services

```bash
curl -s "http://localhost:8000/api/v1/dhcp" \
  -H "Authorization: Bearer $TOKEN" | jq .

# Réponse
{
  "items": [
    {
      "dn": "cn=demo-dhcp,ou=dhcp,dc=heracles,dc=local",
      "cn": "demo-dhcp",
      "dhcpComments": "Service DHCP de démonstration",
      "objectType": "service"
    }
  ],
  "total": 1
}
```

#### Créer un service

```bash
curl -X POST "http://localhost:8000/api/v1/dhcp" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cn": "production-dhcp",
    "comments": "Service DHCP de production",
    "dhcpStatements": [
      "authoritative",
      "default-lease-time 3600",
      "max-lease-time 7200"
    ],
    "dhcpOptions": [
      "domain-name \"heracles.local\"",
      "domain-name-servers 192.168.56.20"
    ]
  }'
```

#### Obtenir les détails d'un service

```bash
curl -s "http://localhost:8000/api/v1/dhcp/demo-dhcp" \
  -H "Authorization: Bearer $TOKEN" | jq .

# Inclut: dhcpStatements, dhcpOption, etc.
```

#### Obtenir l'arborescence complète

```bash
curl -s "http://localhost:8000/api/v1/dhcp/demo-dhcp/tree" \
  -H "Authorization: Bearer $TOKEN" | jq .

# Retourne la hiérarchie: service → subnets → pools, hosts
```

### Subnets et pools

#### Lister les subnets

```bash
curl -s "http://localhost:8000/api/v1/dhcp/demo-dhcp/subnets" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

#### Créer un subnet

```bash
curl -X POST "http://localhost:8000/api/v1/dhcp/demo-dhcp/subnets" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cn": "192.168.56.0",
    "dhcpNetMask": 24,
    "comments": "Subnet de démonstration",
    "dhcpRange": ["192.168.56.100 192.168.56.199"],
    "dhcpStatements": [
      "default-lease-time 3600"
    ],
    "dhcpOptions": [
      "routers 192.168.56.1",
      "subnet-mask 255.255.255.0",
      "broadcast-address 192.168.56.255"
    ]
  }'
```

#### Modifier un subnet

```bash
curl -X PUT "http://localhost:8000/api/v1/dhcp/demo-dhcp/subnets/192.168.56.0" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dhcpRange": ["192.168.56.100 192.168.56.150"],
    "comments": "Pool réduit"
  }'
```

#### Créer un pool dans un subnet

```bash
curl -X POST "http://localhost:8000/api/v1/dhcp/demo-dhcp/subnets/192.168.56.0/pools" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cn": "dynamic-pool",
    "dhcpRange": ["192.168.56.100 192.168.56.150"],
    "comments": "Pool dynamique",
    "dhcpPermitList": ["known-clients"]
  }'
```

### Réservations d'hôtes

#### Lister les hôtes

```bash
# Tous les hôtes du service
curl -s "http://localhost:8000/api/v1/dhcp/demo-dhcp/hosts" \
  -H "Authorization: Bearer $TOKEN" | jq .

# Hôtes d'un subnet spécifique
curl -s "http://localhost:8000/api/v1/dhcp/demo-dhcp/subnets/192.168.56.0/hosts" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

#### Créer une réservation

```bash
curl -X POST "http://localhost:8000/api/v1/dhcp/demo-dhcp/hosts" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cn": "newserver",
    "dhcpHWAddress": "ethernet AA:BB:CC:DD:EE:FF",
    "fixedAddress": "192.168.56.50",
    "comments": "Nouveau serveur de test",
    "dhcpStatements": [
      "filename \"pxelinux.0\""
    ],
    "dhcpOptions": [
      "host-name \"newserver\""
    ]
  }'
```

#### Modifier une réservation

```bash
curl -X PUT "http://localhost:8000/api/v1/dhcp/demo-dhcp/hosts/newserver" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "fixedAddress": "192.168.56.51",
    "comments": "IP mise à jour"
  }'
```

#### Supprimer une réservation

```bash
curl -X DELETE "http://localhost:8000/api/v1/dhcp/demo-dhcp/hosts/newserver" \
  -H "Authorization: Bearer $TOKEN"
```

### Synchronisation LDAP → DHCP

#### Script de synchronisation

Le script `/etc/dhcp/ldap-dhcp-sync.sh` sur `dhcp1` effectue :

1. **Lecture LDAP** : Récupère la configuration du service DHCP
2. **Génération** : Crée `/etc/dhcp/dhcpd.conf.new`
3. **Validation** : Vérifie la syntaxe avec `dhcpd -t`
4. **Déploiement** : Remplace l'ancienne config si valide
5. **Rechargement** : `systemctl reload isc-dhcp-server`

#### Exécution manuelle

```bash
vagrant ssh dhcp1 -c "sudo /etc/dhcp/ldap-dhcp-sync.sh"
```

#### Vérifier la configuration générée

```bash
vagrant ssh dhcp1 -c "cat /etc/dhcp/dhcpd.conf"
```

Exemple de sortie :
```
# Configuration générée par ldap-dhcp-sync.sh
# Date: 2024-01-15 10:30:00

authoritative;
default-lease-time 3600;
max-lease-time 7200;

option domain-name "heracles.local";
option domain-name-servers 192.168.56.20;

subnet 192.168.56.0 netmask 255.255.255.0 {
    option routers 192.168.56.1;
    option broadcast-address 192.168.56.255;
    
    pool {
        range 192.168.56.100 192.168.56.199;
    }
    
    host server1 {
        hardware ethernet 08:00:27:XX:XX:XX;
        fixed-address 192.168.56.10;
    }
    
    host workstation1 {
        hardware ethernet 08:00:27:YY:YY:YY;
        fixed-address 192.168.56.11;
    }
}
```

#### Tests DHCP

```bash
# Vérifier le service
vagrant ssh dhcp1 -c "sudo systemctl status isc-dhcp-server"

# Voir les baux actifs
vagrant ssh dhcp1 -c "cat /var/lib/dhcp/dhcpd.leases"

# Tester une demande DHCP depuis un client
vagrant ssh server1 -c "sudo dhclient -v eth1"

# Logs DHCP
vagrant ssh dhcp1 -c "sudo journalctl -u isc-dhcp-server -f"
```

---

## Intégration DNS-DHCP

### Dynamic DNS (DDNS)

Pour mettre à jour automatiquement DNS lors des attributions DHCP :

#### Configuration DHCP

```bash
# Ajouter au service DHCP
curl -X PUT "http://localhost:8000/api/v1/dhcp/demo-dhcp" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dhcpStatements": [
      "authoritative",
      "ddns-update-style interim",
      "ddns-updates on",
      "ddns-domainname \"heracles.local.\"",
      "ddns-rev-domainname \"in-addr.arpa.\""
    ]
  }'
```

#### Clé TSIG partagée

```bash
# Créer une clé TSIG
curl -X POST "http://localhost:8000/api/v1/dhcp/demo-dhcp/tsig-keys" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cn": "ddns-key",
    "algorithm": "hmac-sha256",
    "secret": "base64-encoded-secret-here"
  }'
```

### Workflow typique

1. **Nouveau serveur** :
   ```bash
   # 1. Créer la réservation DHCP
   curl -X POST ".../dhcp/demo-dhcp/hosts" -d '{"cn": "newserver", ...}'
   
   # 2. Créer l'enregistrement DNS
   curl -X POST ".../dns/zones/heracles.local/records" -d '{"name": "newserver", "type": "A", ...}'
   
   # 3. Créer l'enregistrement PTR
   curl -X POST ".../dns/zones/56.168.192.in-addr.arpa/records" -d '{"name": "50", "type": "PTR", ...}'
   
   # 4. Synchroniser DHCP
   vagrant ssh dhcp1 -c "sudo /etc/dhcp/ldap-dhcp-sync.sh"
   ```

2. **Retrait d'un serveur** :
   ```bash
   # Supprimer dans l'ordre inverse
   curl -X DELETE ".../dhcp/demo-dhcp/hosts/newserver"
   curl -X DELETE ".../dns/zones/heracles.local/records/newserver?type=A"
   curl -X DELETE ".../dns/zones/56.168.192.in-addr.arpa/records/50?type=PTR"
   ```

### Bonnes pratiques

1. **Nommage cohérent** : Utiliser le même `cn` pour DHCP et DNS
2. **TTL approprié** : TTL court pour les enregistrements dynamiques
3. **Monitoring** : Surveiller les logs BIND et DHCP
4. **Sauvegarde** : Exporter régulièrement les données LDAP

```bash
# Export LDAP des zones DNS
ldapsearch -x -H ldap://localhost:389 -b "ou=dns,dc=heracles,dc=local" \
  -D "cn=admin,dc=heracles,dc=local" -w admin_secret > dns-backup.ldif

# Export LDAP de la config DHCP
ldapsearch -x -H ldap://localhost:389 -b "ou=dhcp,dc=heracles,dc=local" \
  -D "cn=admin,dc=heracles,dc=local" -w admin_secret > dhcp-backup.ldif
```
