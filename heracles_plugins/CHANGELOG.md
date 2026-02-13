# Changelog - heracles_plugins

All notable changes to the Heracles plugins package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.8.1-rc] - 2026-02-13

### Changed
- **Package management**: Migrated from setuptools to **hatchling** build backend (uv-compatible)
- Updated dev dependency versions (pytest, pytest-asyncio, pytest-cov)
- Removed `heracles_plugins.egg-info/` directory

### Added
- `minimum_api_version` field in PluginInfo for API compatibility checking

## [0.8.0-beta] - 2026-02-04

### Added
- **Package version aligned with API** (was 0.1.0)
- All plugins now at v1.0.0 (feature complete)

### Plugins

#### posix v1.0.0
- POSIX account management (posixAccount, shadowAccount)
- UID/GID automatic allocation with atomic operations
- POSIX groups (posixGroup objectClass)
- Mixed groups (groupOfNames + posixGroupAux)
- System trust via hostObject
- Shadow account expiration management
- 65+ unit tests

#### sudo v1.0.0
- Sudoers rules management (sudoRole objectClass)
- Full CRUD operations for sudo rules
- User/group/host/command targeting
- RunAs user/group configuration
- Sudo options support
- 97 unit tests

#### ssh v1.0.0
- SSH public key management (ldapPublicKey objectClass)
- Multiple keys per user
- Key validation (RSA, ECDSA, Ed25519)
- Fingerprint generation
- Activation/deactivation support

#### systems v1.0.0
- System management (device objectClass)
- 7 system types: server, workstation, terminal, printer, component, phone, mobile
- Custom heracles-systems.schema
- Integration with POSIX hostObject for system trust
- 24 unit tests

#### dns v1.0.0
- DNS zone management (dNSZone objectClass)
- 8 record types: A, AAAA, MX, NS, CNAME, PTR, TXT, SRV
- Zone SOA and NS configuration
- Hierarchical record management

#### dhcp v1.0.0
- DHCP configuration management
- 11 object types: service, shared_network, subnet, pool, host, group, class, subclass, tsig_key, dns_zone, failover_peer
- Custom dhcp-heracles.schema
- Tree structure for configuration hierarchy
- 80 unit tests

#### mail v1.0.0
- Mail attributes for users (mailLocalAddress, mailRoutingAddress)
- Mail attributes for groups (mailForwardingAddress)
- Basic mail integration support

## [0.1.0-alpha] - 2026-01-15

### Added
- Initial plugin framework
- Plugin base classes and interfaces
- POSIX plugin (partial implementation)

[Unreleased]: https://github.com/abdoufermat5/heracles/compare/heracles-plugins/v0.8.1-rc...HEAD
[0.8.1-rc]: https://github.com/abdoufermat5/heracles/compare/heracles-plugins/v0.8.0-beta...heracles-plugins/v0.8.1-rc
[0.8.0-beta]: https://github.com/abdoufermat5/heracles/compare/heracles-plugins/v0.1.0-alpha...heracles-plugins/v0.8.0-beta
[0.1.0-alpha]: https://github.com/abdoufermat5/heracles/releases/tag/heracles-plugins/v0.1.0-alpha
