# Authentication

Heracles uses JWT (JSON Web Tokens) for API authentication.

---

## Login

Authenticate with username and password to receive tokens.

```http
POST /auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "secret"
}
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "dn": "uid=admin,ou=people,dc=example,dc=com",
    "uid": "admin",
    "cn": "Administrator"
  }
}
```

---

## Using Tokens

Include the access token in the `Authorization` header:

```http
GET /api/v1/users
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

---

## Refresh Token

When the access token expires, use the refresh token to obtain a new one without re-entering credentials.

```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_in": 1800
}
```

---

## Logout

Invalidate the current tokens.

```http
POST /auth/logout
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

**Response:** `204 No Content`

---

## Current User

Get information about the authenticated user.

```http
GET /auth/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

**Response:**

```json
{
  "dn": "uid=admin,ou=people,dc=example,dc=com",
  "uid": "admin",
  "cn": "Administrator",
  "mail": "admin@example.com",
  "permissions": ["user:read", "user:write", "group:read"]
}
```

---

## Token Lifetimes

| Token | Duration | Renewal |
|---|---|---|
| Access token | 30 minutes | Via refresh token |
| Refresh token | 7 days | Requires re-login |

See [Security > Auth & Tokens](../security/auth-tokens.md) for implementation details.
