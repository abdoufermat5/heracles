//! Python bindings for Heracles Core.
//!
//! This module exposes heracles-core functionality to Python via PyO3.

use pyo3::prelude::*;
use pyo3::exceptions::{PyRuntimeError, PyValueError};

use crate::crypto::password::{
    hash_password as rust_hash_password, verify_password as rust_verify_password,
    HashMethod, PasswordHash,
};
use crate::ldap::dn::{
    escape_dn_value as rust_escape_dn_value, escape_filter_value as rust_escape_filter_value,
    DistinguishedName,
};

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

    // Classes
    m.add_class::<PyHashMethod>()?;

    Ok(())
}

/// Supported password hash methods.
#[pyclass(name = "HashMethod")]
#[derive(Clone)]
pub struct PyHashMethod {
    inner: HashMethod,
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
///     method: The hash method to use (default: "ssha").
///             Supported: "ssha", "argon2", "bcrypt", "sha512", "ssha512",
///                       "sha256", "ssha256", "md5", "smd5"
///
/// Returns:
///     The LDAP-formatted password hash (e.g., "{SSHA}base64hash").
///
/// Example:
///     >>> import heracles_core
///     >>> hash = heracles_core.hash_password("secret123", "argon2")
///     >>> print(hash)
///     {ARGON2}$argon2id$v=19$m=19456,t=2,p=1$...
#[pyfunction]
#[pyo3(signature = (password, method="ssha"))]
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
}
