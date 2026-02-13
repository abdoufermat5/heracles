# API Reference# API Reference


















































































































[:octicons-arrow-right-24: Authentication details](authentication.md) · [:octicons-arrow-right-24: Full endpoint reference](endpoints.md)| Audit | `/audit` | Audit log queries || Settings | `/settings` | System configuration || ACL | `/acl` | Access control policies || Sudo | `/sudo` | Sudo rules || Systems | `/systems` | System inventory || DHCP | `/dhcp` | DHCP configuration || DNS | `/dns` | DNS zones and records || Departments | `/departments` | Organizational units || Groups | `/groups` | Group management || Users | `/users` | User CRUD operations || Authentication | `/auth/*` | Login, refresh, logout ||---|---|---|| Area | Base Path | Description |## Endpoints Overview---| `present` | Attribute exists | `mail:present` || `ends` | Suffix match | `mail:ends:@example.com` || `starts` | Prefix match | `mail:starts:admin` || `contains` | Substring match | `cn:contains:john` || `eq` | Exact match | `uid:eq:jdoe` ||---|---|---|| Operator | Description | Example |```GET /api/v1/users?filter=cn:contains:john&filter=mail:ends:@example.com```httpUse the simplified LDAP filter syntax:### Filtering```}  }    "has_more": true    "offset": 40,    "limit": 20,    "total": 150,  "pagination": {  "data": [...],{```jsonResponse includes pagination metadata:```GET /api/v1/users?limit=20&offset=40```httpAll list endpoints support pagination:### Pagination| `500` | Internal Server Error | Server-side failure || `422` | Unprocessable Entity | Business logic error || `409` | Conflict | Entry already exists || `404` | Not Found | Resource does not exist || `403` | Forbidden | ACL denied || `401` | Unauthorized | Missing or invalid token || `400` | Bad Request | Validation failure || `204` | No Content | Successful DELETE || `201` | Created | Successful POST || `200` | OK | Successful GET, PUT ||---|---|---|| Code | Meaning | When |### HTTP Status Codes```}  }    }      "search_base": "ou=people,dc=example,dc=com"      "uid": "jdoe",    "details": {    "message": "User with uid 'jdoe' not found",    "code": "USER_NOT_FOUND",  "error": {{```json### Error FormatAll responses are JSON with `Content-Type: application/json; charset=utf-8`.### Response FormatThe API is versioned via the URL path: `/api/v1/`, `/api/v2/`. A version is supported for at least 12 months after deprecation.### Versioning## Conventions---Interactive API documentation (Swagger UI) is available at `/docs`.| Production | `https://heracles.example.com/api/v1` || Development | `http://localhost:8000/api/v1` ||---|---|| Environment | URL |## Base URL---Heracles exposes a RESTful API for all directory operations.
Heracles exposes a RESTful API for all directory operations.

---

## Base URL

```
Production:  https://heracles.example.com/api/v1
Development: http://localhost:8000/api/v1
```

## Interactive Docs

When running Heracles, visit **`/docs`** for the auto-generated Swagger UI:

```
http://localhost:8000/docs
```

---

## Conventions

### Versioning

The API is versioned via the URL path: `/api/v1/`, `/api/v2/`. Breaking changes require a new major version. Each version is supported for at least 12 months after deprecation.

### Response Format

All responses are JSON with `Content-Type: application/json; charset=utf-8`.

### Error Format

```json
{
  "error": {
    "code": "USER_NOT_FOUND",
    "message": "User with uid 'jdoe' not found",
    "details": {
      "uid": "jdoe",
      "search_base": "ou=people,dc=example,dc=com"
    }
  }
}
```

### HTTP Status Codes

| Code | Meaning | When |
|---|---|---|
| `200` | OK | Successful GET or PUT |
| `201` | Created | Successful POST |
| `204` | No Content | Successful DELETE |
| `400` | Bad Request | Validation error |
| `401` | Unauthorized | Missing or invalid token |
| `403` | Forbidden | ACL denied |
| `404` | Not Found | Resource doesn't exist |
| `409` | Conflict | Entry already exists |
| `422` | Unprocessable Entity | Business logic error |
| `500` | Internal Server Error | Server-side failure |

### Pagination

```http
GET /api/v1/users?limit=20&offset=40
```

```json
{
  "data": [...],
  "pagination": {
    "total": 150,
    "limit": 20,
    "offset": 40,
    "has_more": true
  }
}
```

### Filtering

Use simplified LDAP filter syntax:

```http
GET /api/v1/users?filter=cn:contains:john&filter=mail:ends:@example.com
```

| Operator | Description |
|---|---|
| `eq` | Exact match |
| `contains` | Substring match |
| `starts` | Prefix match |
| `ends` | Suffix match |
| `present` | Attribute exists |

---

## Endpoint Overview

| Method | Endpoint | Description |
|---|---|---|
| **Auth** | | |
| `POST` | `/auth/login` | Authenticate and get tokens |
| `POST` | `/auth/refresh` | Refresh access token |
| `POST` | `/auth/logout` | Invalidate tokens |
| `GET` | `/auth/me` | Current user info |
| **Users** | | |
| `GET` | `/users` | List users |
| `POST` | `/users` | Create user |
| `GET` | `/users/{uid}` | Get user |
| `PUT` | `/users/{uid}` | Update user |
| `DELETE` | `/users/{uid}` | Delete user |
| `POST` | `/users/{uid}/password` | Change password |
| **Groups** | | |
| `GET` | `/groups` | List groups |
| `POST` | `/groups` | Create group |
| `GET` | `/groups/{cn}` | Get group |
| `PUT` | `/groups/{cn}` | Update group |
| `DELETE` | `/groups/{cn}` | Delete group |
| `POST` | `/groups/{cn}/members` | Add member |
| `DELETE` | `/groups/{cn}/members/{uid}` | Remove member |
| **Departments** | | |
| `GET` | `/departments` | List departments |
| `POST` | `/departments` | Create department |
| `DELETE` | `/departments/{ou}` | Delete department |
| **Templates** | | |
| `GET` | `/templates` | List templates |
| `POST` | `/templates` | Create template |

[:octicons-arrow-right-24: Authentication details](authentication.md) · [:octicons-arrow-right-24: Full endpoint reference](endpoints.md)
