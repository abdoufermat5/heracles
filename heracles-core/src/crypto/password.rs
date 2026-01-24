//! Password hashing and verification.
//!
//! This module provides password hashing compatible with LDAP userPassword
//! attribute formats.

use crate::errors::{HeraclesError, Result};
use argon2::{
    password_hash::{rand_core::OsRng, PasswordHasher as Argon2Hasher, SaltString},
    Argon2, PasswordVerifier as Argon2Verifier,
};
use base64::{engine::general_purpose::STANDARD as BASE64, Engine};
use bcrypt::{hash as bcrypt_hash, verify as bcrypt_verify, DEFAULT_COST};
use rand::RngCore;
use sha2::{Digest, Sha256, Sha512};
use std::fmt;

/// Supported password hash methods.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HashMethod {
    /// Salted SHA-1 (LDAP standard default)
    Ssha,
    /// Argon2id (modern, recommended)
    Argon2id,
    /// bcrypt
    Bcrypt,
    /// SHA-512
    Sha512,
    /// Salted SHA-512
    Ssha512,
    /// SHA-256
    Sha256,
    /// Salted SHA-256
    Ssha256,
    /// MD5 (legacy only, insecure)
    Md5,
    /// Salted MD5 (legacy only)
    Smd5,
    /// Plain text (for testing only, never use in production)
    Plain,
}

impl HashMethod {
    /// Returns the LDAP scheme prefix for this method.
    pub fn scheme(&self) -> &'static str {
        match self {
            HashMethod::Ssha => "{SSHA}",
            HashMethod::Argon2id => "{ARGON2}",
            HashMethod::Bcrypt => "{BCRYPT}",
            HashMethod::Sha512 => "{SHA512}",
            HashMethod::Ssha512 => "{SSHA512}",
            HashMethod::Sha256 => "{SHA256}",
            HashMethod::Ssha256 => "{SSHA256}",
            HashMethod::Md5 => "{MD5}",
            HashMethod::Smd5 => "{SMD5}",
            HashMethod::Plain => "",
        }
    }

    /// Parses a hash method from a string.
    pub fn from_str(s: &str) -> Option<Self> {
        match s.to_uppercase().as_str() {
            "SSHA" | "{SSHA}" => Some(HashMethod::Ssha),
            "ARGON2" | "ARGON2ID" | "{ARGON2}" => Some(HashMethod::Argon2id),
            "BCRYPT" | "{BCRYPT}" => Some(HashMethod::Bcrypt),
            "SHA512" | "{SHA512}" => Some(HashMethod::Sha512),
            "SSHA512" | "{SSHA512}" => Some(HashMethod::Ssha512),
            "SHA256" | "{SHA256}" => Some(HashMethod::Sha256),
            "SSHA256" | "{SSHA256}" => Some(HashMethod::Ssha256),
            "MD5" | "{MD5}" => Some(HashMethod::Md5),
            "SMD5" | "{SMD5}" => Some(HashMethod::Smd5),
            "PLAIN" | "CLEAR" | "CLEARTEXT" => Some(HashMethod::Plain),
            _ => None,
        }
    }

    /// Detects the hash method from an LDAP password hash.
    pub fn detect(hash: &str) -> Option<Self> {
        let upper = hash.to_uppercase();
        if upper.starts_with("{SSHA512}") {
            Some(HashMethod::Ssha512)
        } else if upper.starts_with("{SSHA256}") {
            Some(HashMethod::Ssha256)
        } else if upper.starts_with("{SSHA}") {
            Some(HashMethod::Ssha)
        } else if upper.starts_with("{SHA512}") {
            Some(HashMethod::Sha512)
        } else if upper.starts_with("{SHA256}") {
            Some(HashMethod::Sha256)
        } else if upper.starts_with("{ARGON2}") {
            Some(HashMethod::Argon2id)
        } else if upper.starts_with("{BCRYPT}") || hash.starts_with("$2") {
            Some(HashMethod::Bcrypt)
        } else if upper.starts_with("{SMD5}") {
            Some(HashMethod::Smd5)
        } else if upper.starts_with("{MD5}") {
            Some(HashMethod::Md5)
        } else {
            None
        }
    }

    /// Returns true if this is a secure hash method.
    pub fn is_secure(&self) -> bool {
        matches!(
            self,
            HashMethod::Argon2id
                | HashMethod::Bcrypt
                | HashMethod::Ssha512
                | HashMethod::Ssha256
                | HashMethod::Ssha
        )
    }
}

impl Default for HashMethod {
    fn default() -> Self {
        HashMethod::Ssha // LDAP standard default
    }
}

impl fmt::Display for HashMethod {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.scheme())
    }
}

/// Represents a password hash with its method.
#[derive(Debug, Clone)]
pub struct PasswordHash {
    /// The hash method used.
    pub method: HashMethod,
    /// The full LDAP-formatted hash (including scheme).
    pub hash: String,
}

impl PasswordHash {
    /// Creates a new password hash.
    pub fn new(method: HashMethod, hash: String) -> Self {
        Self { method, hash }
    }

    /// Parses an LDAP password hash.
    pub fn parse(hash: &str) -> Result<Self> {
        let method = HashMethod::detect(hash)
            .ok_or_else(|| HeraclesError::UnsupportedHashMethod(hash.to_string()))?;
        Ok(Self {
            method,
            hash: hash.to_string(),
        })
    }

    /// Returns the hash value without the scheme prefix.
    pub fn value(&self) -> &str {
        let scheme_len = self.method.scheme().len();
        if self.hash.len() > scheme_len {
            &self.hash[scheme_len..]
        } else {
            &self.hash
        }
    }
}

/// Trait for password hashing.
pub trait PasswordHasher {
    /// Hashes a password using the specified method.
    fn hash(&self, password: &str, method: HashMethod) -> Result<PasswordHash>;
}

/// Trait for password verification.
pub trait PasswordVerifier {
    /// Verifies a password against a hash.
    fn verify(&self, password: &str, hash: &PasswordHash) -> Result<bool>;
}

/// Default password hasher implementation.
#[derive(Debug, Default)]
pub struct DefaultPasswordHasher;

impl PasswordHasher for DefaultPasswordHasher {
    fn hash(&self, password: &str, method: HashMethod) -> Result<PasswordHash> {
        hash_password(password, method)
    }
}

impl PasswordVerifier for DefaultPasswordHasher {
    fn verify(&self, password: &str, hash: &PasswordHash) -> Result<bool> {
        verify_password(password, hash)
    }
}

/// Hashes a password using the specified method.
pub fn hash_password(password: &str, method: HashMethod) -> Result<PasswordHash> {
    let hash = match method {
        HashMethod::Ssha => hash_ssha(password)?,
        HashMethod::Argon2id => hash_argon2(password)?,
        HashMethod::Bcrypt => hash_bcrypt(password)?,
        HashMethod::Sha512 => hash_sha512(password),
        HashMethod::Ssha512 => hash_ssha512(password)?,
        HashMethod::Sha256 => hash_sha256(password),
        HashMethod::Ssha256 => hash_ssha256(password)?,
        HashMethod::Md5 => hash_md5(password),
        HashMethod::Smd5 => hash_smd5(password)?,
        HashMethod::Plain => password.to_string(),
    };

    Ok(PasswordHash::new(method, hash))
}

/// Verifies a password against a hash.
pub fn verify_password(password: &str, hash: &PasswordHash) -> Result<bool> {
    match hash.method {
        HashMethod::Ssha => verify_ssha(password, &hash.hash),
        HashMethod::Argon2id => verify_argon2(password, &hash.hash),
        HashMethod::Bcrypt => verify_bcrypt(password, &hash.hash),
        HashMethod::Sha512 => Ok(verify_sha512(password, &hash.hash)),
        HashMethod::Ssha512 => verify_ssha512(password, &hash.hash),
        HashMethod::Sha256 => Ok(verify_sha256(password, &hash.hash)),
        HashMethod::Ssha256 => verify_ssha256(password, &hash.hash),
        HashMethod::Md5 => Ok(verify_md5(password, &hash.hash)),
        HashMethod::Smd5 => verify_smd5(password, &hash.hash),
        HashMethod::Plain => Ok(password == hash.hash),
    }
}

// ============ SSHA (Salted SHA-1) ============

fn hash_ssha(password: &str) -> Result<String> {
    use sha1::{Digest as Sha1Digest, Sha1};

    let mut salt = [0u8; 8];
    rand::thread_rng().fill_bytes(&mut salt);

    let mut hasher = Sha1::new();
    hasher.update(password.as_bytes());
    hasher.update(&salt);
    let digest = hasher.finalize();

    let mut hash_with_salt = Vec::with_capacity(digest.len() + salt.len());
    hash_with_salt.extend_from_slice(&digest);
    hash_with_salt.extend_from_slice(&salt);

    Ok(format!("{{SSHA}}{}", BASE64.encode(&hash_with_salt)))
}

fn verify_ssha(password: &str, hash: &str) -> Result<bool> {
    use sha1::{Digest as Sha1Digest, Sha1};

    let hash_value = hash
        .strip_prefix("{SSHA}")
        .or_else(|| hash.strip_prefix("{ssha}"))
        .unwrap_or(hash);

    let decoded = BASE64
        .decode(hash_value)
        .map_err(|e| HeraclesError::PasswordVerify(format!("Invalid base64: {}", e)))?;

    if decoded.len() < 20 {
        return Err(HeraclesError::PasswordVerify(
            "Invalid SSHA hash length".to_string(),
        ));
    }

    let (stored_hash, salt) = decoded.split_at(20);

    let mut hasher = Sha1::new();
    hasher.update(password.as_bytes());
    hasher.update(salt);
    let computed = hasher.finalize();

    Ok(constant_time_eq(&computed, stored_hash))
}

// ============ Argon2 ============

fn hash_argon2(password: &str) -> Result<String> {
    let salt = SaltString::generate(&mut OsRng);
    let argon2 = Argon2::default();

    let hash = argon2
        .hash_password(password.as_bytes(), &salt)
        .map_err(|e| HeraclesError::PasswordHash(format!("Argon2 hash failed: {}", e)))?
        .to_string();

    Ok(format!("{{ARGON2}}{}", hash))
}

fn verify_argon2(password: &str, hash: &str) -> Result<bool> {
    let hash_value = hash
        .strip_prefix("{ARGON2}")
        .or_else(|| hash.strip_prefix("{argon2}"))
        .unwrap_or(hash);

    let parsed = argon2::PasswordHash::new(hash_value)
        .map_err(|e| HeraclesError::PasswordVerify(format!("Invalid Argon2 hash: {}", e)))?;

    Ok(Argon2::default()
        .verify_password(password.as_bytes(), &parsed)
        .is_ok())
}

// ============ bcrypt ============

fn hash_bcrypt(password: &str) -> Result<String> {
    let hash = bcrypt_hash(password, DEFAULT_COST)
        .map_err(|e| HeraclesError::PasswordHash(format!("bcrypt hash failed: {}", e)))?;

    Ok(format!("{{BCRYPT}}{}", hash))
}

fn verify_bcrypt(password: &str, hash: &str) -> Result<bool> {
    let hash_value = hash
        .strip_prefix("{BCRYPT}")
        .or_else(|| hash.strip_prefix("{bcrypt}"))
        .unwrap_or(hash);

    bcrypt_verify(password, hash_value)
        .map_err(|e| HeraclesError::PasswordVerify(format!("bcrypt verify failed: {}", e)))
}

// ============ SHA-512 ============

fn hash_sha512(password: &str) -> String {
    let mut hasher = Sha512::new();
    hasher.update(password.as_bytes());
    let digest = hasher.finalize();
    format!("{{SHA512}}{}", BASE64.encode(&digest))
}

fn verify_sha512(password: &str, hash: &str) -> bool {
    let hash_value = hash
        .strip_prefix("{SHA512}")
        .or_else(|| hash.strip_prefix("{sha512}"))
        .unwrap_or(hash);

    let mut hasher = Sha512::new();
    hasher.update(password.as_bytes());
    let computed = hasher.finalize();
    let computed_b64 = BASE64.encode(&computed);

    hash_value == computed_b64
}

fn hash_ssha512(password: &str) -> Result<String> {
    let mut salt = [0u8; 16];
    rand::thread_rng().fill_bytes(&mut salt);

    let mut hasher = Sha512::new();
    hasher.update(password.as_bytes());
    hasher.update(&salt);
    let digest = hasher.finalize();

    let mut hash_with_salt = Vec::with_capacity(digest.len() + salt.len());
    hash_with_salt.extend_from_slice(&digest);
    hash_with_salt.extend_from_slice(&salt);

    Ok(format!("{{SSHA512}}{}", BASE64.encode(&hash_with_salt)))
}

fn verify_ssha512(password: &str, hash: &str) -> Result<bool> {
    let hash_value = hash
        .strip_prefix("{SSHA512}")
        .or_else(|| hash.strip_prefix("{ssha512}"))
        .unwrap_or(hash);

    let decoded = BASE64
        .decode(hash_value)
        .map_err(|e| HeraclesError::PasswordVerify(format!("Invalid base64: {}", e)))?;

    if decoded.len() < 64 {
        return Err(HeraclesError::PasswordVerify(
            "Invalid SSHA512 hash length".to_string(),
        ));
    }

    let (stored_hash, salt) = decoded.split_at(64);

    let mut hasher = Sha512::new();
    hasher.update(password.as_bytes());
    hasher.update(salt);
    let computed = hasher.finalize();

    Ok(constant_time_eq(&computed, stored_hash))
}

// ============ SHA-256 ============

fn hash_sha256(password: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(password.as_bytes());
    let digest = hasher.finalize();
    format!("{{SHA256}}{}", BASE64.encode(&digest))
}

fn verify_sha256(password: &str, hash: &str) -> bool {
    let hash_value = hash
        .strip_prefix("{SHA256}")
        .or_else(|| hash.strip_prefix("{sha256}"))
        .unwrap_or(hash);

    let mut hasher = Sha256::new();
    hasher.update(password.as_bytes());
    let computed = hasher.finalize();
    let computed_b64 = BASE64.encode(&computed);

    hash_value == computed_b64
}

fn hash_ssha256(password: &str) -> Result<String> {
    let mut salt = [0u8; 16];
    rand::thread_rng().fill_bytes(&mut salt);

    let mut hasher = Sha256::new();
    hasher.update(password.as_bytes());
    hasher.update(&salt);
    let digest = hasher.finalize();

    let mut hash_with_salt = Vec::with_capacity(digest.len() + salt.len());
    hash_with_salt.extend_from_slice(&digest);
    hash_with_salt.extend_from_slice(&salt);

    Ok(format!("{{SSHA256}}{}", BASE64.encode(&hash_with_salt)))
}

fn verify_ssha256(password: &str, hash: &str) -> Result<bool> {
    let hash_value = hash
        .strip_prefix("{SSHA256}")
        .or_else(|| hash.strip_prefix("{ssha256}"))
        .unwrap_or(hash);

    let decoded = BASE64
        .decode(hash_value)
        .map_err(|e| HeraclesError::PasswordVerify(format!("Invalid base64: {}", e)))?;

    if decoded.len() < 32 {
        return Err(HeraclesError::PasswordVerify(
            "Invalid SSHA256 hash length".to_string(),
        ));
    }

    let (stored_hash, salt) = decoded.split_at(32);

    let mut hasher = Sha256::new();
    hasher.update(password.as_bytes());
    hasher.update(salt);
    let computed = hasher.finalize();

    Ok(constant_time_eq(&computed, stored_hash))
}

// ============ MD5 (Legacy) ============

fn hash_md5(password: &str) -> String {
    use md5::Digest;
    let mut hasher = md5::Md5::new();
    hasher.update(password.as_bytes());
    let digest = hasher.finalize();
    format!("{{MD5}}{}", BASE64.encode(&digest))
}

fn verify_md5(password: &str, hash: &str) -> bool {
    use md5::Digest;
    let hash_value = hash
        .strip_prefix("{MD5}")
        .or_else(|| hash.strip_prefix("{md5}"))
        .unwrap_or(hash);

    let mut hasher = md5::Md5::new();
    hasher.update(password.as_bytes());
    let computed = hasher.finalize();
    let computed_b64 = BASE64.encode(&computed);

    hash_value == computed_b64
}

fn hash_smd5(password: &str) -> Result<String> {
    use md5::Digest;
    let mut salt = [0u8; 8];
    rand::thread_rng().fill_bytes(&mut salt);

    let mut hasher = md5::Md5::new();
    hasher.update(password.as_bytes());
    hasher.update(&salt);
    let digest = hasher.finalize();

    let mut hash_with_salt = Vec::with_capacity(16 + salt.len());
    hash_with_salt.extend_from_slice(&digest);
    hash_with_salt.extend_from_slice(&salt);

    Ok(format!("{{SMD5}}{}", BASE64.encode(&hash_with_salt)))
}

fn verify_smd5(password: &str, hash: &str) -> Result<bool> {
    use md5::Digest;
    let hash_value = hash
        .strip_prefix("{SMD5}")
        .or_else(|| hash.strip_prefix("{smd5}"))
        .unwrap_or(hash);

    let decoded = BASE64
        .decode(hash_value)
        .map_err(|e| HeraclesError::PasswordVerify(format!("Invalid base64: {}", e)))?;

    if decoded.len() < 16 {
        return Err(HeraclesError::PasswordVerify(
            "Invalid SMD5 hash length".to_string(),
        ));
    }

    let (stored_hash, salt) = decoded.split_at(16);

    let mut hasher = md5::Md5::new();
    hasher.update(password.as_bytes());
    hasher.update(salt);
    let computed = hasher.finalize();

    Ok(constant_time_eq(&computed, stored_hash))
}

// ============ Utilities ============

/// Constant-time comparison to prevent timing attacks.
fn constant_time_eq(a: &[u8], b: &[u8]) -> bool {
    if a.len() != b.len() {
        return false;
    }

    let mut result = 0u8;
    for (x, y) in a.iter().zip(b.iter()) {
        result |= x ^ y;
    }
    result == 0
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ssha_hash_verify() {
        let password = "test_password_123";
        let hash = hash_password(password, HashMethod::Ssha).unwrap();

        assert!(hash.hash.starts_with("{SSHA}"));
        assert!(verify_password(password, &hash).unwrap());
        assert!(!verify_password("wrong_password", &hash).unwrap());
    }

    #[test]
    fn test_argon2_hash_verify() {
        let password = "secure_password_456";
        let hash = hash_password(password, HashMethod::Argon2id).unwrap();

        assert!(hash.hash.starts_with("{ARGON2}"));
        assert!(verify_password(password, &hash).unwrap());
        assert!(!verify_password("wrong_password", &hash).unwrap());
    }

    #[test]
    fn test_bcrypt_hash_verify() {
        let password = "bcrypt_password_789";
        let hash = hash_password(password, HashMethod::Bcrypt).unwrap();

        assert!(hash.hash.starts_with("{BCRYPT}"));
        assert!(verify_password(password, &hash).unwrap());
        assert!(!verify_password("wrong_password", &hash).unwrap());
    }

    #[test]
    fn test_sha512_hash_verify() {
        let password = "sha512_password";
        let hash = hash_password(password, HashMethod::Sha512).unwrap();

        assert!(hash.hash.starts_with("{SHA512}"));
        assert!(verify_password(password, &hash).unwrap());
        assert!(!verify_password("wrong", &hash).unwrap());
    }

    #[test]
    fn test_ssha512_hash_verify() {
        let password = "ssha512_password";
        let hash = hash_password(password, HashMethod::Ssha512).unwrap();

        assert!(hash.hash.starts_with("{SSHA512}"));
        assert!(verify_password(password, &hash).unwrap());
        assert!(!verify_password("wrong", &hash).unwrap());
    }

    #[test]
    fn test_sha256_hash_verify() {
        let password = "sha256_password";
        let hash = hash_password(password, HashMethod::Sha256).unwrap();

        assert!(hash.hash.starts_with("{SHA256}"));
        assert!(verify_password(password, &hash).unwrap());
        assert!(!verify_password("wrong", &hash).unwrap());
    }

    #[test]
    fn test_ssha256_hash_verify() {
        let password = "ssha256_password";
        let hash = hash_password(password, HashMethod::Ssha256).unwrap();

        assert!(hash.hash.starts_with("{SSHA256}"));
        assert!(verify_password(password, &hash).unwrap());
        assert!(!verify_password("wrong", &hash).unwrap());
    }

    #[test]
    fn test_md5_hash_verify() {
        let password = "md5_password";
        let hash = hash_password(password, HashMethod::Md5).unwrap();

        assert!(hash.hash.starts_with("{MD5}"));
        assert!(verify_password(password, &hash).unwrap());
        assert!(!verify_password("wrong", &hash).unwrap());
    }

    #[test]
    fn test_smd5_hash_verify() {
        let password = "smd5_password";
        let hash = hash_password(password, HashMethod::Smd5).unwrap();

        assert!(hash.hash.starts_with("{SMD5}"));
        assert!(verify_password(password, &hash).unwrap());
        assert!(!verify_password("wrong", &hash).unwrap());
    }

    #[test]
    fn test_hash_method_detection() {
        assert_eq!(HashMethod::detect("{SSHA}abc123"), Some(HashMethod::Ssha));
        assert_eq!(
            HashMethod::detect("{ARGON2}$argon2id$v=19..."),
            Some(HashMethod::Argon2id)
        );
        assert_eq!(HashMethod::detect("{BCRYPT}$2b$..."), Some(HashMethod::Bcrypt));
        assert_eq!(
            HashMethod::detect("{SHA512}abc123"),
            Some(HashMethod::Sha512)
        );
        assert_eq!(HashMethod::detect("plaintext"), None);
    }

    #[test]
    fn test_hash_method_is_secure() {
        assert!(HashMethod::Argon2id.is_secure());
        assert!(HashMethod::Bcrypt.is_secure());
        assert!(HashMethod::Ssha512.is_secure());
        assert!(HashMethod::Ssha.is_secure());
        assert!(!HashMethod::Md5.is_secure());
        assert!(!HashMethod::Plain.is_secure());
    }

    #[test]
    fn test_password_hash_parse() {
        let hash = PasswordHash::parse("{SSHA}abc123xyz").unwrap();
        assert_eq!(hash.method, HashMethod::Ssha);
        assert_eq!(hash.value(), "abc123xyz");
    }

    #[test]
    fn test_constant_time_eq() {
        assert!(constant_time_eq(b"hello", b"hello"));
        assert!(!constant_time_eq(b"hello", b"world"));
        assert!(!constant_time_eq(b"hello", b"hell"));
    }

    #[test]
    fn test_default_hasher() {
        let hasher = DefaultPasswordHasher;
        let password = "test123";
        let hash = hasher.hash(password, HashMethod::Ssha).unwrap();
        assert!(hasher.verify(password, &hash).unwrap());
    }
}
