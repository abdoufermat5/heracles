# Changelog - heracles-core

All notable changes to the Heracles Core library will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Expose `__version__` constant to Python via PyO3 bindings

## [0.1.0] - 2026-01-15

### Added
- Initial release
- LDAP connection pooling with `deadpool` for high-performance connection management
- LDAP operations: search, add, modify, delete, bind, compare
- Password hashing algorithms:
  - Argon2id (recommended)
  - bcrypt
  - SSHA (SHA-1 salted)
  - SHA-256, SHA-512
  - MD5 (legacy compatibility only)
- Password verification with automatic algorithm detection
- DN utilities: parsing, building, escaping
- PyO3 bindings for Python integration:
  - `hash_password()` - Hash passwords with specified algorithm
  - `verify_password()` - Verify passwords against stored hashes
  - `detect_hash_method()` - Detect algorithm from hash string
  - `escape_dn_value()` - Escape special DN characters
  - `escape_filter_value()` - Escape LDAP filter special characters
  - `parse_dn()` - Parse DN string to components
  - `build_dn()` - Build DN from components
  - `PyLdapConnection` - Async LDAP connection class
  - `PyLdapEntry` - LDAP entry wrapper
  - `PyHashMethod` - Password hash method enum
- Comprehensive test suite (57 tests)

### Security
- All password hashing uses cryptographically secure random salts
- Argon2id configured with OWASP recommended parameters
- No plaintext password storage

[Unreleased]: https://github.com/abdoufermat5/heracles/compare/heracles-core/v0.1.0...HEAD
[0.1.0]: https://github.com/abdoufermat5/heracles/releases/tag/heracles-core/v0.1.0
