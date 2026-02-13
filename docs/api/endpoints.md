# API Endpoints

Complete reference for all Heracles REST API endpoints.

All endpoints require authentication unless noted otherwise. Include the access token:

```http
Authorization: Bearer <access_token>
```

---

## Users

### List Users

```http
GET /api/v1/users?limit=50&offset=0&filter=cn:contains:john
```

**Response `200`:**

```json
{
  "data": [
    {
      "dn": "uid=jdoe,ou=people,dc=example,dc=com",
      "uid": "jdoe",
      "cn": "John Doe",
      "sn": "Doe",
      "givenName": "John",
      "mail": "jdoe@example.com",
      "objectClass": ["inetOrgPerson", "posixAccount"]
    }
  ],
  "pagination": { "total": 150, "limit": 50, "offset": 0, "has_more": true }
}
```

### Get User

```http
GET /api/v1/users/{uid}
```

Returns the full user object including plugin tab status.

### Create User

```http
POST /api/v1/users
Content-Type: application/json

{
  "uid": "jdoe",
  "cn": "John Doe",
  "sn": "Doe",
  "givenName": "John",
  "mail": "jdoe@example.com",
  "userPassword": "SecureP@ss123",
  "posix": {
    "uidNumber": null,
    "gidNumber": 10000,
    "homeDirectory": "/home/jdoe",
    "loginShell": "/bin/bash"
  }
}
```

!!! note
    `uidNumber: null` triggers automatic allocation. `userPassword` is hashed server-side.

**Response `201`:** Created user object.

### Update User

```http
PUT /api/v1/users/{uid}
Content-Type: application/json

{
  "cn": "John M. Doe",
  "mail": "john.doe@example.com"
}
```

**Response `200`:** Updated user object.

### Delete User

```http
DELETE /api/v1/users/{uid}
```

**Response `204`:** No content.

---

## Groups

### List Groups

```http
GET /api/v1/groups?limit=50&offset=0
```

### Get Group

```http
GET /api/v1/groups/{cn}
```

### Create Group

```http
POST /api/v1/groups
Content-Type: application/json

{
  "cn": "developers",
  "description": "Development team",
  "groupType": "mixed",
  "gidNumber": 20001
}
```

### Update Group

```http
PUT /api/v1/groups/{cn}
```

### Delete Group

```http
DELETE /api/v1/groups/{cn}
```

### Add Member

```http
POST /api/v1/groups/{cn}/members
Content-Type: application/json

{
  "member": "uid=jdoe,ou=people,dc=example,dc=com"
}
```

### Remove Member

```http
DELETE /api/v1/groups/{cn}/members/{member_dn}
```

---

## Departments

### List Departments

```http
GET /api/v1/departments
```

### Create Department

```http
POST /api/v1/departments
Content-Type: application/json

{
  "ou": "Engineering",
  "description": "Engineering department"
}
```

### Delete Department

```http
DELETE /api/v1/departments/{ou}
```

---

## DNS

### List Zones

```http
GET /api/v1/dns/zones
```

### Create Zone

```http
POST /api/v1/dns/zones
Content-Type: application/json

{
  "zoneName": "example.com",
  "zoneType": "forward",
  "primaryNs": "ns1.example.com",
  "adminEmail": "admin@example.com"
}
```

### List Records

```http
GET /api/v1/dns/zones/{zoneName}/records
```

### Create Record

```http
POST /api/v1/dns/zones/{zoneName}/records
Content-Type: application/json

{
  "name": "www",
  "type": "A",
  "value": "192.168.1.10",
  "ttl": 3600
}
```

### Delete Record

```http
DELETE /api/v1/dns/zones/{zoneName}/records/{name}/{type}
```

---

## DHCP

### List Services

```http
GET /api/v1/dhcp/services
```

### Create Service

```http
POST /api/v1/dhcp/services
```

### Get Service Details

```http
GET /api/v1/dhcp/services/{serviceName}
```

---

## Systems

### List Systems

```http
GET /api/v1/systems?type=server
```

### Create System

```http
POST /api/v1/systems
Content-Type: application/json

{
  "cn": "server1",
  "type": "server",
  "ipAddress": "192.168.1.10",
  "macAddress": "00:11:22:33:44:55",
  "description": "Web server"
}
```

### Delete System

```http
DELETE /api/v1/systems/{cn}
```

---

## Sudo

### List Sudo Roles

```http
GET /api/v1/sudo
```

### Create Sudo Role

```http
POST /api/v1/sudo
Content-Type: application/json

{
  "cn": "web-admins",
  "sudoUser": ["jdoe", "%webadmins"],
  "sudoHost": ["ALL"],
  "sudoCommand": ["/usr/bin/systemctl restart nginx"],
  "sudoOption": ["!authenticate"]
}
```

### Delete Sudo Role

```http
DELETE /api/v1/sudo/{cn}
```

---

## ACL

### List Policies

```http
GET /api/v1/acl/policies
```

### Get User Permissions

```http
GET /api/v1/acl/permissions/{uid}
```

---

## Audit

### Query Audit Logs

```http
GET /api/v1/audit?limit=100&offset=0&filter=actor:eq:admin
```

---

## Health

### Health Check (No Auth Required)

```http
GET /api/v1/health
```

**Response `200`:**

```json
{
  "status": "healthy",
  "version": "0.8.1-rc",
  "services": {
    "ldap": "connected",
    "postgresql": "connected",
    "redis": "connected"
  }
}
```
