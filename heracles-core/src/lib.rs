//! # Heracles Core
//!
//! Core library for Heracles LDAP identity management system.
//!
//! This crate provides:
//! - LDAP connection pooling and operations
//! - Password hashing (Argon2, bcrypt, SSHA, SHA, MD5)
//! - Schema validation
//! - Python bindings via PyO3
//!
//! ## Example
//!
//! ```rust,no_run
//! use heracles_core::ldap::{LdapConfig, create_pool, LdapPoolExt};
//! use heracles_core::crypto::{hash_password, HashMethod};
//!
//! #[tokio::main]
//! async fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     // Create LDAP connection pool
//!     let config = LdapConfig::from_env()?;
//!     let pool = create_pool(config)?;
//!     
//!     // Get a connection
//!     let conn = pool.get_connection().await?;
//!     
//!     // Hash a password
//!     let hash = hash_password("secret123", HashMethod::Argon2id)?;
//!     println!("Hash: {}", hash.hash);
//!     
//!     Ok(())
//! }
//! ```

pub mod acl;
pub mod crypto;
pub mod errors;
pub mod ldap;

#[cfg(feature = "python")]
mod python;

pub use errors::{HeraclesError, Result};

/// Crate version from Cargo.toml
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

#[cfg(feature = "python")]
use pyo3::prelude::*;

/// Initialize the Python module
#[cfg(feature = "python")]
#[pymodule]
fn heracles_core(py: Python<'_>, m: &PyModule) -> PyResult<()> {
    // Expose version as __version__
    m.add("__version__", VERSION)?;
    python::register_module(py, m)?;
    Ok(())
}
