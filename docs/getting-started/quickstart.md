# Quick Start

Get Heracles running in under a minute.

---

## Prerequisites

- Docker 24.0+
- Docker Compose 2.20+

## Steps

### 1. Clone and Generate TLS Certificates

```bash
git clone https://github.com/abdoufermat5/heracles.git
cd heracles
./scripts/dev-pki/generate.sh
```

### 2. Start Infrastructure

```bash
make up-infra
```

This starts OpenLDAP, PostgreSQL, and Redis.

### 3. Start the Full Stack

```bash
make up
```

### 4. Open the UI

Navigate to **http://localhost:3000** and log in with the admin credentials printed during setup.

!!! success "You're ready"
    The API is at `http://localhost:8000/api/v1` and Swagger docs at `http://localhost:8000/docs`.

---

## TLS Setup (Development)

For HTTPS access on `*.heracles.local`, add host entries and trust the dev CA:

=== "Host entries"

    ```bash
    sudo sh -c 'cat >> /etc/hosts << EOF
    127.0.0.1 heracles.local
    127.0.0.1 ui.heracles.local
    127.0.0.1 api.heracles.local
    127.0.0.1 ldap.heracles.local
    EOF'
    ```

=== "Trust dev CA"

    ```bash
    sudo cp pki/dev/ca/heracles-dev-ca.crt /usr/local/share/ca-certificates/
    sudo update-ca-certificates
    ```

After this, access:

- **UI**: `https://ui.heracles.local`
- **API**: `https://api.heracles.local/api/v1/health`

---

## What's Next?

- [Configuration reference](configuration.md) — Customize your environment
- [User management](../guide/users.md) — Start managing identities
- [Architecture overview](../architecture/index.md) — Understand how it works
