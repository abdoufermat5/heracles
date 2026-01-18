//! Cryptographic module for Heracles.
//!
//! This module provides password hashing and verification using various methods
//! compatible with LDAP password storage (FusionDirectory compatible).
//!
//! Supported hash methods:
//! - SSHA (Salted SHA-1) - FusionDirectory default
//! - Argon2id - Modern secure option
//! - bcrypt - Widely used secure option
//! - SHA-512 / SHA-256 - Standard hashes
//! - SSHA-512 / SSHA-256 - Salted SHA variants
//! - MD5 / SMD5 - Legacy support only (not recommended)

pub mod password;

pub use password::{
    hash_password, verify_password, HashMethod, PasswordHash, PasswordHasher, PasswordVerifier,
};
