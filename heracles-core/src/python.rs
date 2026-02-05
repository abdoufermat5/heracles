//! Python bindings for Heracles Core.
//!
//! This module exposes heracles-core functionality to Python via PyO3.
//! Includes LDAP operations, password hashing, DN utilities, and ACL engine.

use pyo3::prelude::*;
use pyo3::exceptions::{PyConnectionError, PyRuntimeError, PyValueError};
use pyo3::types::PyDict;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::Mutex;

use crate::acl::{
    compile as rust_compile_acl, AclRow, AttrRuleRow, PermissionBitmap, UserAcl,
};
use crate::crypto::password::{
    hash_password as rust_hash_password, verify_password as rust_verify_password,
    HashMethod, PasswordHash,
};
use crate::ldap::config::LdapConfig;
use crate::ldap::connection::LdapConnection;
use crate::ldap::dn::{
    escape_dn_value as rust_escape_dn_value, escape_filter_value as rust_escape_filter_value,
    DistinguishedName,
};
use crate::ldap::operations::{LdapEntry as RustLdapEntry, LdapModification, SearchScope};

/// Registers the Python module.
pub fn register_module(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    // Password functions
    m.add_function(wrap_pyfunction!(hash_password, m)?)?;
    m.add_function(wrap_pyfunction!(verify_password, m)?)?;
    m.add_function(wrap_pyfunction!(detect_hash_method, m)?)?;

    // DN utilities
    m.add_function(wrap_pyfunction!(escape_dn_value, m)?)?;
    m.add_function(wrap_pyfunction!(escape_filter_value, m)?)?;
    m.add_function(wrap_pyfunction!(parse_dn, m)?)?;
    m.add_function(wrap_pyfunction!(build_dn, m)?)?;

    // ACL functions
    m.add_function(wrap_pyfunction!(compile_user_acl, m)?)?;

    // LDAP classes
    m.add_class::<PyLdapConnection>()?;
    m.add_class::<PyLdapEntry>()?;
    m.add_class::<PyHashMethod>()?;

    // ACL classes
    m.add_class::<PyUserAcl>()?;
    m.add_class::<PyAclRow>()?;
    m.add_class::<PyAttrRuleRow>()?;
    m.add_class::<PyPermissionBitmap>()?;

    Ok(())
}

/// Supported password hash methods.
#[pyclass(name = "HashMethod")]
#[derive(Clone)]
pub struct PyHashMethod {
    inner: HashMethod,
}

// ============================================================================
// LDAP Entry wrapper
// ============================================================================

/// Represents an LDAP entry returned from search operations.
#[pyclass(name = "LdapEntry")]
#[derive(Clone)]
pub struct PyLdapEntry {
    #[pyo3(get)]
    dn: String,
    attributes: HashMap<String, Vec<String>>,
}

#[pymethods]
impl PyLdapEntry {
    /// Get all attributes as a dictionary.
    #[getter]
    fn attributes(&self, py: Python<'_>) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        for (key, values) in &self.attributes {
            dict.set_item(key, values.clone())?;
        }
        Ok(dict.into())
    }

    /// Get the first value of an attribute.
    fn get(&self, attr: &str, default: Option<String>) -> Option<String> {
        self.attributes
            .get(attr)
            .and_then(|v| v.first())
            .cloned()
            .or(default)
    }

    /// Get all values of an attribute.
    fn get_all(&self, attr: &str) -> Vec<String> {
        self.attributes.get(attr).cloned().unwrap_or_default()
    }

    /// Check if entry has a specific objectClass.
    fn has_object_class(&self, object_class: &str) -> bool {
        self.attributes
            .get("objectClass")
            .map(|classes| classes.iter().any(|c| c.eq_ignore_ascii_case(object_class)))
            .unwrap_or(false)
    }

    fn __repr__(&self) -> String {
        format!("LdapEntry(dn='{}')", self.dn)
    }
}

impl From<RustLdapEntry> for PyLdapEntry {
    fn from(entry: RustLdapEntry) -> Self {
        Self {
            dn: entry.dn,
            attributes: entry.attributes,
        }
    }
}

// ============================================================================
// LDAP Connection wrapper
// ============================================================================

/// LDAP connection for performing operations.
///
/// Example:
///     >>> import heracles_core
///     >>> conn = heracles_core.LdapConnection(
///     ...     uri="ldap://localhost:389",
///     ...     base_dn="dc=example,dc=com",
///     ...     bind_dn="cn=admin,dc=example,dc=com",
///     ...     bind_password="secret"
///     ... )
///     >>> await conn.connect()
///     >>> entries = await conn.search("ou=users", "(objectClass=person)")
#[pyclass(name = "LdapConnection")]
pub struct PyLdapConnection {
    config: LdapConfig,
    connection: Arc<Mutex<Option<LdapConnection>>>,
}

#[pymethods]
impl PyLdapConnection {
    #[new]
    #[pyo3(signature = (uri, base_dn, bind_dn, bind_password, use_tls=false, timeout=30))]
    fn new(
        uri: String,
        base_dn: String,
        bind_dn: String,
        bind_password: String,
        use_tls: bool,
        timeout: u64,
    ) -> Self {
        let mut config = LdapConfig::new(uri, base_dn, bind_dn, bind_password);
        config.use_tls = use_tls;
        config.timeout_seconds = timeout;

        Self {
            config,
            connection: Arc::new(Mutex::new(None)),
        }
    }

    /// Connect and bind to the LDAP server.
    fn connect<'py>(&self, py: Python<'py>) -> PyResult<&'py PyAny> {
        let config = self.config.clone();
        let connection = self.connection.clone();

        pyo3_asyncio::tokio::future_into_py(py, async move {
            let mut conn = LdapConnection::new(config)
                .await
                .map_err(|e| PyConnectionError::new_err(e.to_string()))?;

            conn.bind()
                .await
                .map_err(|e| PyConnectionError::new_err(e.to_string()))?;

            let mut guard = connection.lock().await;
            *guard = Some(conn);

            Ok(())
        })
    }

    /// Disconnect from the LDAP server.
    fn disconnect<'py>(&self, py: Python<'py>) -> PyResult<&'py PyAny> {
        let connection = self.connection.clone();

        pyo3_asyncio::tokio::future_into_py(py, async move {
            let mut guard = connection.lock().await;
            if let Some(mut conn) = guard.take() {
                conn.unbind()
                    .await
                    .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
            }
            Ok(())
        })
    }

    /// Check if connected.
    fn is_connected<'py>(&self, py: Python<'py>) -> PyResult<&'py PyAny> {
        let connection = self.connection.clone();

        pyo3_asyncio::tokio::future_into_py(py, async move {
            let guard = connection.lock().await;
            Ok(guard.as_ref().map(|c| c.is_bound()).unwrap_or(false))
        })
    }

    /// Authenticate a user (bind as user then rebind as admin).
    ///
    /// Args:
    ///     user_dn: The user's DN
    ///     password: The user's password
    ///
    /// Returns:
    ///     True if authentication successful, False otherwise
    #[pyo3(signature = (user_dn, password))]
    fn authenticate<'py>(&self, py: Python<'py>, user_dn: String, password: String) -> PyResult<&'py PyAny> {
        let config = self.config.clone();
        let connection = self.connection.clone();

        pyo3_asyncio::tokio::future_into_py(py, async move {
            // Create a temporary connection for auth
            let mut auth_conn = LdapConnection::new(config.clone())
                .await
                .map_err(|e| PyConnectionError::new_err(e.to_string()))?;

            // Try to bind as the user
            match auth_conn.bind_as(&user_dn, &password).await {
                Ok(_) => {
                    // Unbind the auth connection
                    let _ = auth_conn.unbind().await;
                    Ok(true)
                }
                Err(_) => Ok(false),
            }
        })
    }

    /// Search for LDAP entries.
    ///
    /// Args:
    ///     base: Search base DN (relative to configured base_dn)
    ///     filter: LDAP search filter
    ///     scope: Search scope ("base", "onelevel", "subtree")
    ///     attributes: List of attributes to return (None = all)
    ///     size_limit: Maximum entries to return (0 = unlimited)
    #[pyo3(signature = (base, filter, scope="subtree", attributes=None, size_limit=0))]
    fn search<'py>(
        &self,
        py: Python<'py>,
        base: String,
        filter: String,
        scope: &str,
        attributes: Option<Vec<String>>,
        size_limit: i32,
    ) -> PyResult<&'py PyAny> {
        let connection = self.connection.clone();
        let search_scope = match scope {
            "base" => ldap3::Scope::Base,
            "onelevel" | "one" => ldap3::Scope::OneLevel,
            _ => ldap3::Scope::Subtree,
        };
        let attrs = attributes.unwrap_or_else(|| vec!["*".to_string()]);

        pyo3_asyncio::tokio::future_into_py(py, async move {
            let mut guard = connection.lock().await;
            let conn = guard
                .as_mut()
                .ok_or_else(|| PyConnectionError::new_err("Not connected"))?;

            let attrs_ref: Vec<&str> = attrs.iter().map(|s| s.as_str()).collect();

            let entries = conn
                .search(&base, search_scope, &filter, attrs_ref)
                .await
                .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

            let py_entries: Vec<PyLdapEntry> = entries.into_iter().map(|e| e.into()).collect();
            Ok(py_entries)
        })
    }

    /// Get a single entry by DN.
    #[pyo3(signature = (dn, attributes=None))]
    fn get_by_dn<'py>(
        &self,
        py: Python<'py>,
        dn: String,
        attributes: Option<Vec<String>>,
    ) -> PyResult<&'py PyAny> {
        let connection = self.connection.clone();
        let attrs = attributes.unwrap_or_else(|| vec!["*".to_string()]);

        pyo3_asyncio::tokio::future_into_py(py, async move {
            let mut guard = connection.lock().await;
            let conn = guard
                .as_mut()
                .ok_or_else(|| PyConnectionError::new_err("Not connected"))?;

            let attrs_ref: Vec<&str> = attrs.iter().map(|s| s.as_str()).collect();

            let entries = conn
                .search(&dn, ldap3::Scope::Base, "(objectClass=*)", attrs_ref)
                .await
                .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

            Ok(entries.into_iter().next().map(PyLdapEntry::from))
        })
    }

    /// Add a new LDAP entry.
    ///
    /// Args:
    ///     dn: Distinguished name of the entry
    ///     attributes: Dictionary of attribute name -> list of values
    #[pyo3(signature = (dn, attributes))]
    fn add<'py>(
        &self,
        py: Python<'py>,
        dn: String,
        attributes: HashMap<String, Vec<String>>,
    ) -> PyResult<&'py PyAny> {
        let connection = self.connection.clone();

        pyo3_asyncio::tokio::future_into_py(py, async move {
            let mut guard = connection.lock().await;
            let conn = guard
                .as_mut()
                .ok_or_else(|| PyConnectionError::new_err("Not connected"))?;

            conn.add(&dn, attributes)
                .await
                .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

            Ok(true)
        })
    }

    /// Modify an existing LDAP entry.
    ///
    /// Args:
    ///     dn: Distinguished name of the entry
    ///     modifications: List of (operation, attribute, values) tuples
    ///                   operation: "add", "delete", "replace"
    #[pyo3(signature = (dn, modifications))]
    fn modify<'py>(
        &self,
        py: Python<'py>,
        dn: String,
        modifications: Vec<(String, String, Vec<String>)>,
    ) -> PyResult<&'py PyAny> {
        let connection = self.connection.clone();

        pyo3_asyncio::tokio::future_into_py(py, async move {
            let mut guard = connection.lock().await;
            let conn = guard
                .as_mut()
                .ok_or_else(|| PyConnectionError::new_err("Not connected"))?;

            let mods: Vec<LdapModification> = modifications
                .into_iter()
                .map(|(op, attr, values)| match op.as_str() {
                    "add" => LdapModification::add(attr, values),
                    "delete" => LdapModification::delete(attr, values),
                    _ => LdapModification::replace(attr, values),
                })
                .collect();

            conn.modify(&dn, mods)
                .await
                .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

            Ok(true)
        })
    }

    /// Delete an LDAP entry.
    #[pyo3(signature = (dn,))]
    fn delete<'py>(&self, py: Python<'py>, dn: String) -> PyResult<&'py PyAny> {
        let connection = self.connection.clone();

        pyo3_asyncio::tokio::future_into_py(py, async move {
            let mut guard = connection.lock().await;
            let conn = guard
                .as_mut()
                .ok_or_else(|| PyConnectionError::new_err("Not connected"))?;

            conn.delete(&dn)
                .await
                .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

            Ok(true)
        })
    }

    /// Get the configured base DN.
    #[getter]
    fn base_dn(&self) -> &str {
        &self.config.base_dn
    }

    fn __repr__(&self) -> String {
        format!("LdapConnection(uri='{}', base_dn='{}')", self.config.uri, self.config.base_dn)
    }
}

#[pymethods]
impl PyHashMethod {
    #[staticmethod]
    fn ssha() -> Self {
        Self {
            inner: HashMethod::Ssha,
        }
    }

    #[staticmethod]
    fn argon2() -> Self {
        Self {
            inner: HashMethod::Argon2id,
        }
    }

    #[staticmethod]
    fn bcrypt() -> Self {
        Self {
            inner: HashMethod::Bcrypt,
        }
    }

    #[staticmethod]
    fn sha512() -> Self {
        Self {
            inner: HashMethod::Sha512,
        }
    }

    #[staticmethod]
    fn ssha512() -> Self {
        Self {
            inner: HashMethod::Ssha512,
        }
    }

    #[staticmethod]
    fn sha256() -> Self {
        Self {
            inner: HashMethod::Sha256,
        }
    }

    #[staticmethod]
    fn ssha256() -> Self {
        Self {
            inner: HashMethod::Ssha256,
        }
    }

    #[staticmethod]
    fn md5() -> Self {
        Self {
            inner: HashMethod::Md5,
        }
    }

    #[staticmethod]
    fn smd5() -> Self {
        Self {
            inner: HashMethod::Smd5,
        }
    }

    #[staticmethod]
    fn from_string(s: &str) -> PyResult<Self> {
        HashMethod::from_str(s)
            .map(|inner| Self { inner })
            .ok_or_else(|| PyValueError::new_err(format!("Unknown hash method: {}", s)))
    }

    fn scheme(&self) -> &str {
        self.inner.scheme()
    }

    fn is_secure(&self) -> bool {
        self.inner.is_secure()
    }

    fn __str__(&self) -> String {
        self.inner.scheme().to_string()
    }

    fn __repr__(&self) -> String {
        format!("HashMethod('{}')", self.inner.scheme())
    }
}

/// Hashes a password using the specified method.
///
/// Args:
///     password: The password to hash.
///     method: The hash method to use (default: "argon2").
///             Supported: "ssha", "argon2", "bcrypt", "sha512", "ssha512",
///                       "sha256", "ssha256", "md5", "smd5"
///
/// Returns:
///     The LDAP-formatted password hash (e.g., "{ARGON2}$argon2id$...").
///
/// Example:
///     >>> import heracles_core
///     >>> hash = heracles_core.hash_password("secret123")
///     >>> print(hash)
///     {ARGON2}$argon2id$v=19$m=19456,t=2,p=1$...
#[pyfunction]
#[pyo3(signature = (password, method="argon2"))]
fn hash_password(password: &str, method: &str) -> PyResult<String> {
    let hash_method = HashMethod::from_str(method)
        .ok_or_else(|| PyValueError::new_err(format!("Unknown hash method: {}", method)))?;

    rust_hash_password(password, hash_method)
        .map(|h| h.hash)
        .map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

/// Verifies a password against an LDAP password hash.
///
/// Args:
///     password: The password to verify.
///     hash: The LDAP password hash (e.g., "{SSHA}base64hash").
///
/// Returns:
///     True if the password matches, False otherwise.
///
/// Example:
///     >>> import heracles_core
///     >>> hash = heracles_core.hash_password("secret123", "ssha")
///     >>> heracles_core.verify_password("secret123", hash)
///     True
///     >>> heracles_core.verify_password("wrong", hash)
///     False
#[pyfunction]
fn verify_password(password: &str, hash: &str) -> PyResult<bool> {
    let password_hash = PasswordHash::parse(hash)
        .map_err(|e| PyValueError::new_err(format!("Invalid hash format: {}", e)))?;

    rust_verify_password(password, &password_hash)
        .map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

/// Detects the hash method from an LDAP password hash.
///
/// Args:
///     hash: The LDAP password hash.
///
/// Returns:
///     The hash method name (e.g., "ssha", "argon2") or None if unknown.
///
/// Example:
///     >>> import heracles_core
///     >>> heracles_core.detect_hash_method("{SSHA}base64hash")
///     'ssha'
#[pyfunction]
fn detect_hash_method(hash: &str) -> Option<String> {
    HashMethod::detect(hash).map(|m| match m {
        HashMethod::Ssha => "ssha".to_string(),
        HashMethod::Argon2id => "argon2".to_string(),
        HashMethod::Bcrypt => "bcrypt".to_string(),
        HashMethod::Sha512 => "sha512".to_string(),
        HashMethod::Ssha512 => "ssha512".to_string(),
        HashMethod::Sha256 => "sha256".to_string(),
        HashMethod::Ssha256 => "ssha256".to_string(),
        HashMethod::Md5 => "md5".to_string(),
        HashMethod::Smd5 => "smd5".to_string(),
        HashMethod::Plain => "plain".to_string(),
    })
}

/// Escapes a value for use in a Distinguished Name (DN).
///
/// Args:
///     value: The value to escape.
///
/// Returns:
///     The escaped value safe for use in a DN.
///
/// Example:
///     >>> import heracles_core
///     >>> heracles_core.escape_dn_value("John, Jr.")
///     'John\\, Jr.'
#[pyfunction]
fn escape_dn_value(value: &str) -> String {
    rust_escape_dn_value(value)
}

/// Escapes a value for use in an LDAP filter.
///
/// Args:
///     value: The value to escape.
///
/// Returns:
///     The escaped value safe for use in an LDAP filter.
///
/// Example:
///     >>> import heracles_core
///     >>> heracles_core.escape_filter_value("user*")
///     'user\\2a'
#[pyfunction]
fn escape_filter_value(value: &str) -> String {
    rust_escape_filter_value(value)
}

/// Parses a Distinguished Name (DN) into its components.
///
/// Args:
///     dn: The DN to parse.
///
/// Returns:
///     A list of (attribute_type, attribute_value) tuples.
///
/// Example:
///     >>> import heracles_core
///     >>> heracles_core.parse_dn("uid=test,ou=users,dc=example,dc=com")
///     [('uid', 'test'), ('ou', 'users'), ('dc', 'example'), ('dc', 'com')]
#[pyfunction]
fn parse_dn(dn: &str) -> PyResult<Vec<(String, String)>> {
    let parsed = DistinguishedName::parse(dn)
        .map_err(|e| PyValueError::new_err(format!("Invalid DN: {}", e)))?;

    Ok(parsed
        .components
        .into_iter()
        .map(|c| (c.attr_type, c.attr_value))
        .collect())
}

/// Builds a Distinguished Name (DN) from components.
///
/// Args:
///     components: A list of (attribute_type, attribute_value) tuples.
///
/// Returns:
///     The properly escaped DN string.
///
/// Example:
///     >>> import heracles_core
///     >>> heracles_core.build_dn([("uid", "test"), ("ou", "users"), ("dc", "example"), ("dc", "com")])
///     'uid=test,ou=users,dc=example,dc=com'
#[pyfunction]
fn build_dn(components: Vec<(String, String)>) -> String {
    use crate::ldap::dn::{DistinguishedName, RdnComponent};

    let dn = DistinguishedName::from_components(
        components
            .into_iter()
            .map(|(t, v)| RdnComponent::new(t, v))
            .collect(),
    );

    dn.to_string()
}

// ============================================================================
// ACL Permission Bitmap
// ============================================================================

/// Permission bitmap for fast permission checks.
///
/// Stores up to 128 permissions as a bitmap. Each permission is assigned
/// a stable bit position by the database.
///
/// Example:
///     >>> import heracles_core
///     >>> bitmap = heracles_core.PermissionBitmap.from_bit(0)
///     >>> bitmap.has_bit(0)
///     True
#[pyclass(name = "PermissionBitmap")]
#[derive(Clone)]
pub struct PyPermissionBitmap {
    inner: PermissionBitmap,
}

#[pymethods]
impl PyPermissionBitmap {
    /// Create an empty bitmap (no permissions).
    #[staticmethod]
    fn empty() -> Self {
        Self {
            inner: PermissionBitmap::EMPTY,
        }
    }

    /// Create a bitmap with all permissions set.
    #[staticmethod]
    fn all() -> Self {
        Self {
            inner: PermissionBitmap::ALL,
        }
    }

    /// Create a bitmap with a single bit set.
    #[staticmethod]
    fn from_bit(pos: u8) -> PyResult<Self> {
        if pos >= 128 {
            return Err(PyValueError::new_err("bit position must be 0-127"));
        }
        Ok(Self {
            inner: PermissionBitmap::from_bit(pos),
        })
    }

    /// Create a bitmap from multiple bit positions.
    #[staticmethod]
    fn from_bits(positions: Vec<u8>) -> Self {
        Self {
            inner: PermissionBitmap::from_bits(&positions),
        }
    }

    /// Create a bitmap from two i64 halves (from PostgreSQL BIGINT columns).
    #[staticmethod]
    fn from_halves(low: i64, high: i64) -> Self {
        Self {
            inner: PermissionBitmap::from_halves(low, high),
        }
    }

    /// Split into two i64 halves for PostgreSQL storage.
    fn to_halves(&self) -> (i64, i64) {
        self.inner.to_halves()
    }

    /// Check if this bitmap has all bits in the required bitmap.
    fn has(&self, required: &PyPermissionBitmap) -> bool {
        self.inner.has(required.inner)
    }

    /// Check if this bitmap has any bit in the required bitmap.
    fn has_any(&self, required: &PyPermissionBitmap) -> bool {
        self.inner.has_any(required.inner)
    }

    /// Check if a specific bit is set.
    fn has_bit(&self, pos: u8) -> bool {
        self.inner.has_bit(pos)
    }

    /// Union (OR) two bitmaps.
    fn union(&self, other: &PyPermissionBitmap) -> Self {
        Self {
            inner: self.inner.union(other.inner),
        }
    }

    /// Subtract (remove) bits present in other.
    fn subtract(&self, other: &PyPermissionBitmap) -> Self {
        Self {
            inner: self.inner.subtract(other.inner),
        }
    }

    /// Check if the bitmap is empty.
    fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }

    /// Count the number of set bits.
    fn count(&self) -> u32 {
        self.inner.count()
    }

    /// Get all set bit positions.
    fn to_bits(&self) -> Vec<u8> {
        self.inner.to_bits()
    }

    fn __repr__(&self) -> String {
        format!("{:?}", self.inner)
    }
}

// ============================================================================
// ACL Attribute Rule Row (for compilation)
// ============================================================================

/// A single attribute-level rule for ACL compilation.
///
/// Represents one row from acl_policy_attr_rules with expanded attributes.
#[pyclass(name = "AttrRuleRow")]
#[derive(Clone)]
pub struct PyAttrRuleRow {
    /// Object type (e.g., "user", "group").
    #[pyo3(get, set)]
    pub object_type: String,

    /// Action: "read" or "write".
    #[pyo3(get, set)]
    pub action: String,

    /// Rule type: "allow" or "deny".
    #[pyo3(get, set)]
    pub rule_type: String,

    /// Expanded attribute names.
    #[pyo3(get, set)]
    pub attributes: Vec<String>,
}

#[pymethods]
impl PyAttrRuleRow {
    #[new]
    fn new(
        object_type: String,
        action: String,
        rule_type: String,
        attributes: Vec<String>,
    ) -> Self {
        Self {
            object_type,
            action,
            rule_type,
            attributes,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "AttrRuleRow(object_type='{}', action='{}', rule_type='{}', attributes={:?})",
            self.object_type, self.action, self.rule_type, self.attributes
        )
    }
}

impl From<PyAttrRuleRow> for AttrRuleRow {
    fn from(row: PyAttrRuleRow) -> Self {
        Self {
            object_type: row.object_type,
            action: row.action,
            rule_type: row.rule_type,
            attributes: row.attributes,
        }
    }
}

// ============================================================================
// ACL Row (for compilation)
// ============================================================================

/// Raw ACL row from database for compilation.
///
/// Represents joined data from acl_assignments + acl_policies.
#[pyclass(name = "AclRow")]
#[derive(Clone)]
pub struct PyAclRow {
    /// Policy name (for debugging).
    #[pyo3(get, set)]
    pub policy_name: String,

    /// Lower 64 bits of permission bitmap.
    #[pyo3(get, set)]
    pub perm_low: i64,

    /// Upper 64 bits of permission bitmap.
    #[pyo3(get, set)]
    pub perm_high: i64,

    /// Scope DN (empty = global).
    #[pyo3(get, set)]
    pub scope_dn: String,

    /// Scope type: "base" or "subtree".
    #[pyo3(get, set)]
    pub scope_type: String,

    /// Only applies to own entry.
    #[pyo3(get, set)]
    pub self_only: bool,

    /// Is this a deny entry?
    #[pyo3(get, set)]
    pub deny: bool,

    /// Priority (higher = later).
    #[pyo3(get, set)]
    pub priority: i16,

    /// Attribute rules for this policy.
    attr_rules: Vec<PyAttrRuleRow>,
}

#[pymethods]
impl PyAclRow {
    #[new]
    #[pyo3(signature = (policy_name, perm_low, perm_high, scope_dn, scope_type, self_only, deny, priority, attr_rules=None))]
    fn new(
        policy_name: String,
        perm_low: i64,
        perm_high: i64,
        scope_dn: String,
        scope_type: String,
        self_only: bool,
        deny: bool,
        priority: i16,
        attr_rules: Option<Vec<PyAttrRuleRow>>,
    ) -> Self {
        Self {
            policy_name,
            perm_low,
            perm_high,
            scope_dn,
            scope_type,
            self_only,
            deny,
            priority,
            attr_rules: attr_rules.unwrap_or_default(),
        }
    }

    /// Get the attribute rules.
    #[getter]
    fn attr_rules(&self) -> Vec<PyAttrRuleRow> {
        self.attr_rules.clone()
    }

    /// Set the attribute rules.
    #[setter]
    fn set_attr_rules(&mut self, rules: Vec<PyAttrRuleRow>) {
        self.attr_rules = rules;
    }

    /// Add an attribute rule.
    fn add_attr_rule(&mut self, rule: PyAttrRuleRow) {
        self.attr_rules.push(rule);
    }

    fn __repr__(&self) -> String {
        format!(
            "AclRow(policy='{}', scope='{}', deny={}, priority={})",
            self.policy_name, self.scope_dn, self.deny, self.priority
        )
    }
}

impl From<PyAclRow> for AclRow {
    fn from(row: PyAclRow) -> Self {
        Self {
            policy_name: row.policy_name,
            perm_low: row.perm_low,
            perm_high: row.perm_high,
            scope_dn: row.scope_dn,
            scope_type: row.scope_type,
            self_only: row.self_only,
            deny: row.deny,
            priority: row.priority,
            attr_rules: row.attr_rules.into_iter().map(Into::into).collect(),
        }
    }
}

// ============================================================================
// User ACL (compiled, for runtime checks)
// ============================================================================

/// Precompiled ACL for a user session.
///
/// Built once at login from database rows. Provides O(1) permission checks
/// for global rules and O(n) for scoped rules (n typically < 20).
///
/// Example:
///     >>> import heracles_core
///     >>> rows = [...]  # AclRow objects from database
///     >>> acl = heracles_core.compile_user_acl("uid=john,ou=users,dc=example,dc=com", rows)
///     >>> acl.check("uid=other,ou=users,dc=example,dc=com", 0b11, 0)
///     True
#[pyclass(name = "UserAcl")]
#[derive(Clone)]
pub struct PyUserAcl {
    inner: UserAcl,
}

#[pymethods]
impl PyUserAcl {
    /// Get the user's DN.
    #[getter]
    fn user_dn(&self) -> String {
        self.inner.user_dn().to_string()
    }

    /// Check object-level permission. Returns bool.
    ///
    /// Args:
    ///     target_dn: The DN of the object being accessed.
    ///     perm_low: Lower 64 bits of required permissions.
    ///     perm_high: Upper 64 bits of required permissions.
    ///
    /// Returns:
    ///     True if user has all required permissions for the target.
    fn check(&self, target_dn: &str, perm_low: i64, perm_high: i64) -> bool {
        let required = PermissionBitmap::from_halves(perm_low, perm_high);
        self.inner.check(target_dn, required)
    }

    /// Check object-level permission with a PermissionBitmap object.
    fn check_bitmap(&self, target_dn: &str, required: &PyPermissionBitmap) -> bool {
        self.inner.check(target_dn, required.inner)
    }

    /// Check object-level + attribute-level permission.
    ///
    /// Args:
    ///     target_dn: The DN of the object.
    ///     perm_low: Lower 64 bits of required permissions.
    ///     perm_high: Upper 64 bits of required permissions.
    ///     object_type: The type of object (e.g., "user", "group").
    ///     action: The action ("read" or "write").
    ///     attribute: The specific attribute to check.
    ///
    /// Returns:
    ///     True if user has permission for the attribute on the target.
    fn check_attribute(
        &self,
        target_dn: &str,
        perm_low: i64,
        perm_high: i64,
        object_type: &str,
        action: &str,
        attribute: &str,
    ) -> bool {
        let required = PermissionBitmap::from_halves(perm_low, perm_high);
        self.inner
            .check_attribute(target_dn, required, object_type, action, attribute)
    }

    /// Filter a list of attributes, returning only permitted ones.
    ///
    /// Args:
    ///     target_dn: The DN of the object.
    ///     perm_low: Lower 64 bits of required permissions.
    ///     perm_high: Upper 64 bits of required permissions.
    ///     object_type: The type of object.
    ///     action: The action ("read" or "write").
    ///     attributes: List of attributes to filter.
    ///
    /// Returns:
    ///     List of attributes the user can access.
    fn filter_attributes(
        &self,
        target_dn: &str,
        perm_low: i64,
        perm_high: i64,
        object_type: &str,
        action: &str,
        attributes: Vec<String>,
    ) -> Vec<String> {
        let required = PermissionBitmap::from_halves(perm_low, perm_high);
        let attrs_ref: Vec<&str> = attributes.iter().map(|s| s.as_str()).collect();
        self.inner
            .filter_attributes(target_dn, required, object_type, action, &attrs_ref)
    }

    /// Get effective permissions for a target DN.
    ///
    /// Returns a PermissionBitmap with all applicable permissions.
    fn effective_permissions(&self, target_dn: &str) -> PyPermissionBitmap {
        PyPermissionBitmap {
            inner: self.inner.effective_permissions(target_dn),
        }
    }

    /// Check if target_dn is the user's own entry.
    fn is_self(&self, target_dn: &str) -> bool {
        self.inner.is_self(target_dn)
    }

    /// Serialize to JSON for Redis caching.
    fn to_json(&self) -> PyResult<String> {
        serde_json::to_string(&self.inner)
            .map_err(|e| PyRuntimeError::new_err(format!("Serialization failed: {}", e)))
    }

    /// Deserialize from JSON (for loading from Redis cache).
    #[staticmethod]
    fn from_json(json: &str) -> PyResult<Self> {
        let inner: UserAcl = serde_json::from_str(json)
            .map_err(|e| PyValueError::new_err(format!("Deserialization failed: {}", e)))?;
        Ok(Self { inner })
    }

    fn __repr__(&self) -> String {
        format!(
            "UserAcl(user_dn='{}', global_allow={}, global_deny={}, scoped_entries={})",
            self.inner.user_dn(),
            self.inner.global_allow().count(),
            self.inner.global_deny().count(),
            self.inner.scoped_entries().len()
        )
    }
}

/// Compile a UserAcl from raw database rows.
///
/// Called once at login by the Python ACL service.
/// The resulting UserAcl is cached in Redis.
///
/// Args:
///     user_dn: The DN of the user being authenticated.
///     rows: List of AclRow objects from the database query.
///
/// Returns:
///     A compiled UserAcl for runtime permission checks.
///
/// Example:
///     >>> import heracles_core
///     >>> row = heracles_core.AclRow(
///     ...     policy_name="Admin",
///     ...     perm_low=0xFFFFFFFF,
///     ...     perm_high=0,
///     ...     scope_dn="",
///     ...     scope_type="subtree",
///     ...     self_only=False,
///     ...     deny=False,
///     ...     priority=0
///     ... )
///     >>> acl = heracles_core.compile_user_acl("uid=admin,ou=users,dc=example,dc=com", [row])
#[pyfunction]
fn compile_user_acl(user_dn: &str, rows: Vec<PyAclRow>) -> PyUserAcl {
    let acl_rows: Vec<AclRow> = rows.into_iter().map(Into::into).collect();
    let inner = rust_compile_acl(user_dn, acl_rows);
    PyUserAcl { inner }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hash_method_scheme() {
        let method = PyHashMethod::ssha();
        assert_eq!(method.scheme(), "{SSHA}");
    }

    #[test]
    fn test_hash_method_from_string() {
        let method = PyHashMethod::from_string("argon2").unwrap();
        assert!(method.is_secure());
    }

    #[test]
    fn test_py_permission_bitmap() {
        let bitmap = PyPermissionBitmap::from_bits(vec![0, 1, 2]);
        assert!(bitmap.has_bit(0));
        assert!(bitmap.has_bit(1));
        assert!(bitmap.has_bit(2));
        assert!(!bitmap.has_bit(3));
    }

    #[test]
    fn test_py_acl_row_conversion() {
        let py_row = PyAclRow::new(
            "TestPolicy".to_string(),
            0b111,
            0,
            "ou=test,dc=example,dc=com".to_string(),
            "subtree".to_string(),
            false,
            false,
            5,
            None,
        );

        let rust_row: AclRow = py_row.into();
        assert_eq!(rust_row.policy_name, "TestPolicy");
        assert_eq!(rust_row.perm_low, 0b111);
        assert_eq!(rust_row.priority, 5);
    }
}
