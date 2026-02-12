//! LDAP connection management.

use crate::errors::{HeraclesError, Result};
use crate::ldap::config::LdapConfig;
use crate::ldap::operations::{LdapEntry, LdapModification};
use ldap3::{Ldap, LdapConnAsync, LdapConnSettings, Scope, SearchEntry};
use std::collections::HashMap;
use std::time::Duration;
use tracing::{debug, error, instrument, trace};

/// An LDAP connection that can perform operations.
pub struct LdapConnection {
    ldap: Ldap,
    config: LdapConfig,
    bound: bool,
}

impl LdapConnection {
    /// Creates a new LDAP connection.
    #[instrument(skip(config), fields(uri = %config.uri))]
    pub async fn new(config: LdapConfig) -> Result<Self> {
        config.validate()?;

        let settings = LdapConnSettings::new()
            .set_conn_timeout(Duration::from_secs(config.timeout_seconds))
            .set_starttls(config.use_tls);

        debug!("Connecting to LDAP server: {}", config.uri);

        let (conn, ldap) = LdapConnAsync::with_settings(settings, &config.uri)
            .await
            .map_err(|e| HeraclesError::LdapConnection(e.to_string()))?;

        // Spawn the connection driver
        tokio::spawn(async move {
            if let Err(e) = conn.drive().await {
                error!("LDAP connection error: {}", e);
            }
        });

        Ok(Self {
            ldap,
            config,
            bound: false,
        })
    }

    /// Binds to the LDAP server using the configured credentials.
    #[instrument(skip(self))]
    pub async fn bind(&mut self) -> Result<()> {
        debug!("Binding as: {}", self.config.bind_dn);

        self.ldap
            .simple_bind(&self.config.bind_dn, &self.config.bind_password)
            .await
            .map_err(|e| HeraclesError::LdapBind(e.to_string()))?
            .success()
            .map_err(|e| HeraclesError::LdapBind(e.to_string()))?;

        self.bound = true;
        debug!("LDAP bind successful");
        Ok(())
    }

    /// Binds with custom credentials (for user authentication).
    #[instrument(skip(self, password), fields(dn = %dn))]
    pub async fn bind_as(&mut self, dn: &str, password: &str) -> Result<()> {
        debug!("Attempting bind as: {}", dn);

        self.ldap
            .simple_bind(dn, password)
            .await
            .map_err(|e| HeraclesError::LdapBind(e.to_string()))?
            .success()
            .map_err(|e| HeraclesError::LdapBind(format!("Invalid credentials: {}", e)))?;

        debug!("Bind successful for: {}", dn);
        Ok(())
    }

    /// Searches for LDAP entries.
    ///
    /// # Arguments
    ///
    /// * `base` - The base DN to search from (relative to config base_dn if not absolute)
    /// * `scope` - Search scope (Base, OneLevel, Subtree)
    /// * `filter` - LDAP search filter
    /// * `attrs` - Attributes to retrieve (empty = all)
    #[instrument(skip(self, attrs), fields(base = %base, filter = %filter))]
    pub async fn search(
        &mut self,
        base: &str,
        scope: Scope,
        filter: &str,
        attrs: Vec<&str>,
    ) -> Result<Vec<LdapEntry>> {
        self.ensure_bound().await?;

        // Build absolute base DN
        let search_base = if base.contains('=') {
            base.to_string()
        } else if base.is_empty() {
            self.config.base_dn.clone()
        } else {
            format!("{},{}", base, self.config.base_dn)
        };

        trace!(
            "Searching: base={}, scope={:?}, filter={}",
            search_base,
            scope,
            filter
        );

        let (results, _res) = self
            .ldap
            .search(&search_base, scope, filter, attrs)
            .await
            .map_err(|e| HeraclesError::LdapSearch(e.to_string()))?
            .success()
            .map_err(|e| HeraclesError::LdapSearch(e.to_string()))?;

        let entries: Vec<LdapEntry> = results
            .into_iter()
            .filter_map(|entry| {
                let search_entry = SearchEntry::construct(entry);
                Some(LdapEntry {
                    dn: search_entry.dn,
                    attributes: search_entry
                        .attrs
                        .into_iter()
                        .map(|(k, v)| (k, v))
                        .collect(),
                })
            })
            .collect();

        debug!("Search returned {} entries", entries.len());
        Ok(entries)
    }

    /// Adds a new LDAP entry.
    #[instrument(skip(self, attributes), fields(dn = %dn))]
    pub async fn add(&mut self, dn: &str, attributes: HashMap<String, Vec<String>>) -> Result<()> {
        use std::collections::HashSet;
        self.ensure_bound().await?;

        let attrs: Vec<(String, HashSet<String>)> = attributes
            .into_iter()
            .map(|(k, v)| (k, v.into_iter().collect::<HashSet<_>>()))
            .collect();
        let attrs_ref: Vec<(&str, HashSet<&str>)> = attrs
            .iter()
            .map(|(k, v)| (k.as_str(), v.iter().map(|s| s.as_str()).collect()))
            .collect();

        debug!("Adding entry: {}", dn);

        self.ldap
            .add(dn, attrs_ref)
            .await
            .map_err(|e| HeraclesError::LdapAdd(e.to_string()))?
            .success()
            .map_err(|e| {
                if e.to_string().contains("68") || e.to_string().contains("Already exists") {
                    HeraclesError::LdapAlreadyExists(dn.to_string())
                } else {
                    HeraclesError::LdapAdd(e.to_string())
                }
            })?;

        debug!("Entry added successfully: {}", dn);
        Ok(())
    }

    /// Modifies an existing LDAP entry.
    #[instrument(skip(self, modifications), fields(dn = %dn))]
    pub async fn modify(&mut self, dn: &str, modifications: Vec<LdapModification>) -> Result<()> {
        self.ensure_bound().await?;

        let mods: Vec<ldap3::Mod<&str>> = modifications.iter().map(|m| m.to_ldap3_mod()).collect();

        debug!("Modifying entry: {} with {} changes", dn, mods.len());

        self.ldap
            .modify(dn, mods)
            .await
            .map_err(|e| HeraclesError::LdapModify(e.to_string()))?
            .success()
            .map_err(|e| {
                if e.to_string().contains("32") || e.to_string().contains("No such object") {
                    HeraclesError::LdapNotFound(dn.to_string())
                } else {
                    HeraclesError::LdapModify(e.to_string())
                }
            })?;

        debug!("Entry modified successfully: {}", dn);
        Ok(())
    }

    /// Deletes an LDAP entry.
    #[instrument(skip(self), fields(dn = %dn))]
    pub async fn delete(&mut self, dn: &str) -> Result<()> {
        self.ensure_bound().await?;

        debug!("Deleting entry: {}", dn);

        self.ldap
            .delete(dn)
            .await
            .map_err(|e| HeraclesError::LdapDelete(e.to_string()))?
            .success()
            .map_err(|e| {
                if e.to_string().contains("32") || e.to_string().contains("No such object") {
                    HeraclesError::LdapNotFound(dn.to_string())
                } else {
                    HeraclesError::LdapDelete(e.to_string())
                }
            })?;

        debug!("Entry deleted successfully: {}", dn);
        Ok(())
    }

    /// Checks if the connection is bound.
    pub fn is_bound(&self) -> bool {
        self.bound
    }

    /// Returns the base DN from the configuration.
    pub fn base_dn(&self) -> &str {
        &self.config.base_dn
    }

    /// Ensures the connection is bound before an operation.
    async fn ensure_bound(&mut self) -> Result<()> {
        if !self.bound {
            self.bind().await?;
        }
        Ok(())
    }

    /// Unbinds from the LDAP server.
    pub async fn unbind(&mut self) -> Result<()> {
        if self.bound {
            self.ldap
                .unbind()
                .await
                .map_err(|e| HeraclesError::Internal(e.to_string()))?;
            self.bound = false;
        }
        Ok(())
    }
}

impl Drop for LdapConnection {
    fn drop(&mut self) {
        self.bound = false;
    }
}
