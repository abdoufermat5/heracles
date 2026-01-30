# Plugin Systems - Documentation

## Vue d'ensemble

Le plugin Systems gère l'inventaire des équipements IT : serveurs, postes de travail, imprimantes, téléphones, etc. Il sert de base pour les plugins DNS et DHCP.

## Architecture

```
┌─────────────────┐      REST API       ┌─────────────────┐
│   Heracles UI   │ ──────────────────▶ │  Systems Plugin │
│  (Page Systems) │                     │   (FastAPI)     │
└─────────────────┘                     └────────┬────────┘
                                                 │ LDAP
                                                 ▼
                                        ┌─────────────────┐
        Plugins dépendants              │    OpenLDAP     │
        ├── DNS (enregistrements)       │   (hrcSystem)   │
        ├── DHCP (réservations)         └─────────────────┘
        └── POSIX (hostObject)
```

## Types de systèmes

| Type | ObjectClass | Usage |
|------|-------------|-------|
| `server` | hrcServer | Serveurs physiques/virtuels |
| `workstation` | hrcWorkstation | Postes de travail |
| `terminal` | hrcTerminal | Clients légers |
| `printer` | hrcPrinter | Imprimantes |
| `component` | device | Composants réseau (switch, AP) |
| `phone` | hrcPhone | Téléphones fixes |
| `mobile` | hrcMobile | Téléphones mobiles |

## Schémas LDAP customs

Le plugin utilise des objectClasses personnalisés définis dans `heracles-systems.schema` :

```ldif
objectClass ( 1.3.6.1.4.1.XXXXX.1.1
    NAME 'hrcServer'
    DESC 'Server system'
    SUP top STRUCTURAL
    MUST cn
    MAY ( description $ ipHostNumber $ macAddress $ hrcLockMode ) )
```

## Schémas de données

### SystemCreate
Création d'un système.

```python
{
    "cn": "web-server-01",
    "systemType": "server",
    "description": "Serveur web principal",
    "ipAddresses": ["192.168.1.10", "10.0.0.10"],
    "macAddresses": ["00:11:22:33:44:55"],
    "lockMode": "unlocked"
}
```

### SystemRead
Lecture d'un système.

```python
{
    "dn": "cn=web-server-01,ou=servers,ou=systems,dc=example,dc=com",
    "cn": "web-server-01",
    "systemType": "server",
    "description": "Serveur web principal",
    "ipAddresses": ["192.168.1.10"],
    "macAddresses": ["00:11:22:33:44:55"],
    "lockMode": "unlocked",
    "objectClass": "hrcServer"
}
```

### Champs spécifiques par type

**Printer :**
```python
{
    "labeledURI": "ipp://printer.example.com/printers/main",
    "printerLocation": "Building A, Floor 2",
    "windowsDriverName": "HP LaserJet Pro MFP"
}
```

**Mobile :**
```python
{
    "imei": "123456789012345",
    "operatingSystem": "iOS 17",
    "puk": "12345678"
}
```

**Component :**
```python
{
    "serialNumber": "SN-12345",
    "owner": "uid=jdoe,ou=people,dc=example,dc=com"
}
```

## Endpoints API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/systems` | Lister tous les systèmes |
| GET | `/systems?type=server` | Filtrer par type |
| GET | `/systems/{cn}` | Lire un système |
| POST | `/systems` | Créer un système |
| PUT | `/systems/{cn}` | Modifier un système |
| DELETE | `/systems/{cn}` | Supprimer un système |

## Validation

### Adresses IP
- IPv4 : `192.168.1.10`
- IPv6 : `2001:db8::1`
- Validation par le module `ipaddress`

### Adresses MAC
- Format accepté : `00:11:22:33:44:55`, `00-11-22-33-44-55`, `001122334455`
- Normalisé en : `00:11:22:33:44:55`

### IMEI (mobiles)
- 15 chiffres
- Validation de la checksum (algorithme de Luhn)

## Intégration avec POSIX (hostObject)

Les systèmes peuvent être référencés dans le `host` attribute des comptes POSIX :

```python
# User avec accès restreint
{
    "uid": "jdoe",
    "trustMode": "byhost",
    "host": ["web-server-01", "db-server-01"]
}
```

Le Host Selector dans l'UI permet de sélectionner les systèmes enregistrés.

## Structure LDAP

```
ou=systems,dc=example,dc=com
├── ou=servers
│   ├── cn=web-server-01
│   │   ├── objectClass: hrcServer
│   │   ├── ipHostNumber: 192.168.1.10
│   │   └── macAddress: 00:11:22:33:44:55
│   └── cn=db-server-01
│       └── ...
├── ou=workstations
│   └── cn=dev-ws-01
├── ou=printers
│   └── cn=printer-floor2
├── ou=phones
├── ou=mobiles
├── ou=terminals
└── ou=components
```

## Workflow typique

1. **Ajouter un nouveau serveur**
   ```bash
   POST /systems {
     "cn": "app-server-02",
     "systemType": "server",
     "ipAddresses": ["192.168.1.20"],
     "macAddresses": ["AA:BB:CC:DD:EE:FF"],
     "description": "Serveur applicatif secondaire"
   }
   ```

2. **Créer une réservation DHCP** (plugin DHCP)
   ```bash
   POST /dhcp/demo-dhcp/hosts {
     "cn": "app-server-02",
     "dhcpHWAddress": "ethernet AA:BB:CC:DD:EE:FF",
     "fixedAddress": "192.168.1.20"
   }
   ```

3. **Créer un enregistrement DNS** (plugin DNS)
   ```bash
   POST /dns/zones/example.com/records {
     "name": "app-server-02",
     "type": "A",
     "content": "192.168.1.20"
   }
   ```
