# Installation

Heracles offers several installation methods depending on your needs.

---

## 1. Interactive Wizard (Recommended)

The wizard walks you through configuration, generates secrets, bootstraps LDAP, and starts all services.

```bash
git clone https://github.com/abdoufermat5/heracles.git
cd heracles
make setup
```

The wizard:

- Creates `.env` with sensible defaults
- Generates all passwords and secrets automatically
- Bootstraps the LDAP directory
- Starts all containers

---

## 2. One-Command Quick Start

For CI/testing or non-interactive setups:

```bash
make quick-start
```

Uses defaults or an existing `.env` file — no prompts.

---

## 3. Pre-Built Docker Images

Pull images from GitHub Container Registry:

```bash
docker pull ghcr.io/abdoufermat5/heracles-api:0.8.1-rc
docker pull ghcr.io/abdoufermat5/heracles-ui:0.8.1-rc
```

Then configure and start:

```bash
cp docker-compose.prod.yml docker-compose.yml
cp .env.production.example .env
# Edit .env — set all [CHANGE] values
docker compose up -d
```

---

## 4. Ansible (Production)

For deploying to production servers:

```bash
cd deploy/ansible
cp group_vars/all.yml.example group_vars/all.yml
# Edit inventory and variables
ansible-playbook -i inventory/production.yml playbooks/deploy.yml
```

!!! info "Ansible Requirements"
    Ansible 2.14+ and Python 3.11+ on the controller machine.

See `deploy/ansible/` for full playbook documentation.

---

## Post-Install Steps

After installation:

1. **Login** — Open `http://localhost:3000` with your admin credentials (or `https://ui.heracles.local` with TLS)
2. **Create departments** — Organize your directory hierarchy
3. **Create templates** — Standardize user creation with templates
4. **Import users** — Bulk import via CSV from the Import page
5. **Enable plugins** — Activate POSIX, Sudo, SSH, DNS, DHCP, Mail as needed

---

## Services

After a successful install, these services are available:

| Service | URL | Description |
|---|---|---|
| UI | `http://localhost:3000` | Web interface |
| API | `http://localhost:8000/api/v1` | REST API |
| API Docs | `http://localhost:8000/docs` | Swagger / OpenAPI |
| phpLDAPadmin | `http://localhost:8080` | LDAP browser (dev only) |

---

## Useful Commands

```bash
make logs              # View all service logs
make logs s=api        # View API logs only
make shell s=api       # Shell into the API container
make down              # Stop all services
make clean             # Remove everything (including volumes)
make version           # Show component versions
```
