//! Distinguished Name (DN) utilities.

use crate::errors::{HeraclesError, Result};
use std::fmt;

/// Represents a parsed Distinguished Name component.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RdnComponent {
    /// Attribute type (e.g., "uid", "cn", "ou")
    pub attr_type: String,
    /// Attribute value
    pub attr_value: String,
}

impl RdnComponent {
    /// Creates a new RDN component.
    pub fn new(attr_type: impl Into<String>, attr_value: impl Into<String>) -> Self {
        Self {
            attr_type: attr_type.into(),
            attr_value: attr_value.into(),
        }
    }

    /// Parses an RDN component from string (e.g., "uid=test").
    pub fn parse(s: &str) -> Result<Self> {
        let parts: Vec<&str> = s.splitn(2, '=').collect();
        if parts.len() != 2 {
            return Err(HeraclesError::Schema(format!("Invalid RDN: {}", s)));
        }
        Ok(Self {
            attr_type: parts[0].trim().to_string(),
            attr_value: unescape_dn_value(parts[1].trim()),
        })
    }
}

impl fmt::Display for RdnComponent {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}={}", self.attr_type, escape_dn_value(&self.attr_value))
    }
}

/// Represents a full Distinguished Name.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DistinguishedName {
    /// RDN components from left to right (most specific to least specific).
    pub components: Vec<RdnComponent>,
}

impl DistinguishedName {
    /// Creates an empty DN.
    pub fn empty() -> Self {
        Self { components: vec![] }
    }

    /// Creates a DN from components.
    pub fn from_components(components: Vec<RdnComponent>) -> Self {
        Self { components }
    }

    /// Parses a DN from string.
    pub fn parse(dn: &str) -> Result<Self> {
        if dn.is_empty() {
            return Ok(Self::empty());
        }

        let parts = split_dn(dn);
        let components: Result<Vec<RdnComponent>> =
            parts.into_iter().map(|p| RdnComponent::parse(&p)).collect();

        Ok(Self {
            components: components?,
        })
    }

    /// Returns the RDN (first component).
    pub fn rdn(&self) -> Option<&RdnComponent> {
        self.components.first()
    }

    /// Returns the parent DN.
    pub fn parent(&self) -> Option<Self> {
        if self.components.len() <= 1 {
            None
        } else {
            Some(Self {
                components: self.components[1..].to_vec(),
            })
        }
    }

    /// Returns the RDN value (e.g., "test" for "uid=test,ou=users,dc=example,dc=com").
    pub fn rdn_value(&self) -> Option<&str> {
        self.rdn().map(|r| r.attr_value.as_str())
    }

    /// Returns the RDN attribute type (e.g., "uid" for "uid=test,ou=users,dc=example,dc=com").
    pub fn rdn_type(&self) -> Option<&str> {
        self.rdn().map(|r| r.attr_type.as_str())
    }

    /// Checks if this DN is under the given base DN.
    pub fn is_under(&self, base: &DistinguishedName) -> bool {
        if base.components.len() > self.components.len() {
            return false;
        }

        let offset = self.components.len() - base.components.len();
        self.components[offset..] == base.components
    }

    /// Appends another DN (base) to this DN.
    pub fn append(&self, base: &DistinguishedName) -> Self {
        let mut components = self.components.clone();
        components.extend(base.components.clone());
        Self { components }
    }

    /// Returns the number of components.
    pub fn len(&self) -> usize {
        self.components.len()
    }

    /// Checks if the DN is empty.
    pub fn is_empty(&self) -> bool {
        self.components.is_empty()
    }

    /// Converts to canonical lowercase form.
    pub fn to_canonical(&self) -> Self {
        Self {
            components: self
                .components
                .iter()
                .map(|c| RdnComponent {
                    attr_type: c.attr_type.to_lowercase(),
                    attr_value: c.attr_value.clone(),
                })
                .collect(),
        }
    }
}

impl fmt::Display for DistinguishedName {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let parts: Vec<String> = self.components.iter().map(|c| c.to_string()).collect();
        write!(f, "{}", parts.join(","))
    }
}

impl From<&str> for DistinguishedName {
    fn from(s: &str) -> Self {
        Self::parse(s).unwrap_or_else(|_| Self::empty())
    }
}

impl From<String> for DistinguishedName {
    fn from(s: String) -> Self {
        Self::from(s.as_str())
    }
}

/// Builds a DN from parts.
#[derive(Debug, Default)]
pub struct DnBuilder {
    components: Vec<RdnComponent>,
}

impl DnBuilder {
    /// Creates a new DN builder.
    pub fn new() -> Self {
        Self::default()
    }

    /// Adds a component to the DN.
    pub fn add(mut self, attr_type: impl Into<String>, attr_value: impl Into<String>) -> Self {
        self.components
            .push(RdnComponent::new(attr_type, attr_value));
        self
    }

    /// Adds a uid component.
    pub fn uid(self, value: impl Into<String>) -> Self {
        self.add("uid", value)
    }

    /// Adds a cn component.
    pub fn cn(self, value: impl Into<String>) -> Self {
        self.add("cn", value)
    }

    /// Adds an ou component.
    pub fn ou(self, value: impl Into<String>) -> Self {
        self.add("ou", value)
    }

    /// Adds a dc component.
    pub fn dc(self, value: impl Into<String>) -> Self {
        self.add("dc", value)
    }

    /// Appends a base DN string.
    pub fn base(mut self, base: &str) -> Self {
        if let Ok(dn) = DistinguishedName::parse(base) {
            self.components.extend(dn.components);
        }
        self
    }

    /// Builds the DN.
    pub fn build(self) -> DistinguishedName {
        DistinguishedName::from_components(self.components)
    }
}

/// Escapes special characters in a DN value according to RFC 4514.
pub fn escape_dn_value(value: &str) -> String {
    let mut result = String::with_capacity(value.len() * 2);

    for (i, c) in value.chars().enumerate() {
        match c {
            // Characters that must be escaped
            '"' | '+' | ',' | ';' | '<' | '>' | '\\' => {
                result.push('\\');
                result.push(c);
            }
            // Space at beginning or end
            ' ' if i == 0 || i == value.len() - 1 => {
                result.push('\\');
                result.push(c);
            }
            // Hash at beginning
            '#' if i == 0 => {
                result.push('\\');
                result.push(c);
            }
            // Equals sign (for safety)
            '=' => {
                result.push('\\');
                result.push(c);
            }
            // Normal character
            _ => result.push(c),
        }
    }

    result
}

/// Unescapes a DN value.
pub fn unescape_dn_value(value: &str) -> String {
    let mut result = String::with_capacity(value.len());
    let mut chars = value.chars().peekable();

    while let Some(c) = chars.next() {
        if c == '\\' {
            let next = chars.next();
            match next {
                None => {
                    result.push('\\');
                    break;
                }
                Some(n1) => {
                    if n1.is_ascii_hexdigit() {
                        let n2 = chars.next();
                        if let Some(n2) = n2 {
                            if n2.is_ascii_hexdigit() {
                                if let Ok(byte) =
                                    u8::from_str_radix(&format!("{}{}", n1, n2), 16)
                                {
                                    result.push(byte as char);
                                    continue;
                                }
                            }
                            result.push(n1);
                            result.push(n2);
                            continue;
                        }
                        result.push(n1);
                        break;
                    }
                    result.push(n1);
                }
            }
        } else {
            result.push(c);
        }
    }

    result
}

/// Splits a DN into RDN components, handling escaped commas.
fn split_dn(dn: &str) -> Vec<String> {
    let mut result = Vec::new();
    let mut current = String::new();
    let mut escaped = false;

    for c in dn.chars() {
        if escaped {
            current.push(c);
            escaped = false;
        } else if c == '\\' {
            current.push(c);
            escaped = true;
        } else if c == ',' {
            if !current.is_empty() {
                result.push(current.trim().to_string());
            }
            current = String::new();
        } else {
            current.push(c);
        }
    }

    if !current.is_empty() {
        result.push(current.trim().to_string());
    }

    result
}

/// Escapes special characters in an LDAP filter value according to RFC 4515.
pub fn escape_filter_value(value: &str) -> String {
    let mut result = String::with_capacity(value.len() * 3);

    for c in value.chars() {
        match c {
            '*' => result.push_str("\\2a"),
            '(' => result.push_str("\\28"),
            ')' => result.push_str("\\29"),
            '\\' => result.push_str("\\5c"),
            '\0' => result.push_str("\\00"),
            _ => result.push(c),
        }
    }

    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rdn_component_parse() {
        let rdn = RdnComponent::parse("uid=testuser").unwrap();
        assert_eq!(rdn.attr_type, "uid");
        assert_eq!(rdn.attr_value, "testuser");
    }

    #[test]
    fn test_rdn_component_display() {
        let rdn = RdnComponent::new("cn", "Test, User");
        assert_eq!(rdn.to_string(), "cn=Test\\, User");
    }

    #[test]
    fn test_dn_parse() {
        let dn = DistinguishedName::parse("uid=test,ou=users,dc=example,dc=com").unwrap();
        assert_eq!(dn.components.len(), 4);
        assert_eq!(dn.rdn_type(), Some("uid"));
        assert_eq!(dn.rdn_value(), Some("test"));
    }

    #[test]
    fn test_dn_display() {
        let dn = DistinguishedName::parse("uid=test,ou=users,dc=example,dc=com").unwrap();
        assert_eq!(dn.to_string(), "uid=test,ou=users,dc=example,dc=com");
    }

    #[test]
    fn test_dn_parent() {
        let dn = DistinguishedName::parse("uid=test,ou=users,dc=example,dc=com").unwrap();
        let parent = dn.parent().unwrap();
        assert_eq!(parent.to_string(), "ou=users,dc=example,dc=com");
    }

    #[test]
    fn test_dn_is_under() {
        let dn = DistinguishedName::parse("uid=test,ou=users,dc=example,dc=com").unwrap();
        let base = DistinguishedName::parse("dc=example,dc=com").unwrap();
        let other = DistinguishedName::parse("dc=other,dc=com").unwrap();

        assert!(dn.is_under(&base));
        assert!(!dn.is_under(&other));
    }

    #[test]
    fn test_dn_builder() {
        let dn = DnBuilder::new()
            .uid("testuser")
            .ou("users")
            .dc("example")
            .dc("com")
            .build();

        assert_eq!(dn.to_string(), "uid=testuser,ou=users,dc=example,dc=com");
    }

    #[test]
    fn test_dn_builder_with_base() {
        let dn = DnBuilder::new()
            .uid("testuser")
            .base("ou=users,dc=example,dc=com")
            .build();

        assert_eq!(dn.to_string(), "uid=testuser,ou=users,dc=example,dc=com");
    }

    #[test]
    fn test_escape_dn_value() {
        assert_eq!(escape_dn_value("simple"), "simple");
        assert_eq!(escape_dn_value("with,comma"), "with\\,comma");
        assert_eq!(escape_dn_value("with+plus"), "with\\+plus");
        assert_eq!(escape_dn_value(" leading"), "\\ leading");
        assert_eq!(escape_dn_value("trailing "), "trailing\\ ");
        assert_eq!(escape_dn_value("#hash"), "\\#hash");
    }

    #[test]
    fn test_unescape_dn_value() {
        assert_eq!(unescape_dn_value("simple"), "simple");
        assert_eq!(unescape_dn_value("with\\,comma"), "with,comma");
        assert_eq!(unescape_dn_value("with\\+plus"), "with+plus");
        assert_eq!(unescape_dn_value("\\ leading"), " leading");
    }

    #[test]
    fn test_escape_filter_value() {
        assert_eq!(escape_filter_value("simple"), "simple");
        assert_eq!(escape_filter_value("with*wildcard"), "with\\2awildcard");
        assert_eq!(escape_filter_value("(parens)"), "\\28parens\\29");
        assert_eq!(escape_filter_value("back\\slash"), "back\\5cslash");
    }

    #[test]
    fn test_split_dn_with_escaped_comma() {
        let parts = split_dn("cn=Test\\, User,ou=users,dc=example,dc=com");
        assert_eq!(parts.len(), 4);
        assert_eq!(parts[0], "cn=Test\\, User");
    }

    #[test]
    fn test_dn_canonical() {
        let dn = DistinguishedName::parse("UID=Test,OU=Users,DC=Example,DC=COM").unwrap();
        let canonical = dn.to_canonical();
        assert_eq!(canonical.rdn_type(), Some("uid"));
    }
}
