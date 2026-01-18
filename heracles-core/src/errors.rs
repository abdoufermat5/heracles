//! Error types for Heracles Core.
//!
//! This module defines all error types used throughout the library.

use thiserror::Error;

/// Result type alias for Heracles operations.
pub type Result<T> = std::result::Result<T, HeraclesError>;

/// Main error type for Heracles Core operations.
#[derive(Error, Debug)]
pub enum HeraclesError {
    /// LDAP connection error
    #[error("LDAP connection failed: {0}")]
    LdapConnection(String),

    /// LDAP bind (authentication) error
    #[error("LDAP bind failed: {0}")]
    LdapBind(String),

    /// LDAP search error
    #[error("LDAP search failed: {0}")]
    LdapSearch(String),

    /// LDAP add operation error
    #[error("LDAP add failed: {0}")]
    LdapAdd(String),

    /// LDAP modify operation error
    #[error("LDAP modify failed: {0}")]
    LdapModify(String),

    /// LDAP delete operation error
    #[error("LDAP delete failed: {0}")]
    LdapDelete(String),

    /// LDAP entry not found
    #[error("LDAP entry not found: {0}")]
    LdapNotFound(String),

    /// LDAP entry already exists
    #[error("LDAP entry already exists: {0}")]
    LdapAlreadyExists(String),

    /// Invalid DN format
    #[error("Invalid DN format: {0}")]
    InvalidDN(String),

    /// Invalid LDAP filter
    #[error("Invalid LDAP filter: {0}")]
    InvalidFilter(String),

    /// Password hashing error
    #[error("Password hashing failed: {0}")]
    PasswordHash(String),

    /// Password verification error
    #[error("Password verification failed: {0}")]
    PasswordVerify(String),

    /// Unsupported hash method
    #[error("Unsupported hash method: {0}")]
    UnsupportedHashMethod(String),

    /// Schema validation error
    #[error("Schema validation failed: {0}")]
    SchemaValidation(String),

    /// Configuration error
    #[error("Configuration error: {0}")]
    Configuration(String),

    /// Pool error
    #[error("Connection pool error: {0}")]
    Pool(String),

    /// Timeout error
    #[error("Operation timed out: {0}")]
    Timeout(String),

    /// Internal error
    #[error("Internal error: {0}")]
    Internal(String),

    /// Schema error
    #[error("Schema error: {0}")]
    Schema(String),

    /// Configuration error (generic)
    #[error("Configuration error: {0}")]
    Config(String),
}

impl From<ldap3::LdapError> for HeraclesError {
    fn from(err: ldap3::LdapError) -> Self {
        HeraclesError::Internal(err.to_string())
    }
}

impl From<std::io::Error> for HeraclesError {
    fn from(err: std::io::Error) -> Self {
        HeraclesError::Internal(err.to_string())
    }
}

impl From<std::env::VarError> for HeraclesError {
    fn from(err: std::env::VarError) -> Self {
        HeraclesError::Config(err.to_string())
    }
}

#[cfg(feature = "python")]
impl From<HeraclesError> for pyo3::PyErr {
    fn from(err: HeraclesError) -> pyo3::PyErr {
        pyo3::exceptions::PyRuntimeError::new_err(err.to_string())
    }
}
