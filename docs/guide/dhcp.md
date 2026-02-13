# DHCP Management# DHCP Management

























































DHCP configuration stored in LDAP can be consumed by ISC DHCP Server using the `ldap-server` directive. See the [demo environment](../development/demo.md) for a working example.## ISC DHCP Integration---Assign static IP addresses to specific MAC addresses for servers and infrastructure devices.### Fixed Hosts| Lease time | Default lease duration | `86400` (24h) || Gateway | Default router | `192.168.1.1` || Range end | Last allocatable IP | `192.168.1.200` || Range start | First allocatable IP | `192.168.1.100` || Netmask | Subnet mask | `255.255.255.0` || Network | Subnet address | `192.168.1.0` ||---|---|---|| Field | Description | Example |Each subnet defines a network range and its DHCP parameters:### Subnets![Service Details](../assets/dhcp/service_details.png)Configure subnets, pools, and global options for a DHCP service.## Service Details---| DNS servers | DNS servers to distribute | `192.168.1.1, 192.168.1.2` || Domain name | Default domain for clients | `example.com` || Primary server | Server hostname | `dhcp1.example.com` || Service name | Identifier for this DHCP instance | `dhcp-main` ||---|---|---|| Field | Description | Example |![Create Service](../assets/dhcp/create_service.png)Click **Create Service** to register a new DHCP server.## Creating a DHCP Service---![DHCP Services](../assets/dhcp/services_list.png)View and manage DHCP server instances.## Service List---Configure DHCP services, subnets, and address pools stored in LDAP.
Manage ISC DHCP server configurations stored in LDAP.

---

## Service List

View all DHCP service instances.

![DHCP Services](../assets/dhcp/services_list.png)

---

## Creating a Service

Click **Create Service** to deploy a new DHCP service configuration.

![Create Service](../assets/dhcp/create_service.png)

| Field | Description | Example |
|---|---|---|
| Service name | Unique identifier | `dhcp-office` |
| Primary server | Server hostname | `dhcp1.example.com` |
| Domain name | Default domain | `example.com` |
| DNS servers | Name servers for clients | `192.168.1.1, 192.168.1.2` |

---

## Service Configuration

Configure subnets, pools, and options within a DHCP service.

![Service Details](../assets/dhcp/service_details.png)

### Subnets

| Field | Description | Example |
|---|---|---|
| Network | Subnet address | `192.168.1.0` |
| Netmask | Subnet mask | `255.255.255.0` |
| Router | Default gateway | `192.168.1.1` |
| Range start | First address in pool | `192.168.1.100` |
| Range end | Last address in pool | `192.168.1.200` |
| Lease time | Default lease duration | `86400` (24h) |

### Static Hosts

Assign fixed IP addresses to specific MAC addresses for servers and network equipment.

---

## LDAP Integration

DHCP configuration is stored under `ou=dhcp` in the LDAP tree. ISC DHCP servers configured with the `ldap-hdb` module read their configuration directly from LDAP, enabling centralized management without touching config files on each server.
