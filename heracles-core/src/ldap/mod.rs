//! LDAP module for Heracles Core.
//!
//! This module provides LDAP connection pooling and operations:
//! - Connection management with deadpool-based pooling
//! - DN parsing, escaping, and manipulation
//! - Filter building with proper escaping
//! - CRUD operations on LDAP entries
//!
//! # Example
//!
//! ```rust,no_run
//! use heracles_core::ldap::{LdapConfig, create_pool, LdapPoolExt, FilterBuilder};
//!
//! # async fn example() -> heracles_core::errors::Result<()> {
//! let config = LdapConfig::from_env()?;
//! let pool = create_pool(config)?;
//!
//! let mut conn = pool.get_connection().await?;
//!
//! // Search for users
//! let filter = FilterBuilder::new()
//!     .object_class("inetOrgPerson")
//!     .eq("uid", "testuser")
//!     .build_and();
//!
//! let entries = conn.search(
//!     "ou=users",
//!     ldap3::Scope::Subtree,
//!     &filter.to_string(),
//!     vec!["cn", "mail", "uid"],
//! ).await?;
//! # Ok(())
//! # }
//! ```

pub mod config;
pub mod connection;
pub mod dn;
pub mod filter;
pub mod operations;
pub mod pool;

// Re-export main types
pub use config::LdapConfig;
pub use connection::LdapConnection;
pub use dn::{
    escape_dn_value, escape_filter_value, unescape_dn_value, DistinguishedName, DnBuilder,
    RdnComponent,
};
pub use filter::{patterns, FilterBuilder, LdapFilter};
pub use operations::{LdapEntry, LdapModification, SearchBuilder, SearchScope};
pub use pool::{
    create_pool, create_pool_from_env, LdapPool, LdapPoolBuilder, LdapPoolExt, PoolStatus,
    PooledConnection,
};
