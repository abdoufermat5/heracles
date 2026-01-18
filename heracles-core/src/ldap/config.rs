//! LDAP configuration management.

use crate::errors::{HeraclesError, Result};
use serde::{Deserialize, Serialize};
use std::env;
use std::time::Duration;

/// LDAP connection configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LdapConfig {
    /// LDAP server URI (e.g., "ldap://localhost:389" or "ldaps://ldap.example.com:636")
    pub uri: String,

    /// Base DN for searches (e.g., "dc=example,dc=com")
    pub base_dn: String,

    /// DN to bind as for admin operations
    pub bind_dn: String,

    /// Password for bind DN
    #[serde(skip_serializing)]
    pub bind_password: String,

    /// Whether to use STARTTLS (for ldap:// URIs)
    #[serde(default)]
    pub use_tls: bool,

    /// Connection pool size
    #[serde(default = "default_pool_size")]
    pub pool_size: usize,

    /// Connection timeout in seconds
    #[serde(default = "default_timeout")]
    pub timeout_seconds: u64,

    /// Search size limit (0 = no limit)
    #[serde(default)]
    pub size_limit: i32,

    /// Search time limit in seconds (0 = no limit)
    #[serde(default)]
    pub time_limit: i32,
}

fn default_pool_size() -> usize {
    10
}

fn default_timeout() -> u64 {
    30
}

impl LdapConfig {
    /// Creates a new LDAP configuration.
    pub fn new(
        uri: impl Into<String>,
        base_dn: impl Into<String>,
        bind_dn: impl Into<String>,
        bind_password: impl Into<String>,
    ) -> Self {
        Self {
            uri: uri.into(),
            base_dn: base_dn.into(),
            bind_dn: bind_dn.into(),
            bind_password: bind_password.into(),
            use_tls: false,
            pool_size: default_pool_size(),
            timeout_seconds: default_timeout(),
            size_limit: 0,
            time_limit: 0,
        }
    }

    /// Creates configuration from environment variables.
    ///
    /// Required environment variables:
    /// - `LDAP_URI`: LDAP server URI
    /// - `LDAP_BASE_DN`: Base DN
    /// - `LDAP_BIND_DN`: Bind DN
    /// - `LDAP_BIND_PASSWORD`: Bind password
    ///
    /// Optional:
    /// - `LDAP_USE_TLS`: "true" or "false" (default: false)
    /// - `LDAP_POOL_SIZE`: Pool size (default: 10)
    /// - `LDAP_TIMEOUT`: Timeout in seconds (default: 30)
    pub fn from_env() -> Result<Self> {
        let uri = env::var("LDAP_URI")
            .map_err(|_| HeraclesError::Configuration("LDAP_URI not set".into()))?;

        let base_dn = env::var("LDAP_BASE_DN")
            .map_err(|_| HeraclesError::Configuration("LDAP_BASE_DN not set".into()))?;

        let bind_dn = env::var("LDAP_BIND_DN")
            .map_err(|_| HeraclesError::Configuration("LDAP_BIND_DN not set".into()))?;

        let bind_password = env::var("LDAP_BIND_PASSWORD")
            .map_err(|_| HeraclesError::Configuration("LDAP_BIND_PASSWORD not set".into()))?;

        let use_tls = env::var("LDAP_USE_TLS")
            .map(|v| v.to_lowercase() == "true")
            .unwrap_or(false);

        let pool_size = env::var("LDAP_POOL_SIZE")
            .ok()
            .and_then(|v| v.parse().ok())
            .unwrap_or(default_pool_size());

        let timeout_seconds = env::var("LDAP_TIMEOUT")
            .ok()
            .and_then(|v| v.parse().ok())
            .unwrap_or(default_timeout());

        Ok(Self {
            uri,
            base_dn,
            bind_dn,
            bind_password,
            use_tls,
            pool_size,
            timeout_seconds,
            size_limit: 0,
            time_limit: 0,
        })
    }

    /// Returns the connection timeout as a Duration.
    pub fn timeout(&self) -> Duration {
        Duration::from_secs(self.timeout_seconds)
    }

    /// Validates the configuration.
    pub fn validate(&self) -> Result<()> {
        if self.uri.is_empty() {
            return Err(HeraclesError::Configuration("URI cannot be empty".into()));
        }

        if !self.uri.starts_with("ldap://") && !self.uri.starts_with("ldaps://") {
            return Err(HeraclesError::Configuration(
                "URI must start with ldap:// or ldaps://".into(),
            ));
        }

        if self.base_dn.is_empty() {
            return Err(HeraclesError::Configuration(
                "Base DN cannot be empty".into(),
            ));
        }

        if self.bind_dn.is_empty() {
            return Err(HeraclesError::Configuration(
                "Bind DN cannot be empty".into(),
            ));
        }

        if self.pool_size == 0 {
            return Err(HeraclesError::Configuration(
                "Pool size must be greater than 0".into(),
            ));
        }

        Ok(())
    }
}

impl Default for LdapConfig {
    fn default() -> Self {
        Self {
            uri: "ldap://localhost:389".into(),
            base_dn: "dc=example,dc=com".into(),
            bind_dn: "cn=admin,dc=example,dc=com".into(),
            bind_password: String::new(),
            use_tls: false,
            pool_size: default_pool_size(),
            timeout_seconds: default_timeout(),
            size_limit: 0,
            time_limit: 0,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_config_new() {
        let config = LdapConfig::new(
            "ldap://localhost:389",
            "dc=test,dc=com",
            "cn=admin,dc=test,dc=com",
            "secret",
        );

        assert_eq!(config.uri, "ldap://localhost:389");
        assert_eq!(config.base_dn, "dc=test,dc=com");
        assert_eq!(config.pool_size, 10);
    }

    #[test]
    fn test_config_validate_valid() {
        let config = LdapConfig::new(
            "ldap://localhost:389",
            "dc=test,dc=com",
            "cn=admin,dc=test,dc=com",
            "secret",
        );

        assert!(config.validate().is_ok());
    }

    #[test]
    fn test_config_validate_invalid_uri() {
        let mut config = LdapConfig::default();
        config.uri = "invalid://localhost".into();

        assert!(config.validate().is_err());
    }

    #[test]
    fn test_config_validate_empty_base_dn() {
        let mut config = LdapConfig::default();
        config.uri = "ldap://localhost:389".into();
        config.base_dn = String::new();

        assert!(config.validate().is_err());
    }
}
