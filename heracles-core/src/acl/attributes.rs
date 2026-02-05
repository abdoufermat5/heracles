//! Attribute-level access control using group-based filtering.
//!
//! Provides fine-grained control over which LDAP attributes a user
//! can read or write, organized into logical groups (e.g., "identity",
//! "contact", "security") rather than individual attribute checkboxes.

use serde::{Deserialize, Serialize};
use std::collections::HashSet;

/// Resolved attribute rules for one (object_type, action) pair.
///
/// Built at compile time from `acl_policy_attr_rules` + `acl_attribute_groups`.
/// Provides O(1) attribute permission checks.
///
/// # Access Control Model
///
/// - If NO allow rules exist: all attributes are allowed (open by default)
/// - If ANY allow rules exist: only those groups are permitted (whitelist mode)
/// - Deny rules always win over allow rules
///
/// # Example
///
/// ```rust
/// use heracles_core::acl::AttributeFilter;
/// use std::collections::HashSet;
///
/// // Create a filter that allows only "identity" and "contact" groups
/// let allowed: HashSet<String> = ["cn", "sn", "mail", "telephoneNumber"]
///     .iter().map(|s| s.to_string()).collect();
/// let denied: HashSet<String> = ["userPassword"].iter().map(|s| s.to_string()).collect();
///
/// let filter = AttributeFilter::new(Some(allowed), denied);
///
/// assert!(filter.is_attribute_permitted("cn"));
/// assert!(filter.is_attribute_permitted("mail"));
/// assert!(!filter.is_attribute_permitted("userPassword")); // Explicitly denied
/// assert!(!filter.is_attribute_permitted("homeDirectory")); // Not in allow list
/// ```
#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct AttributeFilter {
    /// If Some, only these attributes are allowed (whitelist mode).
    /// If None, all attributes are allowed (no allow rules defined).
    allowed: Option<HashSet<String>>,
    /// Always applied — these attributes are stripped regardless.
    denied: HashSet<String>,
}

impl AttributeFilter {
    /// Create a new attribute filter.
    ///
    /// # Arguments
    ///
    /// * `allowed` - If Some, only these attributes are permitted (whitelist).
    ///               If None, all attributes are allowed except denied ones.
    /// * `denied` - These attributes are always blocked, regardless of allowed.
    pub fn new(allowed: Option<HashSet<String>>, denied: HashSet<String>) -> Self {
        // Normalize to lowercase for case-insensitive comparison
        let allowed = allowed.map(|set| {
            set.into_iter()
                .map(|s| s.to_ascii_lowercase())
                .collect()
        });
        let denied = denied
            .into_iter()
            .map(|s| s.to_ascii_lowercase())
            .collect();

        Self { allowed, denied }
    }

    /// Create a filter that allows all attributes (no restrictions).
    pub fn allow_all() -> Self {
        Self {
            allowed: None,
            denied: HashSet::new(),
        }
    }

    /// Create a filter that denies all attributes.
    pub fn deny_all() -> Self {
        Self {
            allowed: Some(HashSet::new()),
            denied: HashSet::new(),
        }
    }

    /// Create a filter with only an allow list (whitelist mode).
    pub fn with_allowed<I, S>(attrs: I) -> Self
    where
        I: IntoIterator<Item = S>,
        S: AsRef<str>,
    {
        let allowed: HashSet<String> = attrs
            .into_iter()
            .map(|s| s.as_ref().to_ascii_lowercase())
            .collect();
        Self {
            allowed: Some(allowed),
            denied: HashSet::new(),
        }
    }

    /// Create a filter with only a deny list.
    pub fn with_denied<I, S>(attrs: I) -> Self
    where
        I: IntoIterator<Item = S>,
        S: AsRef<str>,
    {
        let denied: HashSet<String> = attrs
            .into_iter()
            .map(|s| s.as_ref().to_ascii_lowercase())
            .collect();
        Self {
            allowed: None,
            denied,
        }
    }

    /// Check if a specific attribute is permitted.
    ///
    /// # Rules
    ///
    /// 1. If attribute is in deny list → denied
    /// 2. If no allow list (None) → allowed
    /// 3. If allow list exists → must be in allow list
    pub fn is_attribute_permitted(&self, attr: &str) -> bool {
        let attr_lower = attr.to_ascii_lowercase();

        // Deny always wins
        if self.denied.contains(&attr_lower) {
            return false;
        }

        // If no whitelist, everything (not denied) is allowed
        match &self.allowed {
            None => true,
            Some(allowed) => allowed.contains(&attr_lower),
        }
    }

    /// Filter a list of attributes, returning only permitted ones.
    pub fn filter_attributes<'a>(&self, attrs: &[&'a str]) -> Vec<&'a str> {
        attrs
            .iter()
            .copied()
            .filter(|attr| self.is_attribute_permitted(attr))
            .collect()
    }

    /// Filter a list of owned strings, returning only permitted ones.
    pub fn filter_attributes_owned(&self, attrs: &[String]) -> Vec<String> {
        attrs
            .iter()
            .filter(|attr| self.is_attribute_permitted(attr))
            .cloned()
            .collect()
    }

    /// Get the set of allowed attributes, if in whitelist mode.
    pub fn allowed(&self) -> Option<&HashSet<String>> {
        self.allowed.as_ref()
    }

    /// Get the set of denied attributes.
    pub fn denied(&self) -> &HashSet<String> {
        &self.denied
    }

    /// Check if this filter is in whitelist mode.
    pub fn is_whitelist_mode(&self) -> bool {
        self.allowed.is_some()
    }

    /// Check if this filter allows all attributes (no restrictions).
    pub fn is_allow_all(&self) -> bool {
        self.allowed.is_none() && self.denied.is_empty()
    }

    /// Merge another filter into this one.
    ///
    /// # Merge Rules
    ///
    /// - Deny sets are unioned (if ANY policy denies it, it's denied)
    /// - Allow sets are unioned (if ANY policy allows it, it's allowed)
    /// - If either filter is "allow all", the result is the union of allows from the other
    pub fn merge(&mut self, other: &AttributeFilter) {
        // Merge denies (union — if ANY policy denies it, denied)
        self.denied = self.denied.union(&other.denied).cloned().collect();

        // Merge allows (union — expand what's allowed)
        match (&mut self.allowed, &other.allowed) {
            // Both have whitelists: union them
            (Some(self_allowed), Some(other_allowed)) => {
                *self_allowed = self_allowed.union(other_allowed).cloned().collect();
            }
            // Self has whitelist, other allows all: keep self's whitelist
            // (other doesn't restrict, so we don't expand)
            (Some(_), None) => {}
            // Self allows all, other has whitelist: adopt other's whitelist
            (None, Some(other_allowed)) => {
                self.allowed = Some(other_allowed.clone());
            }
            // Both allow all: stay as allow all
            (None, None) => {}
        }
    }

    /// Create a merged filter from two filters.
    pub fn merged(&self, other: &AttributeFilter) -> Self {
        let mut result = self.clone();
        result.merge(other);
        result
    }

    /// Add attributes to the allow list.
    ///
    /// If currently in "allow all" mode, switches to whitelist mode
    /// with only the specified attributes.
    pub fn add_allowed<I, S>(&mut self, attrs: I)
    where
        I: IntoIterator<Item = S>,
        S: AsRef<str>,
    {
        let new_attrs: HashSet<String> = attrs
            .into_iter()
            .map(|s| s.as_ref().to_ascii_lowercase())
            .collect();

        match &mut self.allowed {
            Some(allowed) => {
                allowed.extend(new_attrs);
            }
            None => {
                self.allowed = Some(new_attrs);
            }
        }
    }

    /// Add attributes to the deny list.
    pub fn add_denied<I, S>(&mut self, attrs: I)
    where
        I: IntoIterator<Item = S>,
        S: AsRef<str>,
    {
        self.denied.extend(
            attrs
                .into_iter()
                .map(|s| s.as_ref().to_ascii_lowercase()),
        );
    }
}

/// Per-object-type attribute ACL: covers both read and write attribute filters.
///
/// Used to efficiently answer:
/// - "What attributes of a User can this person READ?"
/// - "What attributes of a User can this person WRITE?"
#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct ObjectAttributeAcl {
    /// Filter for read operations.
    pub read: AttributeFilter,
    /// Filter for write operations.
    pub write: AttributeFilter,
}

impl ObjectAttributeAcl {
    /// Create a new object attribute ACL.
    pub fn new(read: AttributeFilter, write: AttributeFilter) -> Self {
        Self { read, write }
    }

    /// Create an ACL that allows all reads and writes.
    pub fn allow_all() -> Self {
        Self {
            read: AttributeFilter::allow_all(),
            write: AttributeFilter::allow_all(),
        }
    }

    /// Create an ACL that denies all reads and writes.
    pub fn deny_all() -> Self {
        Self {
            read: AttributeFilter::deny_all(),
            write: AttributeFilter::deny_all(),
        }
    }

    /// Merge another object ACL into this one.
    pub fn merge(&mut self, other: &ObjectAttributeAcl) {
        self.read.merge(&other.read);
        self.write.merge(&other.write);
    }

    /// Filter attributes for a read operation.
    pub fn filter_read<'a>(&self, attrs: &[&'a str]) -> Vec<&'a str> {
        self.read.filter_attributes(attrs)
    }

    /// Filter attributes for a write operation.
    pub fn filter_write<'a>(&self, attrs: &[&'a str]) -> Vec<&'a str> {
        self.write.filter_attributes(attrs)
    }

    /// Check if a specific attribute can be read.
    pub fn can_read(&self, attr: &str) -> bool {
        self.read.is_attribute_permitted(attr)
    }

    /// Check if a specific attribute can be written.
    pub fn can_write(&self, attr: &str) -> bool {
        self.write.is_attribute_permitted(attr)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_allow_all() {
        let filter = AttributeFilter::allow_all();
        assert!(filter.is_attribute_permitted("anything"));
        assert!(filter.is_attribute_permitted("userPassword"));
        assert!(filter.is_allow_all());
    }

    #[test]
    fn test_deny_all() {
        let filter = AttributeFilter::deny_all();
        assert!(!filter.is_attribute_permitted("anything"));
        assert!(!filter.is_attribute_permitted("cn"));
    }

    #[test]
    fn test_whitelist_mode() {
        let filter = AttributeFilter::with_allowed(["cn", "sn", "mail"]);

        assert!(filter.is_attribute_permitted("cn"));
        assert!(filter.is_attribute_permitted("CN")); // Case insensitive
        assert!(filter.is_attribute_permitted("sn"));
        assert!(filter.is_attribute_permitted("mail"));
        assert!(!filter.is_attribute_permitted("telephoneNumber"));
        assert!(filter.is_whitelist_mode());
    }

    #[test]
    fn test_deny_list() {
        let filter = AttributeFilter::with_denied(["userPassword", "sshPublicKey"]);

        assert!(filter.is_attribute_permitted("cn"));
        assert!(filter.is_attribute_permitted("mail"));
        assert!(!filter.is_attribute_permitted("userPassword"));
        assert!(!filter.is_attribute_permitted("USERPASSWORD")); // Case insensitive
        assert!(!filter.is_attribute_permitted("sshPublicKey"));
        assert!(!filter.is_whitelist_mode());
    }

    #[test]
    fn test_combined_allow_deny() {
        let allowed: HashSet<String> = ["cn", "sn", "userPassword"]
            .iter()
            .map(|s| s.to_string())
            .collect();
        let denied: HashSet<String> = ["userPassword"]
            .iter()
            .map(|s| s.to_string())
            .collect();

        let filter = AttributeFilter::new(Some(allowed), denied);

        // In allow list but also in deny list → denied
        assert!(!filter.is_attribute_permitted("userPassword"));
        // In allow list only → allowed
        assert!(filter.is_attribute_permitted("cn"));
        assert!(filter.is_attribute_permitted("sn"));
        // Not in allow list → denied
        assert!(!filter.is_attribute_permitted("mail"));
    }

    #[test]
    fn test_filter_attributes() {
        let filter = AttributeFilter::with_allowed(["cn", "sn", "mail"]);
        let attrs = vec!["cn", "sn", "mail", "telephoneNumber", "homeDirectory"];
        let filtered = filter.filter_attributes(&attrs);

        assert_eq!(filtered, vec!["cn", "sn", "mail"]);
    }

    #[test]
    fn test_merge_denies_union() {
        let mut filter1 = AttributeFilter::with_denied(["userPassword"]);
        let filter2 = AttributeFilter::with_denied(["sshPublicKey"]);

        filter1.merge(&filter2);

        assert!(!filter1.is_attribute_permitted("userPassword"));
        assert!(!filter1.is_attribute_permitted("sshPublicKey"));
        assert!(filter1.is_attribute_permitted("cn"));
    }

    #[test]
    fn test_merge_allows_union() {
        let mut filter1 = AttributeFilter::with_allowed(["cn", "sn"]);
        let filter2 = AttributeFilter::with_allowed(["mail", "telephoneNumber"]);

        filter1.merge(&filter2);

        // Both sets should be unioned
        assert!(filter1.is_attribute_permitted("cn"));
        assert!(filter1.is_attribute_permitted("sn"));
        assert!(filter1.is_attribute_permitted("mail"));
        assert!(filter1.is_attribute_permitted("telephoneNumber"));
        assert!(!filter1.is_attribute_permitted("homeDirectory"));
    }

    #[test]
    fn test_merge_allow_all_with_whitelist() {
        let mut filter1 = AttributeFilter::allow_all();
        let filter2 = AttributeFilter::with_allowed(["cn", "sn"]);

        filter1.merge(&filter2);

        // Should adopt the whitelist
        assert!(filter1.is_whitelist_mode());
        assert!(filter1.is_attribute_permitted("cn"));
        assert!(filter1.is_attribute_permitted("sn"));
    }

    #[test]
    fn test_object_attribute_acl() {
        let acl = ObjectAttributeAcl::new(
            AttributeFilter::with_allowed(["cn", "sn", "mail", "userPassword"]),
            AttributeFilter::with_allowed(["cn", "sn", "mail"]), // Can't write userPassword
        );

        assert!(acl.can_read("cn"));
        assert!(acl.can_read("userPassword"));
        assert!(acl.can_write("cn"));
        assert!(!acl.can_write("userPassword"));
    }

    #[test]
    fn test_add_allowed() {
        let mut filter = AttributeFilter::allow_all();

        // First add switches to whitelist mode
        filter.add_allowed(["cn", "sn"]);
        assert!(filter.is_whitelist_mode());
        assert!(filter.is_attribute_permitted("cn"));
        assert!(!filter.is_attribute_permitted("mail"));

        // Second add extends the whitelist
        filter.add_allowed(["mail"]);
        assert!(filter.is_attribute_permitted("mail"));
    }

    #[test]
    fn test_add_denied() {
        let mut filter = AttributeFilter::allow_all();

        filter.add_denied(["userPassword"]);
        assert!(!filter.is_attribute_permitted("userPassword"));
        assert!(filter.is_attribute_permitted("cn"));
    }
}
