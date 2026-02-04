# heracles-core

> Rust library for LDAP operations and cryptography (PyO3 bindings for Python)

## Version: 0.1.0

## Structure

```
src/
├── lib.rs         # Module exports + PyO3 module
├── ldap/          # LDAP connection pool, operations
├── crypto/        # Password hashing (Argon2id, bcrypt, SSHA, SHA, MD5)
├── errors.rs      # HeraclesError enum (thiserror)
└── python/        # PyO3 bindings
```

## Commands

```bash
cargo build --release        # Build
cargo test                   # Test (can run on host)
cargo fmt --all              # Format
cargo clippy -- -D warnings  # Lint (no warnings)
cargo doc --open             # Generate docs
```

## Key Exports (PyO3)

```python
import heracles_core

heracles_core.__version__              # "0.1.0"
heracles_core.hash_password(pwd, method)
heracles_core.verify_password(pwd, hash)
heracles_core.escape_filter_chars(input)
heracles_core.escape_dn_chars(input)
```

## Rules

- No `unwrap()` in production → use `?` or explicit handling
- Document public types with `///`
- Use `thiserror` for errors
- All crypto uses secure random salts
- Argon2id is the recommended hash method
