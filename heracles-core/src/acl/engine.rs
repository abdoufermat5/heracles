//! ACL Evaluation Engine.
//!
//! Provides the core UserAcl structure for runtime permission evaluation.
//! Precompiled at login from database rows, cached in Redis.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use super::attributes::{AttributeFilter, ObjectAttributeAcl};
use super::bitmap::PermissionBitmap;

/// A single scoped ACL entry (compiled from an assignment + policy).
///
/// Entries are evaluated in priority order (ascending) against a target DN.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ScopedEntry {
    /// The DN this entry applies to (lowercase for comparison).
    pub dn_lower: String,

    /// Does this apply to the DN and all children (subtree)?
    /// If false, applies only to the exact DN (base).
    pub subtree: bool,

    /// Only applies when target_dn == user_dn.
    /// Used for self-service permissions (edit own profile).
    pub self_only: bool,

    /// Is this a deny entry?
    /// Deny entries subtract permissions instead of adding them.
    pub deny: bool,

    /// Priority (higher = evaluated later).
    /// Deny rules typically have higher priority.
    pub priority: i16,

    /// The permission bitmap from the policy.
    pub permissions: PermissionBitmap,

    /// Attribute-level rules per object type.
    /// Key: object type (e.g., "user", "group")
    /// Value: Read/write attribute filters
    pub attr_acls: HashMap<String, ObjectAttributeAcl>,
}

impl ScopedEntry {
    /// Check if this entry matches the given target DN.
    ///
    /// # Arguments
    ///
    /// * `target_dn_lower` - The target DN (lowercased).
    /// * `user_dn_lower` - The user's own DN (lowercased).
    /// * `is_self` - Whether target_dn == user_dn.
    pub fn matches(&self, target_dn_lower: &str, _user_dn_lower: &str, is_self: bool) -> bool {
        // self_only entries only match when targeting own entry
        if self.self_only && !is_self {
            return false;
        }

        if self.subtree {
            // Subtree: target must be the scope DN or a child of it
            if self.dn_lower.is_empty() {
                // Empty scope DN = global (matches everything)
                return true;
            }
            // Check if target ends with ,<scope_dn> or equals scope_dn
            target_dn_lower == self.dn_lower
                || target_dn_lower.ends_with(&format!(",{}", self.dn_lower))
        } else {
            // Base: exact match only
            target_dn_lower == self.dn_lower
        }
    }
}

/// Result of an ACL check.
#[derive(Clone, Debug)]
pub struct AclVerdict {
    /// Whether the operation is allowed.
    pub allowed: bool,

    /// Attribute filter for the matched scope.
    /// Use this to filter which attributes the user can access.
    pub attr_filter: AttributeFilter,
}

impl Default for AclVerdict {
    fn default() -> Self {
        Self {
            allowed: false,
            attr_filter: AttributeFilter::deny_all(),
        }
    }
}

/// Precompiled ACL for a user session.
///
/// Built once at login from database rows, cached in Redis.
/// All permission checks are O(1) for global rules, O(n) for scoped rules
/// where n is the number of scoped entries (typically < 20).
///
/// # Example
///
/// ```rust,ignore
/// use heracles_core::acl::{UserAcl, PermissionBitmap};
///
/// // Check if user can read users in a specific OU
/// let target = "uid=john,ou=users,dc=example,dc=com";
/// let user_read = PermissionBitmap::from_bit(0); // bit 0 = user:read
///
/// if user_acl.check(target, user_read) {
///     // User has permission
/// }
/// ```
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct UserAcl {
    /// The user's own DN (for self_only checks).
    user_dn: String,

    /// Lowercase version of user DN for comparisons.
    user_dn_lower: String,

    /// Global allow bitmap (from assignments with no scope_dn).
    /// Applied first, before any scoped rules.
    global_allow: PermissionBitmap,

    /// Global deny bitmap.
    /// Applied after global_allow, before scoped rules.
    global_deny: PermissionBitmap,

    /// Global attribute ACLs.
    /// Key: object type (e.g., "user", "group")
    global_attr_acls: HashMap<String, ObjectAttributeAcl>,

    /// Scoped entries, sorted by priority ascending.
    /// Evaluated after global rules for matching target DNs.
    scoped: Vec<ScopedEntry>,
}

impl UserAcl {
    /// Create a new UserAcl.
    ///
    /// Use the `compile` function to build from database rows.
    pub fn new(
        user_dn: String,
        global_allow: PermissionBitmap,
        global_deny: PermissionBitmap,
        global_attr_acls: HashMap<String, ObjectAttributeAcl>,
        mut scoped: Vec<ScopedEntry>,
    ) -> Self {
        // Sort scoped entries by priority (ascending - lower first)
        scoped.sort_by_key(|e| e.priority);

        let user_dn_lower = user_dn.to_ascii_lowercase();

        Self {
            user_dn,
            user_dn_lower,
            global_allow,
            global_deny,
            global_attr_acls,
            scoped,
        }
    }

    /// Create an empty ACL (no permissions).
    pub fn empty(user_dn: String) -> Self {
        Self::new(
            user_dn,
            PermissionBitmap::EMPTY,
            PermissionBitmap::EMPTY,
            HashMap::new(),
            Vec::new(),
        )
    }

    /// Create a superuser ACL (all permissions).
    pub fn superuser(user_dn: String) -> Self {
        Self::new(
            user_dn,
            PermissionBitmap::ALL,
            PermissionBitmap::EMPTY,
            HashMap::new(),
            Vec::new(),
        )
    }

    /// Get the user's DN.
    pub fn user_dn(&self) -> &str {
        &self.user_dn
    }

    /// Fast object-level permission check. Returns bool.
    ///
    /// This is the primary permission check API.
    ///
    /// # Arguments
    ///
    /// * `target_dn` - The DN of the object being accessed.
    /// * `required` - The permissions required (as a bitmap).
    ///
    /// # Example
    ///
    /// ```rust,ignore
    /// let can_read = user_acl.check(
    ///     "uid=john,ou=users,dc=example,dc=com",
    ///     PermissionBitmap::from_bit(0) // user:read
    /// );
    /// ```
    pub fn check(&self, target_dn: &str, required: PermissionBitmap) -> bool {
        self.evaluate(target_dn, required).allowed
    }

    /// Full evaluation: object-level + attribute filter for the matched scope.
    ///
    /// Returns both the allow/deny verdict and the applicable attribute filter.
    /// Use this when you need to filter attributes based on permissions.
    pub fn evaluate(&self, target_dn: &str, required: PermissionBitmap) -> AclVerdict {
        if required.is_empty() {
            // No permissions required = always allowed
            return AclVerdict {
                allowed: true,
                attr_filter: self.resolve_attr_filter(target_dn, ""),
            };
        }

        let target_lower = target_dn.to_ascii_lowercase();
        let is_self = target_lower == self.user_dn_lower;

        // Start with global permissions
        let mut effective = self.global_allow.subtract(self.global_deny);

        // Apply scoped entries in priority order
        for entry in &self.scoped {
            if entry.matches(&target_lower, &self.user_dn_lower, is_self) {
                if entry.deny {
                    effective = effective.subtract(entry.permissions);
                } else {
                    effective = effective.union(entry.permissions);
                }
            }
        }

        // Check if all required permissions are present
        let allowed = effective.has(required);

        AclVerdict {
            allowed,
            attr_filter: self.resolve_attr_filter(target_dn, ""),
        }
    }

    /// Check object-level permission + specific attribute.
    ///
    /// # Arguments
    ///
    /// * `target_dn` - The DN of the object being accessed.
    /// * `required` - The object-level permissions required.
    /// * `object_type` - The type of object (e.g., "user", "group").
    /// * `action` - The action ("read" or "write").
    /// * `attribute` - The specific attribute to check.
    pub fn check_attribute(
        &self,
        target_dn: &str,
        required: PermissionBitmap,
        object_type: &str,
        action: &str,
        attribute: &str,
    ) -> bool {
        let verdict = self.evaluate(target_dn, required);
        if !verdict.allowed {
            return false;
        }

        // Get attribute ACL for this object type
        let attr_filter = self.resolve_attr_filter_for_type(target_dn, object_type, action);
        attr_filter.is_attribute_permitted(attribute)
    }

    /// Filter a list of attributes, returning only the ones this user can access.
    ///
    /// # Arguments
    ///
    /// * `target_dn` - The DN of the object.
    /// * `required` - The base permissions required.
    /// * `object_type` - The type of object.
    /// * `action` - The action ("read" or "write").
    /// * `attributes` - The list of attributes to filter.
    pub fn filter_attributes(
        &self,
        target_dn: &str,
        required: PermissionBitmap,
        object_type: &str,
        action: &str,
        attributes: &[&str],
    ) -> Vec<String> {
        let verdict = self.evaluate(target_dn, required);
        if !verdict.allowed {
            return Vec::new();
        }

        let attr_filter = self.resolve_attr_filter_for_type(target_dn, object_type, action);
        attr_filter
            .filter_attributes(attributes)
            .into_iter()
            .map(|s| s.to_string())
            .collect()
    }

    /// Get the effective permissions for a target DN.
    ///
    /// Returns the permission bitmap after applying all global and scoped rules.
    pub fn effective_permissions(&self, target_dn: &str) -> PermissionBitmap {
        let target_lower = target_dn.to_ascii_lowercase();
        let is_self = target_lower == self.user_dn_lower;

        let mut effective = self.global_allow.subtract(self.global_deny);

        for entry in &self.scoped {
            if entry.matches(&target_lower, &self.user_dn_lower, is_self) {
                if entry.deny {
                    effective = effective.subtract(entry.permissions);
                } else {
                    effective = effective.union(entry.permissions);
                }
            }
        }

        effective
    }

    /// Check if this is a self-access check.
    pub fn is_self(&self, target_dn: &str) -> bool {
        target_dn.to_ascii_lowercase() == self.user_dn_lower
    }

    /// Resolve attribute filter for a target (generic version).
    fn resolve_attr_filter(&self, target_dn: &str, object_type: &str) -> AttributeFilter {
        let target_lower = target_dn.to_ascii_lowercase();
        let is_self = target_lower == self.user_dn_lower;

        // Start with global filter for this object type
        let mut filter = self
            .global_attr_acls
            .get(object_type)
            .map(|acl| acl.read.clone())
            .unwrap_or_else(AttributeFilter::allow_all);

        // Apply scoped entry filters
        for entry in &self.scoped {
            if entry.matches(&target_lower, &self.user_dn_lower, is_self) {
                if let Some(obj_acl) = entry.attr_acls.get(object_type) {
                    if entry.deny {
                        // Deny entry: add denied attributes
                        if let Some(denied) = obj_acl.read.denied().iter().next() {
                            filter.add_denied([denied.as_str()]);
                        }
                    } else {
                        filter.merge(&obj_acl.read);
                    }
                }
            }
        }

        filter
    }

    /// Resolve attribute filter for a specific object type and action.
    fn resolve_attr_filter_for_type(
        &self,
        target_dn: &str,
        object_type: &str,
        action: &str,
    ) -> AttributeFilter {
        let target_lower = target_dn.to_ascii_lowercase();
        let is_self = target_lower == self.user_dn_lower;

        // Start with global filter
        let mut filter = self
            .global_attr_acls
            .get(object_type)
            .map(|acl| {
                if action == "write" {
                    acl.write.clone()
                } else {
                    acl.read.clone()
                }
            })
            .unwrap_or_else(AttributeFilter::allow_all);

        // Apply scoped entry filters
        for entry in &self.scoped {
            if entry.matches(&target_lower, &self.user_dn_lower, is_self) {
                if let Some(obj_acl) = entry.attr_acls.get(object_type) {
                    let entry_filter = if action == "write" {
                        &obj_acl.write
                    } else {
                        &obj_acl.read
                    };

                    if entry.deny {
                        // For deny entries, add their denied attrs to our denied set
                        for attr in entry_filter.denied() {
                            filter.add_denied([attr.as_str()]);
                        }
                    } else {
                        filter.merge(entry_filter);
                    }
                }
            }
        }

        filter
    }

    /// Get all scoped entries (for debugging/inspection).
    pub fn scoped_entries(&self) -> &[ScopedEntry] {
        &self.scoped
    }

    /// Get the global allow bitmap.
    pub fn global_allow(&self) -> PermissionBitmap {
        self.global_allow
    }

    /// Get the global deny bitmap.
    pub fn global_deny(&self) -> PermissionBitmap {
        self.global_deny
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_user_dn() -> String {
        "uid=testuser,ou=users,dc=example,dc=com".to_string()
    }

    #[test]
    fn test_empty_acl_denies_all() {
        let acl = UserAcl::empty(test_user_dn());
        let required = PermissionBitmap::from_bit(0);

        assert!(!acl.check("uid=other,ou=users,dc=example,dc=com", required));
    }

    #[test]
    fn test_superuser_allows_all() {
        let acl = UserAcl::superuser(test_user_dn());
        let required = PermissionBitmap::from_bits(&[0, 1, 2, 50, 100, 127]);

        assert!(acl.check("uid=other,ou=users,dc=example,dc=com", required));
    }

    #[test]
    fn test_global_allow() {
        let acl = UserAcl::new(
            test_user_dn(),
            PermissionBitmap::from_bits(&[0, 1, 2]), // user:read, user:write, user:create
            PermissionBitmap::EMPTY,
            HashMap::new(),
            Vec::new(),
        );

        // Has all required
        assert!(acl.check(
            "uid=other,ou=users,dc=example,dc=com",
            PermissionBitmap::from_bits(&[0, 1])
        ));

        // Missing bit 3
        assert!(!acl.check(
            "uid=other,ou=users,dc=example,dc=com",
            PermissionBitmap::from_bits(&[0, 3])
        ));
    }

    #[test]
    fn test_global_deny() {
        let acl = UserAcl::new(
            test_user_dn(),
            PermissionBitmap::from_bits(&[0, 1, 2]),
            PermissionBitmap::from_bit(1), // Deny bit 1
            HashMap::new(),
            Vec::new(),
        );

        // Bit 1 is denied
        assert!(!acl.check(
            "uid=other,ou=users,dc=example,dc=com",
            PermissionBitmap::from_bit(1)
        ));

        // Bit 0 and 2 still allowed
        assert!(acl.check(
            "uid=other,ou=users,dc=example,dc=com",
            PermissionBitmap::from_bits(&[0, 2])
        ));
    }

    #[test]
    fn test_scoped_entry_subtree() {
        let entry = ScopedEntry {
            dn_lower: "ou=users,dc=example,dc=com".to_string(),
            subtree: true,
            self_only: false,
            deny: false,
            priority: 0,
            permissions: PermissionBitmap::from_bit(5),
            attr_acls: HashMap::new(),
        };

        // Child of scope
        assert!(entry.matches("uid=john,ou=users,dc=example,dc=com", "", false));

        // Exact match
        assert!(entry.matches("ou=users,dc=example,dc=com", "", false));

        // Not in subtree
        assert!(!entry.matches("uid=john,ou=groups,dc=example,dc=com", "", false));
    }

    #[test]
    fn test_scoped_entry_base() {
        let entry = ScopedEntry {
            dn_lower: "uid=john,ou=users,dc=example,dc=com".to_string(),
            subtree: false,
            self_only: false,
            deny: false,
            priority: 0,
            permissions: PermissionBitmap::from_bit(5),
            attr_acls: HashMap::new(),
        };

        // Exact match only
        assert!(entry.matches("uid=john,ou=users,dc=example,dc=com", "", false));

        // Child doesn't match for base scope
        assert!(!entry.matches("ou=users,dc=example,dc=com", "", false));
    }

    #[test]
    fn test_scoped_entry_self_only() {
        let user_dn = "uid=testuser,ou=users,dc=example,dc=com";
        let entry = ScopedEntry {
            dn_lower: "ou=users,dc=example,dc=com".to_string(),
            subtree: true,
            self_only: true,
            deny: false,
            priority: 0,
            permissions: PermissionBitmap::from_bit(5),
            attr_acls: HashMap::new(),
        };

        // Self access
        assert!(entry.matches(
            &user_dn.to_ascii_lowercase(),
            &user_dn.to_ascii_lowercase(),
            true
        ));

        // Not self
        assert!(!entry.matches(
            "uid=other,ou=users,dc=example,dc=com",
            &user_dn.to_ascii_lowercase(),
            false
        ));
    }

    #[test]
    fn test_scoped_allow_extends_global() {
        let acl = UserAcl::new(
            test_user_dn(),
            PermissionBitmap::from_bit(0), // Global: bit 0
            PermissionBitmap::EMPTY,
            HashMap::new(),
            vec![ScopedEntry {
                dn_lower: "ou=special,dc=example,dc=com".to_string(),
                subtree: true,
                self_only: false,
                deny: false,
                priority: 0,
                permissions: PermissionBitmap::from_bit(5), // Scoped: bit 5
                attr_acls: HashMap::new(),
            }],
        );

        // Outside scope: only global (bit 0)
        assert!(acl.check(
            "uid=john,ou=users,dc=example,dc=com",
            PermissionBitmap::from_bit(0)
        ));
        assert!(!acl.check(
            "uid=john,ou=users,dc=example,dc=com",
            PermissionBitmap::from_bit(5)
        ));

        // Inside scope: global + scoped
        assert!(acl.check(
            "uid=john,ou=special,dc=example,dc=com",
            PermissionBitmap::from_bit(0)
        ));
        assert!(acl.check(
            "uid=john,ou=special,dc=example,dc=com",
            PermissionBitmap::from_bit(5)
        ));
    }

    #[test]
    fn test_scoped_deny_overrides_allow() {
        let acl = UserAcl::new(
            test_user_dn(),
            PermissionBitmap::from_bits(&[0, 1, 2]),
            PermissionBitmap::EMPTY,
            HashMap::new(),
            vec![ScopedEntry {
                dn_lower: "ou=restricted,dc=example,dc=com".to_string(),
                subtree: true,
                self_only: false,
                deny: true, // DENY
                priority: 10,
                permissions: PermissionBitmap::from_bit(1), // Deny bit 1
                attr_acls: HashMap::new(),
            }],
        );

        // Outside restricted: all bits available
        assert!(acl.check(
            "uid=john,ou=users,dc=example,dc=com",
            PermissionBitmap::from_bit(1)
        ));

        // Inside restricted: bit 1 denied
        assert!(!acl.check(
            "uid=john,ou=restricted,dc=example,dc=com",
            PermissionBitmap::from_bit(1)
        ));

        // Other bits still allowed
        assert!(acl.check(
            "uid=john,ou=restricted,dc=example,dc=com",
            PermissionBitmap::from_bits(&[0, 2])
        ));
    }

    #[test]
    fn test_priority_ordering() {
        // Lower priority allow, higher priority deny
        let acl = UserAcl::new(
            test_user_dn(),
            PermissionBitmap::EMPTY,
            PermissionBitmap::EMPTY,
            HashMap::new(),
            vec![
                ScopedEntry {
                    dn_lower: "ou=users,dc=example,dc=com".to_string(),
                    subtree: true,
                    self_only: false,
                    deny: false,
                    priority: 0, // Low priority - allow
                    permissions: PermissionBitmap::from_bit(5),
                    attr_acls: HashMap::new(),
                },
                ScopedEntry {
                    dn_lower: "ou=users,dc=example,dc=com".to_string(),
                    subtree: true,
                    self_only: false,
                    deny: true,
                    priority: 10, // High priority - deny wins
                    permissions: PermissionBitmap::from_bit(5),
                    attr_acls: HashMap::new(),
                },
            ],
        );

        // Deny wins because it has higher priority
        assert!(!acl.check(
            "uid=john,ou=users,dc=example,dc=com",
            PermissionBitmap::from_bit(5)
        ));
    }

    #[test]
    fn test_self_service() {
        let user_dn = test_user_dn();
        let acl = UserAcl::new(
            user_dn.clone(),
            PermissionBitmap::EMPTY, // No global permissions
            PermissionBitmap::EMPTY,
            HashMap::new(),
            vec![ScopedEntry {
                dn_lower: "ou=users,dc=example,dc=com".to_string(),
                subtree: true,
                self_only: true, // Self-service only
                deny: false,
                priority: 0,
                permissions: PermissionBitmap::from_bit(1), // Can write self
                attr_acls: HashMap::new(),
            }],
        );

        // Can write own entry
        assert!(acl.check(&user_dn, PermissionBitmap::from_bit(1)));

        // Cannot write other entries
        assert!(!acl.check(
            "uid=other,ou=users,dc=example,dc=com",
            PermissionBitmap::from_bit(1)
        ));
    }

    #[test]
    fn test_effective_permissions() {
        let acl = UserAcl::new(
            test_user_dn(),
            PermissionBitmap::from_bits(&[0, 1, 2]),
            PermissionBitmap::from_bit(2),
            HashMap::new(),
            vec![ScopedEntry {
                dn_lower: "ou=special,dc=example,dc=com".to_string(),
                subtree: true,
                self_only: false,
                deny: false,
                priority: 0,
                permissions: PermissionBitmap::from_bit(5),
                attr_acls: HashMap::new(),
            }],
        );

        // Outside special: bits 0, 1 (2 is denied)
        let eff1 = acl.effective_permissions("uid=john,ou=users,dc=example,dc=com");
        assert!(eff1.has_bit(0));
        assert!(eff1.has_bit(1));
        assert!(!eff1.has_bit(2));
        assert!(!eff1.has_bit(5));

        // Inside special: bits 0, 1, 5 (2 still denied)
        let eff2 = acl.effective_permissions("uid=john,ou=special,dc=example,dc=com");
        assert!(eff2.has_bit(0));
        assert!(eff2.has_bit(1));
        assert!(!eff2.has_bit(2));
        assert!(eff2.has_bit(5));
    }

    #[test]
    fn test_serde_roundtrip() {
        let acl = UserAcl::new(
            test_user_dn(),
            PermissionBitmap::from_bits(&[0, 1, 64, 127]),
            PermissionBitmap::from_bit(5),
            HashMap::new(),
            vec![ScopedEntry {
                dn_lower: "ou=test,dc=example,dc=com".to_string(),
                subtree: true,
                self_only: false,
                deny: false,
                priority: 10,
                permissions: PermissionBitmap::from_bit(10),
                attr_acls: HashMap::new(),
            }],
        );

        let json = serde_json::to_string(&acl).expect("serialize");
        let restored: UserAcl = serde_json::from_str(&json).expect("deserialize");

        assert_eq!(acl.user_dn, restored.user_dn);
        assert_eq!(acl.global_allow, restored.global_allow);
        assert_eq!(acl.global_deny, restored.global_deny);
        assert_eq!(acl.scoped.len(), restored.scoped.len());
    }
}
