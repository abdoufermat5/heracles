# Plugin DHCP - Documentation

## Vue d'ensemble

Le plugin DHCP gère la configuration DHCP via LDAP. La configuration est stockée dans l'annuaire et synchronisée vers ISC DHCP.

## Architecture

```
┌─────────────────┐      REST API       ┌─────────────────┐
│   Heracles UI   │ ──────────────────▶ │   DHCP Plugin   │
│  (Page DHCP)    │                     │   (FastAPI)     │
└─────────────────┘                     └────────┬────────┘
                                                 │ LDAP
                                                 ▼
┌─────────────────┐    Sync Script      ┌─────────────────┐
│    ISC DHCP     │ ◀─────────────────  │    OpenLDAP     │
│    (dhcpd)      │   ldap-dhcp-sync    │  (dhcpService)  │
└────────┬────────┘                     └─────────────────┘
         │
         │ DHCP Protocol
         ▼
┌─────────────────┐
│    Clients      │
│   (DHCPDISCOVER)│
└─────────────────┘
```

Contrairement au DNS (lecture directe), le DHCP nécessite un script de synchronisation qui génère `dhcpd.conf` depuis LDAP.

## Types d'objets DHCP

| Type | ObjectClass | Usage |
|------|-------------|-------|
| `service` | dhcpService | Configuration racine |
| `subnet` | dhcpSubnet | Réseau avec plage d'adresses |
| `pool` | dhcpPool | Sous-ensemble d'IPs |
| `host` | dhcpHost | Réservation MAC → IP |
| `shared_network` | dhcpSharedNetwork | Groupement de subnets |
| `group` | dhcpGroup | Config commune pour hosts |
| `class` | dhcpClass | Classification de clients |
| `subclass` | dhcpSubClass | Sous-classification |
| `tsig_key` | dhcpTSigKey | Clé pour DDNS |
| `dns_zone` | dhcpDnsZone | Zone pour DDNS |
| `failover_peer` | dhcpFailoverPeer | Configuration HA |

## Hiérarchie des objets

```
dhcpService (racine)
├── dhcpSubnet
│   ├── dhcpPool
│   └── dhcpHost
├── dhcpSharedNetwork
│   └── dhcpSubnet
│       ├── dhcpPool
│       └── dhcpHost
├── dhcpGroup
│   └── dhcpHost
├── dhcpClass
│   └── dhcpSubClass
├── dhcpTSigKey
├── dhcpDnsZone
└── dhcpFailoverPeer
```

## Schémas de données

### DhcpServiceCreate
Création d'un service DHCP.

```python
{
    "cn": "main-dhcp",
    "dhcpStatements": [
        "authoritative",
        "default-lease-time 3600",
        "max-lease-time 7200"
    ],
    "dhcpOptions": [
        "domain-name \"example.com\"",
        "domain-name-servers 192.168.1.10"
    ],
    "comments": "Service DHCP principal"
}
```

### DhcpSubnetCreate
Création d'un subnet.

```python
{
    "cn": "192.168.1.0",
    "dhcpNetMask": 24,
    "dhcpRange": ["192.168.1.100 192.168.1.200"],
    "dhcpStatements": ["default-lease-time 1800"],
    "dhcpOptions": [
        "routers 192.168.1.1",
        "subnet-mask 255.255.255.0"
    ]
}
```

### DhcpHostCreate
Création d'une réservation.

```python
{
    "cn": "web-server",
    "dhcpHWAddress": "ethernet AA:BB:CC:DD:EE:FF",
    "fixedAddress": "192.168.1.10",
    "dhcpOptions": ["host-name \"web-server\""],
    "comments": "Serveur web principal"
}
```

## Endpoints API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/dhcp` | Lister les services |
| POST | `/dhcp` | Créer un service |
| GET | `/dhcp/{cn}` | Lire un service |
| GET | `/dhcp/{cn}/tree` | Arborescence complète |
| GET | `/dhcp/{cn}/subnets` | Lister les subnets |
| POST | `/dhcp/{cn}/subnets` | Créer un subnet |
| GET | `/dhcp/{cn}/hosts` | Lister les hosts |
| POST | `/dhcp/{cn}/hosts` | Créer un host |
| POST | `/dhcp/{cn}/tsig-keys` | Créer une clé TSIG |

## Attributs LDAP

| Attribut | Multi | Description |
|----------|-------|-------------|
| `dhcpStatements` | Oui | Instructions DHCP |
| `dhcpOption` | Oui | Options DHCP |
| `dhcpRange` | Oui | Plages d'adresses |
| `dhcpNetMask` | Non | Masque de sous-réseau |
| `dhcpHWAddress` | Non | Adresse MAC |
| `fixedAddress` | Non | IP réservée |
| `dhcpComments` | Non | Description |

## Statements vs Options

| Type | Préfixe | Exemple |
|------|---------|---------|
| Statement | (aucun) | `authoritative`, `default-lease-time 3600` |
| Option | `option` | `domain-name "example.com"` |

Les statements contrôlent le comportement du serveur.
Les options sont transmises aux clients.

## Script de synchronisation

Le script `ldap-dhcp-sync.sh` :
1. Lit la configuration depuis LDAP
2. Génère `/etc/dhcp/dhcpd.conf.new`
3. Valide avec `dhcpd -t`
4. Remplace l'ancienne config si valide
5. Recharge ISC DHCP

```bash
#!/bin/bash
# Génération simplifiée
ldapsearch -x -b "cn=main-dhcp,ou=dhcp,dc=example,dc=com" | \
  /usr/local/bin/ldap2dhcpd > /etc/dhcp/dhcpd.conf.new

dhcpd -t -cf /etc/dhcp/dhcpd.conf.new && \
  mv /etc/dhcp/dhcpd.conf.new /etc/dhcp/dhcpd.conf && \
  systemctl reload isc-dhcp-server
```

## Structure LDAP

```
ou=dhcp,dc=example,dc=com
└── cn=main-dhcp                        # Service
    ├── objectClass: dhcpService
    ├── dhcpStatements: authoritative
    ├── dhcpOption: domain-name "example.com"
    │
    ├── cn=192.168.1.0                  # Subnet
    │   ├── objectClass: dhcpSubnet
    │   ├── dhcpNetMask: 24
    │   ├── dhcpRange: 192.168.1.100 192.168.1.200
    │   │
    │   ├── cn=dynamic-pool             # Pool
    │   │   ├── objectClass: dhcpPool
    │   │   └── dhcpRange: 192.168.1.100 192.168.1.150
    │   │
    │   └── cn=web-server               # Host
    │       ├── objectClass: dhcpHost
    │       ├── dhcpHWAddress: ethernet AA:BB:CC:DD:EE:FF
    │       └── fixedAddress: 192.168.1.10
    │
    └── cn=ddns-key                     # TSIG Key
        ├── objectClass: dhcpTSigKey
        ├── algorithm: hmac-sha256
        └── secret: base64...
```

## Fichier généré (dhcpd.conf)

```
# Généré depuis LDAP
authoritative;
default-lease-time 3600;
max-lease-time 7200;

option domain-name "example.com";
option domain-name-servers 192.168.1.10;

subnet 192.168.1.0 netmask 255.255.255.0 {
    option routers 192.168.1.1;
    
    pool {
        range 192.168.1.100 192.168.1.150;
    }
    
    host web-server {
        hardware ethernet AA:BB:CC:DD:EE:FF;
        fixed-address 192.168.1.10;
    }
}
```

## Workflow typique

1. **Créer un service DHCP**
   ```bash
   POST /dhcp {"cn": "main-dhcp", "dhcpStatements": ["authoritative"]}
   ```

2. **Ajouter un subnet**
   ```bash
   POST /dhcp/main-dhcp/subnets {
     "cn": "192.168.1.0",
     "dhcpNetMask": 24,
     "dhcpRange": ["192.168.1.100 192.168.1.200"]
   }
   ```

3. **Ajouter une réservation**
   ```bash
   POST /dhcp/main-dhcp/hosts {
     "cn": "new-server",
     "dhcpHWAddress": "ethernet 00:11:22:33:44:55",
     "fixedAddress": "192.168.1.50"
   }
   ```

4. **Synchroniser**
   ```bash
   ssh dhcp-server /etc/dhcp/ldap-dhcp-sync.sh
   ```

## Failover (HA)

Configuration haute disponibilité avec deux serveurs :

```python
{
    "cn": "dhcp-failover",
    "primaryServer": "192.168.1.5",
    "secondaryServer": "192.168.1.6",
    "primaryPort": 647,
    "secondaryPort": 647,
    "split": 128,
    "loadBalanceTime": 3
}
```
