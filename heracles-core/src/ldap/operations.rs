//! LDAP operations data structures.

use std::collections::HashMap;

/// Represents an LDAP entry with DN and attributes.
#[derive(Debug, Clone, PartialEq)]
pub struct LdapEntry {
    /// Distinguished Name of the entry.
    pub dn: String,
    /// Attributes and their values.
    pub attributes: HashMap<String, Vec<String>>,
}

impl LdapEntry {
    /// Creates a new LDAP entry.
    pub fn new(dn: impl Into<String>) -> Self {
        Self {
            dn: dn.into(),
            attributes: HashMap::new(),
        }
    }

    /// Adds an attribute with multiple values.
    pub fn with_attribute(
        mut self,
        name: impl Into<String>,
        values: Vec<impl Into<String>>,
    ) -> Self {
        self.attributes
            .insert(name.into(), values.into_iter().map(|v| v.into()).collect());
        self
    }

    /// Adds a single-valued attribute.
    pub fn with_single(mut self, name: impl Into<String>, value: impl Into<String>) -> Self {
        self.attributes.insert(name.into(), vec![value.into()]);
        self
    }

    /// Gets the first value of an attribute.
    pub fn get_first(&self, attr: &str) -> Option<&str> {
        self.attributes
            .get(attr)
            .and_then(|v| v.first())
            .map(|s| s.as_str())
    }

    /// Gets all values of an attribute.
    pub fn get_all(&self, attr: &str) -> Option<&Vec<String>> {
        self.attributes.get(attr)
    }

    /// Checks if the entry has a specific objectClass.
    pub fn has_object_class(&self, object_class: &str) -> bool {
        self.attributes
            .get("objectClass")
            .map(|classes| classes.iter().any(|c| c.eq_ignore_ascii_case(object_class)))
            .unwrap_or(false)
    }

    /// Returns the RDN (first component of the DN).
    pub fn rdn(&self) -> Option<&str> {
        self.dn.split(',').next()
    }
}

/// Represents an LDAP modification operation.
#[derive(Debug, Clone)]
pub enum LdapModification {
    /// Add values to an attribute.
    Add { attr: String, values: Vec<String> },
    /// Delete values from an attribute (empty values = delete all).
    Delete { attr: String, values: Vec<String> },
    /// Replace all values of an attribute.
    Replace { attr: String, values: Vec<String> },
}

impl LdapModification {
    /// Creates an Add modification.
    pub fn add(attr: impl Into<String>, values: Vec<impl Into<String>>) -> Self {
        Self::Add {
            attr: attr.into(),
            values: values.into_iter().map(|v| v.into()).collect(),
        }
    }

    /// Creates a Delete modification.
    pub fn delete(attr: impl Into<String>, values: Vec<impl Into<String>>) -> Self {
        Self::Delete {
            attr: attr.into(),
            values: values.into_iter().map(|v| v.into()).collect(),
        }
    }

    /// Creates a Delete modification to remove all values of an attribute.
    pub fn delete_all(attr: impl Into<String>) -> Self {
        Self::Delete {
            attr: attr.into(),
            values: vec![],
        }
    }

    /// Creates a Replace modification.
    pub fn replace(attr: impl Into<String>, values: Vec<impl Into<String>>) -> Self {
        Self::Replace {
            attr: attr.into(),
            values: values.into_iter().map(|v| v.into()).collect(),
        }
    }

    /// Creates a Replace modification with a single value.
    pub fn replace_single(attr: impl Into<String>, value: impl Into<String>) -> Self {
        Self::Replace {
            attr: attr.into(),
            values: vec![value.into()],
        }
    }

    /// Converts to ldap3 Mod type.
    pub(crate) fn to_ldap3_mod(&self) -> ldap3::Mod<&str> {
        match self {
            LdapModification::Add { attr, values } => {
                let vals: Vec<&str> = values.iter().map(|s| s.as_str()).collect();
                ldap3::Mod::Add(attr.as_str(), std::collections::HashSet::from_iter(vals))
            }
            LdapModification::Delete { attr, values } => {
                let vals: Vec<&str> = values.iter().map(|s| s.as_str()).collect();
                ldap3::Mod::Delete(attr.as_str(), std::collections::HashSet::from_iter(vals))
            }
            LdapModification::Replace { attr, values } => {
                let vals: Vec<&str> = values.iter().map(|s| s.as_str()).collect();
                ldap3::Mod::Replace(attr.as_str(), std::collections::HashSet::from_iter(vals))
            }
        }
    }
}

/// Search scope for LDAP queries.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SearchScope {
    /// Search only the base object.
    Base,
    /// Search only immediate children.
    OneLevel,
    /// Search the entire subtree.
    Subtree,
}

impl From<SearchScope> for ldap3::Scope {
    fn from(scope: SearchScope) -> Self {
        match scope {
            SearchScope::Base => ldap3::Scope::Base,
            SearchScope::OneLevel => ldap3::Scope::OneLevel,
            SearchScope::Subtree => ldap3::Scope::Subtree,
        }
    }
}

impl Default for SearchScope {
    fn default() -> Self {
        Self::Subtree
    }
}

/// Builder for LDAP search queries.
#[derive(Debug, Clone)]
pub struct SearchBuilder {
    base: String,
    scope: SearchScope,
    filter: String,
    attributes: Vec<String>,
    size_limit: Option<usize>,
}

impl SearchBuilder {
    /// Creates a new search builder.
    pub fn new(base: impl Into<String>) -> Self {
        Self {
            base: base.into(),
            scope: SearchScope::Subtree,
            filter: "(objectClass=*)".to_string(),
            attributes: vec![],
            size_limit: None,
        }
    }

    /// Sets the search scope.
    pub fn scope(mut self, scope: SearchScope) -> Self {
        self.scope = scope;
        self
    }

    /// Sets the search filter.
    pub fn filter(mut self, filter: impl Into<String>) -> Self {
        self.filter = filter.into();
        self
    }

    /// Sets the attributes to retrieve.
    pub fn attributes(mut self, attrs: Vec<impl Into<String>>) -> Self {
        self.attributes = attrs.into_iter().map(|a| a.into()).collect();
        self
    }

    /// Adds an attribute to retrieve.
    pub fn add_attribute(mut self, attr: impl Into<String>) -> Self {
        self.attributes.push(attr.into());
        self
    }

    /// Sets the size limit.
    pub fn size_limit(mut self, limit: usize) -> Self {
        self.size_limit = Some(limit);
        self
    }

    /// Returns the base DN.
    pub fn get_base(&self) -> &str {
        &self.base
    }

    /// Returns the scope.
    pub fn get_scope(&self) -> SearchScope {
        self.scope
    }

    /// Returns the filter.
    pub fn get_filter(&self) -> &str {
        &self.filter
    }

    /// Returns the attributes as string slices.
    pub fn get_attributes(&self) -> Vec<&str> {
        self.attributes.iter().map(|s| s.as_str()).collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ldap_entry_new() {
        let entry = LdapEntry::new("uid=test,ou=users,dc=example,dc=com");
        assert_eq!(entry.dn, "uid=test,ou=users,dc=example,dc=com");
        assert!(entry.attributes.is_empty());
    }

    #[test]
    fn test_ldap_entry_with_attributes() {
        let entry = LdapEntry::new("uid=test,ou=users,dc=example,dc=com")
            .with_single("cn", "Test User")
            .with_attribute("objectClass", vec!["inetOrgPerson", "posixAccount"]);

        assert_eq!(entry.get_first("cn"), Some("Test User"));
        assert!(entry.has_object_class("inetOrgPerson"));
        assert!(entry.has_object_class("posixAccount"));
        assert!(!entry.has_object_class("groupOfNames"));
    }

    #[test]
    fn test_ldap_entry_rdn() {
        let entry = LdapEntry::new("uid=test,ou=users,dc=example,dc=com");
        assert_eq!(entry.rdn(), Some("uid=test"));
    }

    #[test]
    fn test_ldap_modification_add() {
        let mod_op = LdapModification::add("memberUid", vec!["user1", "user2"]);
        match mod_op {
            LdapModification::Add { attr, values } => {
                assert_eq!(attr, "memberUid");
                assert_eq!(values, vec!["user1", "user2"]);
            }
            _ => panic!("Expected Add modification"),
        }
    }

    #[test]
    fn test_ldap_modification_replace_single() {
        let mod_op = LdapModification::replace_single("description", "New description");
        match mod_op {
            LdapModification::Replace { attr, values } => {
                assert_eq!(attr, "description");
                assert_eq!(values, vec!["New description"]);
            }
            _ => panic!("Expected Replace modification"),
        }
    }

    #[test]
    fn test_search_builder() {
        let search = SearchBuilder::new("ou=users")
            .scope(SearchScope::OneLevel)
            .filter("(uid=*)")
            .attributes(vec!["cn", "mail", "uid"])
            .size_limit(100);

        assert_eq!(search.get_base(), "ou=users");
        assert_eq!(search.get_scope(), SearchScope::OneLevel);
        assert_eq!(search.get_filter(), "(uid=*)");
        assert_eq!(search.get_attributes(), vec!["cn", "mail", "uid"]);
    }

    #[test]
    fn test_search_scope_conversion() {
        assert!(matches!(
            ldap3::Scope::from(SearchScope::Base),
            ldap3::Scope::Base
        ));
        assert!(matches!(
            ldap3::Scope::from(SearchScope::OneLevel),
            ldap3::Scope::OneLevel
        ));
        assert!(matches!(
            ldap3::Scope::from(SearchScope::Subtree),
            ldap3::Scope::Subtree
        ));
    }
}
