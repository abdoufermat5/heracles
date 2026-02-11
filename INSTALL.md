# Heracles Installation Guide

## Quick Start (30 seconds)

```bash
git clone https://github.com/abdoufermat5/heracles.git
cd heracles
make setup
```

The interactive wizard creates `.env`, generates secrets, bootstraps LDAP, and starts all services.

---

## Installation Methods

### 1. Interactive Wizard (Recommended)

```bash
make setup
```

Walks you through configuration with sensible defaults. Generates all passwords and secrets automatically.

### 2. One-Command Quick Start

```bash
make quick-start
```

Non-interactive. Uses defaults or existing `.env`. Good for CI/testing.

### 3. Pre-Built Docker Images

```bash
# Pull from GitHub Container Registry
docker pull ghcr.io/abdoufermat5/heracles-api:0.8.1-rc
docker pull ghcr.io/abdoufermat5/heracles-ui:0.8.1-rc

# Copy production compose and configure
cp docker-compose.prod.yml docker-compose.yml
cp .env.production.example .env
# Edit .env — set all [CHANGE] values
docker compose up -d
```

### 4. Ansible (Production Servers)

```bash
cd deploy/ansible
cp group_vars/all.yml.example group_vars/all.yml
# Edit inventory and variables
ansible-playbook -i inventory/production.yml playbooks/deploy.yml
```

See [deploy/ansible/](deploy/ansible/) for full documentation.

---

## Requirements

| Component | Minimum |
|-----------|---------|
| Docker | 24.0+ |
| Docker Compose | 2.20+ |
| OpenSSL | 1.1+ (for secret generation) |
| Disk | 2 GB free |
| RAM | 2 GB (4 GB recommended) |

For Ansible deployments: Ansible 2.14+, Python 3.11+ on controller.

---

## Configuration

All configuration is via environment variables in `.env`. Key settings:

| Variable | Description | Default |
|----------|-------------|---------|
| `LDAP_ORGANISATION` | Your organization name | MyOrganisation |
| `LDAP_DOMAIN` | Your domain | heracles.local |
| `LDAP_BASE_DN` | LDAP base DN | dc=heracles,dc=local |
| `LDAP_ADMIN_PASSWORD` | LDAP admin password | (generated) |
| `SECRET_KEY` | JWT signing key | (generated) |
| `POSTGRES_PASSWORD` | PostgreSQL password | (generated) |
| `REDIS_PASSWORD` | Redis password | (generated) |
| `HRC_ADMIN_USER` | Heracles admin username | hrc-admin |
| `HRC_ADMIN_PASSWORD` | Heracles admin password | (generated) |

See [.env.production.example](.env.production.example) for the complete reference.

---

## Post-Install

After installation:

1. **Login**: Open `http://localhost:3000` and login with your admin credentials
2. **Create departments**: Organize your directory structure
3. **Create templates**: Define user creation templates for different roles
4. **Import users**: Bulk import via CSV from the Import page
5. **Configure plugins**: Enable POSIX, Sudo, SSH, DNS, DHCP, Mail as needed

---

## Services

| Service | URL | Description |
|---------|-----|-------------|
| UI | http://localhost:3000 | Web interface |
| API | http://localhost:8000/api/v1 | REST API |
| API Docs | http://localhost:8000/docs | Swagger/OpenAPI |
| phpLDAPadmin | http://localhost:8080 | LDAP browser (dev only) |

---

## Useful Commands

```bash
make logs              # View all logs
make logs s=api        # View API logs only
make shell s=api       # Shell into API container
make down              # Stop all services
make clean             # Remove everything (including volumes)
make version           # Show component versions
make release-validate  # Validate release readiness
```

---

## Upgrading

```bash
# Pull latest images
docker compose pull

# Restart with new images
docker compose up -d

# Or with Ansible
ansible-playbook -i inventory/production.yml playbooks/upgrade.yml \
  -e heracles_version=1.1.0
```

---

## Backup & Restore

### Manual Backup

```bash
# PostgreSQL
docker compose exec postgres pg_dump -U heracles heracles > backup.sql

# LDAP
docker compose exec ldap slapcat > backup.ldif
```

### Ansible Backup

```bash
ansible-playbook -i inventory/production.yml playbooks/backup.yml
```

---

## Troubleshooting

**Services won't start?**
```bash
make logs              # Check for errors
docker compose ps      # Check container status
```

**LDAP bootstrap fails?**
```bash
make bootstrap         # Re-run LDAP initialization
make schemas           # Re-load schemas
```

**Database issues?**
```bash
make shell s=api
python -m alembic upgrade head   # Run migrations manually
```
