//! LDAP connection pool using deadpool.

use crate::errors::{HeraclesError, Result};
use crate::ldap::config::LdapConfig;
use crate::ldap::connection::LdapConnection;
use async_trait::async_trait;
use deadpool::managed::{Manager, Metrics, Object, Pool, RecycleError, RecycleResult};
use std::sync::Arc;
use tracing::{debug, error, instrument, warn};

/// Connection pool for LDAP connections.
pub type LdapPool = Pool<LdapConnectionManager>;

/// Pooled LDAP connection.
pub type PooledConnection = Object<LdapConnectionManager>;

/// Manager for LDAP connections in the pool.
pub struct LdapConnectionManager {
    config: Arc<LdapConfig>,
}

impl LdapConnectionManager {
    /// Creates a new connection manager.
    pub fn new(config: LdapConfig) -> Self {
        Self {
            config: Arc::new(config),
        }
    }
}

#[async_trait]
impl Manager for LdapConnectionManager {
    type Type = LdapConnection;
    type Error = HeraclesError;

    #[instrument(skip(self))]
    async fn create(&self) -> Result<LdapConnection> {
        debug!("Creating new LDAP connection");
        let mut conn = LdapConnection::new((*self.config).clone()).await?;
        conn.bind().await?;
        Ok(conn)
    }

    #[instrument(skip(self, conn))]
    async fn recycle(
        &self,
        conn: &mut LdapConnection,
        _metrics: &Metrics,
    ) -> RecycleResult<Self::Error> {
        // Check if connection is still valid by checking if it's bound
        if !conn.is_bound() {
            warn!("Connection lost its bind, recycling failed");
            return Err(RecycleError::StaticMessage("Connection not bound"));
        }

        // Connection seems valid
        debug!("Recycling LDAP connection");
        Ok(())
    }
}

/// Builder for creating an LDAP connection pool.
#[derive(Debug)]
pub struct LdapPoolBuilder {
    config: LdapConfig,
    max_size: usize,
    wait_timeout: Option<std::time::Duration>,
    create_timeout: Option<std::time::Duration>,
    recycle_timeout: Option<std::time::Duration>,
}

impl LdapPoolBuilder {
    /// Creates a new pool builder with the given configuration.
    pub fn new(config: LdapConfig) -> Self {
        let pool_size = config.pool_size;
        Self {
            config,
            max_size: pool_size,
            wait_timeout: Some(std::time::Duration::from_secs(30)),
            create_timeout: Some(std::time::Duration::from_secs(10)),
            recycle_timeout: Some(std::time::Duration::from_secs(5)),
        }
    }

    /// Sets the maximum pool size.
    pub fn max_size(mut self, size: usize) -> Self {
        self.max_size = size;
        self
    }

    /// Sets the timeout for waiting for a connection.
    pub fn wait_timeout(mut self, timeout: std::time::Duration) -> Self {
        self.wait_timeout = Some(timeout);
        self
    }

    /// Sets the timeout for creating a new connection.
    pub fn create_timeout(mut self, timeout: std::time::Duration) -> Self {
        self.create_timeout = Some(timeout);
        self
    }

    /// Sets the timeout for recycling a connection.
    pub fn recycle_timeout(mut self, timeout: std::time::Duration) -> Self {
        self.recycle_timeout = Some(timeout);
        self
    }

    /// Builds the connection pool.
    pub fn build(self) -> Result<LdapPool> {
        self.config.validate()?;

        let manager = LdapConnectionManager::new(self.config);

        let mut pool_builder = Pool::builder(manager).max_size(self.max_size);

        if let Some(timeout) = self.wait_timeout {
            pool_builder = pool_builder.wait_timeout(Some(timeout));
        }

        if let Some(timeout) = self.create_timeout {
            pool_builder = pool_builder.create_timeout(Some(timeout));
        }

        if let Some(timeout) = self.recycle_timeout {
            pool_builder = pool_builder.recycle_timeout(Some(timeout));
        }

        pool_builder
            .build()
            .map_err(|e| HeraclesError::Config(format!("Failed to build pool: {}", e)))
    }
}

/// Creates a new LDAP connection pool from configuration.
pub fn create_pool(config: LdapConfig) -> Result<LdapPool> {
    LdapPoolBuilder::new(config).build()
}

/// Creates a new LDAP connection pool from environment variables.
pub fn create_pool_from_env() -> Result<LdapPool> {
    let config = LdapConfig::from_env()?;
    create_pool(config)
}

/// Helper trait to get connections from the pool.
#[async_trait]
pub trait LdapPoolExt {
    /// Gets a connection from the pool.
    async fn get_connection(&self) -> Result<PooledConnection>;

    /// Gets pool status information.
    fn status(&self) -> PoolStatus;
}

#[async_trait]
impl LdapPoolExt for LdapPool {
    #[instrument(skip(self))]
    async fn get_connection(&self) -> Result<PooledConnection> {
        self.get().await.map_err(|e| {
            error!("Failed to get connection from pool: {}", e);
            HeraclesError::LdapConnection(format!("Pool error: {}", e))
        })
    }

    fn status(&self) -> PoolStatus {
        let status = self.status();
        PoolStatus {
            max_size: status.max_size,
            size: status.size,
            available: status.available,
            waiting: status.waiting,
        }
    }
}

/// Pool status information.
#[derive(Debug, Clone)]
pub struct PoolStatus {
    /// Maximum pool size.
    pub max_size: usize,
    /// Current number of connections.
    pub size: usize,
    /// Number of available connections.
    pub available: usize,
    /// Number of tasks waiting for a connection.
    pub waiting: usize,
}

impl std::fmt::Display for PoolStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "Pool[max={}, size={}, available={}, waiting={}]",
            self.max_size, self.size, self.available, self.waiting
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pool_builder_default() {
        let config = LdapConfig::default();
        let builder = LdapPoolBuilder::new(config);
        assert_eq!(builder.max_size, 10); // default pool_size
    }

    #[test]
    fn test_pool_builder_custom_size() {
        let config = LdapConfig {
            pool_size: 20,
            ..Default::default()
        };
        let builder = LdapPoolBuilder::new(config).max_size(15);
        assert_eq!(builder.max_size, 15);
    }

    #[test]
    fn test_pool_builder_validation_fails() {
        let config = LdapConfig {
            uri: "".to_string(), // Invalid
            ..Default::default()
        };
        let result = LdapPoolBuilder::new(config).build();
        assert!(result.is_err());
    }

    #[test]
    fn test_pool_status_display() {
        let status = PoolStatus {
            max_size: 10,
            size: 5,
            available: 3,
            waiting: 2,
        };
        let display = format!("{}", status);
        assert!(display.contains("max=10"));
        assert!(display.contains("size=5"));
        assert!(display.contains("available=3"));
        assert!(display.contains("waiting=2"));
    }
}
