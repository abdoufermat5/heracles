# Changelog - heracles-api

All notable changes to the Heracles API will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `/api/v1/version` endpoint exposing component versions
- `minimum_api_version` field in `PluginInfo` for compatibility checking

## [0.8.0-beta] - 2026-02-04

### Added
- **Phase 3 Complete**: All infrastructure plugins operational
- Plugin system with dynamic loading and configuration
- Department management with hierarchical filtering
- Plugin configuration service with database persistence
- Rate limiting middleware with Redis backend
- Plugin access middleware for enabling/disabling plugins

### Plugins (v1.0.0 each)
- **posix**: POSIX account management (UID/GID, shadowAccount, mixed groups)
- **sudo**: Sudoers rules management (sudoRole objectClass)
- **ssh**: SSH public key management (ldapPublicKey objectClass)
- **systems**: System management (7 types: server, workstation, terminal, printer, component, phone, mobile)
- **dns**: DNS zone and record management (8 record types)
- **dhcp**: DHCP configuration management (11 object types)
- **mail**: Mail attributes for users and groups

### Changed
- Version source consolidated to `__version__` in `__init__.py`
- All hardcoded versions replaced with imported constant

## [0.5.0-beta] - 2026-01-20

### Added
- **Phase 2 Complete**: Core identity management
- User CRUD operations (create, read, update, delete)
- Group CRUD operations with member management
- User lock/unlock functionality
- Password management (change, reset)
- POSIX plugin with Unix account attributes

## [0.1.0-alpha] - 2026-01-15

### Added
- **Phase 1 Complete**: Foundation
- FastAPI application skeleton
- JWT authentication with access/refresh tokens
- HttpOnly cookie-based token storage
- Redis session management
- PostgreSQL database with Alembic migrations
- LDAP service integration via heracles-core
- User and group repositories
- Pydantic schemas for validation
- CORS and security middleware
- Structured logging with structlog
- Configuration management with pydantic-settings

### Security
- JWT tokens with configurable expiration
- Password hashing via heracles-core (Argon2id default)
- LDAP injection prevention with proper escaping
- Rate limiting infrastructure

[Unreleased]: https://github.com/abdoufermat5/heracles/compare/heracles-api/v0.8.0-beta...HEAD
[0.8.0-beta]: https://github.com/abdoufermat5/heracles/compare/heracles-api/v0.5.0-beta...heracles-api/v0.8.0-beta
[0.5.0-beta]: https://github.com/abdoufermat5/heracles/compare/heracles-api/v0.1.0-alpha...heracles-api/v0.5.0-beta
[0.1.0-alpha]: https://github.com/abdoufermat5/heracles/releases/tag/heracles-api/v0.1.0-alpha
