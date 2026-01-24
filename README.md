# 🏛️ Heracles

> Next-generation LDAP Identity Management Platform

[![License](https://img.shields.io/badge/license-GPL--2.0-blue.svg)](LICENSE)
[![Rust](https://img.shields.io/badge/rust-1.75+-orange.svg)](https://www.rust-lang.org/)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-18+-61DAFB.svg)](https://reactjs.org/)

---

## 📋 Overview

**Heracles** is a modern LDAP identity management platform, designed to provide a powerful, scalable, and maintainable solution while maintaining **100% compatibility** with standard LDAP deployments and existing directory structures.

### Key Features

- 🚀 **High Performance**: Rust-powered LDAP operations and password hashing
- 🔌 **API-First**: RESTful API with OpenAPI documentation
- 🎨 **Modern UI**: React-based responsive interface
- 🔐 **Enterprise Security**: JWT authentication, fine-grained ACL
- 📦 **Plugin Architecture**: Modular and extensible
- ✅ **LDAP Compatible**: Standard LDAP schemas, coexistence possible

---

## 🏗️ Architecture

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

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Project Charter](docs/00-PROJECT-CHARTER.md) | Vision, principles, constraints |
| [Architecture](docs/01-ARCHITECTURE.md) | Technical architecture details |
| [API Specification](docs/02-API-SPECIFICATION.md) | REST API contract |
| [Data Model](docs/03-DATA-MODEL.md) | LDAP schemas and database |
| [Coding Rules](docs/04-CODING-RULES.md) | Development standards |
| [Plugin Specification](docs/05-PLUGIN-SPECIFICATION.md) | How to create plugins |
| [Security](docs/06-SECURITY.md) | Security requirements |
| [Roadmap](docs/07-ROADMAP.md) | Development timeline |
| [AI Agent Directives](docs/08-AI-AGENT-DIRECTIVES.md) | Guidelines for AI development |

---

## 🔌 Plugins (v1.0 Scope)

| Plugin | Description | Status |
|--------|-------------|--------|
| `core` | Base user/group management | 🔲 Planned |
| `posix` | Unix accounts (posixAccount, shadowAccount) | 🔲 Planned |
| `sudo` | Sudo rules management | 🔲 Planned |
| `ssh` | SSH public keys | 🔲 Planned |
| `systems` | Servers, workstations | 🔲 Planned |
| `dns` | DNS zones and records | 🔲 Planned |
| `dhcp` | DHCP configuration | 🔲 Planned |

---

## � Quick Start

### Prerequisites

- Docker & Docker Compose
- Rust 1.75+ (for development)
- Python 3.11+ (for development)
- Node.js 20+ (for UI development)

### Start Development Infrastructure

```bash
# Clone the repository
git clone https://github.com/your-org/heracles.git
cd heracles

# Start LDAP, PostgreSQL, Redis
make dev-infra

# Access phpLDAPadmin: http://localhost:8080
# Login: cn=admin,dc=heracles,dc=local / admin_secret
```

### Run Tests

```bash
# Run all Rust tests (57 tests)
make test-rust

# Run with cargo directly
cd heracles-core && cargo test --no-default-features
```

### Build heracles-core

```bash
cd heracles-core
cargo build --release
```

---

## �🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Core** | Rust 1.75+ |
| **API** | Python 3.11+, FastAPI |
| **Frontend** | React 18+, TypeScript 5+ |
| **Database** | PostgreSQL 15+ |
| **Cache** | Redis 7+ |
| **Directory** | OpenLDAP / 389DS |

---

## 🚀 Quick Start

> ⚠️ **Note**: Heracles is currently in early development. This section will be updated when the first alpha is released.

### Prerequisites

- Docker & Docker Compose
- Rust 1.75+
- Python 3.11+
- Node.js 20+

### Development Setup

```bash
# Clone the repository
git clone https://github.com/your-org/heracles.git
cd heracles

# Start infrastructure (LDAP, PostgreSQL, Redis)
docker-compose up -d

# Build Rust core
cd heracles-core
cargo build --release

# Start API
cd ../heracles-api
poetry install
poetry run uvicorn app.main:app --reload

# Start UI
cd ../heracles-ui
npm install
npm run dev
```

---

## 🤝 Contributing

Please read our documentation before contributing:

1. [Project Charter](docs/00-PROJECT-CHARTER.md) - Understand the vision
2. [Coding Rules](docs/04-CODING-RULES.md) - Follow the standards
3. [AI Agent Directives](docs/08-AI-AGENT-DIRECTIVES.md) - For AI-assisted development

---

## 📄 License

This project is licensed under the GNU General Public License v2.0 - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [OpenLDAP](https://www.openldap.org/) - The LDAP implementation
- The open-source LDAP management community
