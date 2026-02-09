# Heracles

> Next-generation LDAP Identity Management Platform

[![License](https://img.shields.io/badge/license-GPL--2.0-blue.svg)](LICENSE)
[![Rust](https://img.shields.io/badge/rust-1.75+-orange.svg)](https://www.rust-lang.org/)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-18+-61DAFB.svg)](https://reactjs.org/)

---

## Overview

**Heracles** is a modern LDAP identity management platform, designed to provide a powerful, scalable, and maintainable solution while maintaining **100% compatibility** with standard LDAP deployments and existing directory structures.

### Key Features

- **High Performance**: Rust-powered LDAP operations and password hashing
- **API-First**: RESTful API with OpenAPI documentation
- **Modern UI**: React-based responsive interface
- **Enterprise Security**: JWT authentication, fine-grained ACL
- **Plugin Architecture**: Modular and extensible
- **LDAP Compatible**: Standard LDAP schemas, coexistence possible

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         heracles-ui                              │
│                      (React + TypeScript)                        │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        heracles-api                              │
│                    (Python + FastAPI)                            │
└─────────────────────────────────────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
       ┌───────────┐    ┌───────────┐    ┌───────────┐
       │   LDAP    │    │ PostgreSQL│    │   Redis   │
       │(identity) │    │  (config) │    │  (cache)  │
       └───────────┘    └───────────┘    └───────────┘
              ▲
              │
┌─────────────────────────────────────────────────────────────────┐
│                       heracles-core                              │
│                         (Rust)                                   │
│           LDAP Operations • Password Hashing • Schema            │
└─────────────────────────────────────────────────────────────────┘
```
---

## Demo Environment

Un environnement de démonstration complet est disponible avec Vagrant/[VirtualBox|libvirt] pour tester les plugins SSH, Sudo, POSIX et DNS sur des VMs Linux.

```bash
# Depuis la racine du projet
make demo

# Test SSH avec authentification LDAP
ssh -i demo/keys/testuser testuser@192.168.56.10 'sudo whoami'

# Test DNS (depuis ns1 VM)
dig @192.168.56.20 server1.heracles.local
```

Préparer la PKI pour les VMs (après `scripts/dev-pki/generate.sh`) :

```bash
mkdir -p demo/config/ca demo/config/certs
cp pki/dev/ca/heracles-dev-ca.crt demo/config/ca/
cp pki/dev/server/heracles.local.crt demo/config/certs/
cp pki/dev/server/heracles.local.key demo/config/certs/
```

Voir [demo/README.md](demo/README.md) pour la documentation complète.

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Rust 1.75+ (for development)
- Python 3.11+ (for development)
- Node.js 20+ (for UI development)

### Start Development Infrastructure

```bash
# Clone the repository
git clone https://github.com/abdoufermat5/heracles.git
cd heracles

# Generate dev TLS certificates
./scripts/dev-pki/generate.sh

# Start LDAP, PostgreSQL, Redis
make up-infra

# Access phpLDAPadmin: http://localhost:8080
# Login: cn=admin,dc=heracles,dc=local / admin_secret
```

### Dev TLS + Hosts

Add host entries:

```bash
sudo sh -c 'cat >> /etc/hosts << EOF
127.0.0.1 heracles.local
127.0.0.1 ui.heracles.local
127.0.0.1 api.heracles.local
127.0.0.1 ldap.heracles.local
EOF'
```

Trust the dev CA:

```bash
sudo cp pki/dev/ca/heracles-dev-ca.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

Start the full stack (TLS proxy on :443):

```bash
make up
```

Open:
- UI: https://ui.heracles.local
- API: https://api.heracles.local/api/v1/health

### Build heracles-core

```bash
cd heracles-core
cargo build --release
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Core** | Rust 1.75+ |
| **API** | Python 3.11+, FastAPI |
| **Frontend** | React 18+, TypeScript 5+ |
| **Database** | PostgreSQL 15+ |
| **Cache** | Redis 7+ |
| **Directory** | OpenLDAP / 389DS |

---

## Quick Start

> **Note**: Heracles is currently in early development. This section will be updated when the first version is released.

### Prerequisites

- Docker & Docker Compose
- Rust 1.75+
- Python 3.11+
- Node.js 20+

---

## Contributing

Please read our documentation before contributing:

1. [Project Charter](guidelines/00-PROJECT-CHARTER.md) - Understand the vision
2. [Coding Rules](guidelines/04-CODING-RULES.md) - Follow the standards
3. [AI Agent Directives](guidelines/08-AI-AGENT-DIRECTIVES.md) - For AI-assisted development

---

## License

This project is licensed under the GNU General Public License v2.0 - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [OpenLDAP](https://www.openldap.org/) - The LDAP implementation
- The open-source LDAP management community
