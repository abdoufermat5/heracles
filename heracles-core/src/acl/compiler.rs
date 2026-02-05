//! ACL Compiler - Build UserAcl from database rows.
//!
//! Compiles raw database query results into an optimized UserAcl structure
//! for runtime permission evaluation.

use std::collections::{HashMap, HashSet};

use super::attributes::{AttributeFilter, ObjectAttributeAcl};
use super::bitmap::PermissionBitmap;
use super::engine::{ScopedEntry, UserAcl};

/// Raw row from the SQL query (one per matching assignment+policy join).
///
/// This represents the flattened result of joining:
/// - `acl_assignments`
/// - `acl_policies`
/// - `acl_policy_attr_rules` (expanded)
///
/// The Python layer fetches these rows and passes them to the Rust compiler.
#[derive(Clone, Debug)]
pub struct AclRow {
    /// Policy name (for debugging/logging).
    pub policy_name: String,

    /// Lower 64 bits of the permission bitmap.
    pub perm_low: i64,

    /// Upper 64 bits of the permission bitmap.
    pub perm_high: i64,

    /// Scope DN for this assignment (empty string = global).
    pub scope_dn: String,

    /// Scope type: "base" or "subtree".
    pub scope_type: String,

    /// Only applies when target_dn == user_dn.
    pub self_only: bool,

    /// Is this a deny assignment?
    pub deny: bool,

    /// Priority (higher = evaluated later).
    pub priority: i16,

    /// Attribute-level rules for this policy.
    pub attr_rules: Vec<AttrRuleRow>,
}

/// A single attribute-level rule from a policy.
///
/// Represents one row from `acl_policy_attr_rules` with attribute groups
/// expanded to their actual attribute names.
#[derive(Clone, Debug)]
pub struct AttrRuleRow {
    /// Object type this rule applies to (e.g., "user", "group").
    pub object_type: String,

    /// Action: "read" or "write".
    pub action: String,

    /// Rule type: "allow" or "deny".
    pub rule_type: String,

    /// Actual LDAP attribute names (expanded from group names).
    pub attributes: Vec<String>,
}

/// Compile raw database rows into a UserAcl.
///
/// This is called once at login by the Python ACL service.
/// The resulting UserAcl is cached in Redis.
///
/// # Arguments
///
/// * `user_dn` - The DN of the user being authenticated.
/// * `rows` - All ACL rows applicable to this user (from assignments + policies).
///
/// # Algorithm
///
/// 1. Separate global (scope_dn == "") vs scoped entries
/// 2. Build PermissionBitmaps from perm_low/perm_high
/// 3. Build AttributeFilters from attr_rules
/// 4. Sort scoped entries by priority ascending
/// 5. Return optimized UserAcl
pub fn compile(user_dn: &str, rows: Vec<AclRow>) -> UserAcl {
    let mut global_allow = PermissionBitmap::EMPTY;
    let mut global_deny = PermissionBitmap::EMPTY;
    let mut global_attr_acls: HashMap<String, ObjectAttributeAcl> = HashMap::new();
    let mut scoped_entries: Vec<ScopedEntry> = Vec::new();

    for row in rows {
        let permissions = PermissionBitmap::from_halves(row.perm_low, row.perm_high);
        let attr_acls = build_attr_acls(&row.attr_rules);
        let is_subtree = row.scope_type.eq_ignore_ascii_case("subtree");

        if row.scope_dn.is_empty() && !row.self_only {
            // Global assignment
            if row.deny {
                global_deny = global_deny.union(permissions);
                // Merge denied attributes into global
                merge_global_attr_acls_deny(&mut global_attr_acls, &attr_acls);
            } else {
                global_allow = global_allow.union(permissions);
                // Merge allowed attributes into global
                merge_global_attr_acls_allow(&mut global_attr_acls, &attr_acls);
            }
        } else {
            // Scoped or self_only assignment
            scoped_entries.push(ScopedEntry {
                dn_lower: row.scope_dn.to_ascii_lowercase(),
                subtree: is_subtree,
                self_only: row.self_only,
                deny: row.deny,
                priority: row.priority,
                permissions,
                attr_acls,
            });
        }
    }

    UserAcl::new(
        user_dn.to_string(),
        global_allow,
        global_deny,
        global_attr_acls,
        scoped_entries,
    )
}

/// Build attribute ACLs from attr_rules.
fn build_attr_acls(rules: &[AttrRuleRow]) -> HashMap<String, ObjectAttributeAcl> {
    // Group rules by (object_type, action)
    let mut grouped: HashMap<(String, String), Vec<&AttrRuleRow>> = HashMap::new();

    for rule in rules {
        let key = (rule.object_type.clone(), rule.action.clone());
        grouped.entry(key).or_default().push(rule);
    }

    // Build ObjectAttributeAcl per object_type
    let mut result: HashMap<String, ObjectAttributeAcl> = HashMap::new();

    for ((object_type, action), rules) in grouped {
        let filter = build_attr_filter(&rules);

        let obj_acl = result
            .entry(object_type)
            .or_insert_with(ObjectAttributeAcl::allow_all);

        if action == "read" {
            obj_acl.read = filter;
        } else if action == "write" {
            obj_acl.write = filter;
        }
    }

    result
}

/// Build an AttributeFilter from a set of rules for one (object_type, action).
fn build_attr_filter(rules: &[&AttrRuleRow]) -> AttributeFilter {
    let mut allowed: Option<HashSet<String>> = None;
    let mut denied: HashSet<String> = HashSet::new();

    for rule in rules {
        if rule.rule_type == "allow" {
            // Collect all allowed attributes
            let attrs: HashSet<String> = rule
                .attributes
                .iter()
                .map(|s| s.to_ascii_lowercase())
                .collect();

            match &mut allowed {
                Some(existing) => {
                    // Union with existing allowed
                    existing.extend(attrs);
                }
                None => {
                    allowed = Some(attrs);
                }
            }
        } else if rule.rule_type == "deny" {
            // Add to denied set
            denied.extend(rule.attributes.iter().map(|s| s.to_ascii_lowercase()));
        }
    }

    AttributeFilter::new(allowed, denied)
}

/// Merge attr_acls into global allow (for allow assignments).
fn merge_global_attr_acls_allow(
    global: &mut HashMap<String, ObjectAttributeAcl>,
    new: &HashMap<String, ObjectAttributeAcl>,
) {
    for (obj_type, new_acl) in new {
        match global.get_mut(obj_type) {
            Some(existing) => {
                existing.merge(new_acl);
            }
            None => {
                global.insert(obj_type.clone(), new_acl.clone());
            }
        }
    }
}

/// Merge attr_acls into global deny (for deny assignments).
fn merge_global_attr_acls_deny(
    global: &mut HashMap<String, ObjectAttributeAcl>,
    deny_acls: &HashMap<String, ObjectAttributeAcl>,
) {
    for (obj_type, deny_acl) in deny_acls {
        let global_acl = global
            .entry(obj_type.clone())
            .or_insert_with(ObjectAttributeAcl::allow_all);

        // Add denied attributes from the deny policy
        for attr in deny_acl.read.denied() {
            global_acl.read.add_denied([attr.as_str()]);
        }
        for attr in deny_acl.write.denied() {
            global_acl.write.add_denied([attr.as_str()]);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_user() -> &'static str {
        "uid=testuser,ou=users,dc=example,dc=com"
    }

    #[test]
    fn test_compile_empty() {
        let acl = compile(test_user(), Vec::new());

        assert_eq!(acl.user_dn(), test_user());
        assert!(acl.global_allow().is_empty());
        assert!(acl.global_deny().is_empty());
        assert!(acl.scoped_entries().is_empty());
    }

    #[test]
    fn test_compile_global_allow() {
        let rows = vec![AclRow {
            policy_name: "Basic User".to_string(),
            perm_low: 0b111, // bits 0, 1, 2
            perm_high: 0,
            scope_dn: "".to_string(), // Global
            scope_type: "subtree".to_string(),
            self_only: false,
            deny: false,
            priority: 0,
            attr_rules: vec![],
        }];

        let acl = compile(test_user(), rows);

        assert!(acl.global_allow().has_bit(0));
        assert!(acl.global_allow().has_bit(1));
        assert!(acl.global_allow().has_bit(2));
        assert!(!acl.global_allow().has_bit(3));
    }

    #[test]
    fn test_compile_global_deny() {
        let rows = vec![
            AclRow {
                policy_name: "Full Access".to_string(),
                perm_low: 0b1111, // bits 0-3
                perm_high: 0,
                scope_dn: "".to_string(),
                scope_type: "subtree".to_string(),
                self_only: false,
                deny: false,
                priority: 0,
                attr_rules: vec![],
            },
            AclRow {
                policy_name: "Deny Delete".to_string(),
                perm_low: 0b1000, // bit 3
                perm_high: 0,
                scope_dn: "".to_string(),
                scope_type: "subtree".to_string(),
                self_only: false,
                deny: true, // DENY
                priority: 10,
                attr_rules: vec![],
            },
        ];

        let acl = compile(test_user(), rows);

        // Bit 3 should be denied
        assert!(acl.global_deny().has_bit(3));
        assert!(acl.global_allow().has_bit(3)); // Still in allow...
        // But the engine subtracts deny from allow
    }

    #[test]
    fn test_compile_scoped_entries() {
        let rows = vec![
            AclRow {
                policy_name: "Global".to_string(),
                perm_low: 0b1,
                perm_high: 0,
                scope_dn: "".to_string(),
                scope_type: "subtree".to_string(),
                self_only: false,
                deny: false,
                priority: 0,
                attr_rules: vec![],
            },
            AclRow {
                policy_name: "Special OU".to_string(),
                perm_low: 0b10,
                perm_high: 0,
                scope_dn: "ou=special,dc=example,dc=com".to_string(),
                scope_type: "subtree".to_string(),
                self_only: false,
                deny: false,
                priority: 5,
                attr_rules: vec![],
            },
        ];

        let acl = compile(test_user(), rows);

        assert_eq!(acl.scoped_entries().len(), 1);
        assert_eq!(
            acl.scoped_entries()[0].dn_lower,
            "ou=special,dc=example,dc=com"
        );
        assert!(acl.scoped_entries()[0].subtree);
    }

    #[test]
    fn test_compile_self_only_creates_scoped() {
        let rows = vec![AclRow {
            policy_name: "Self Service".to_string(),
            perm_low: 0b10,
            perm_high: 0,
            scope_dn: "".to_string(), // Global scope...
            scope_type: "subtree".to_string(),
            self_only: true, // ...but self_only
            deny: false,
            priority: 0,
            attr_rules: vec![],
        }];

        let acl = compile(test_user(), rows);

        // self_only goes to scoped, not global
        assert!(acl.global_allow().is_empty());
        assert_eq!(acl.scoped_entries().len(), 1);
        assert!(acl.scoped_entries()[0].self_only);
    }

    #[test]
    fn test_compile_with_attr_rules() {
        let rows = vec![AclRow {
            policy_name: "Limited".to_string(),
            perm_low: 0b11,
            perm_high: 0,
            scope_dn: "".to_string(),
            scope_type: "subtree".to_string(),
            self_only: false,
            deny: false,
            priority: 0,
            attr_rules: vec![
                AttrRuleRow {
                    object_type: "user".to_string(),
                    action: "read".to_string(),
                    rule_type: "allow".to_string(),
                    attributes: vec!["cn".to_string(), "sn".to_string(), "mail".to_string()],
                },
                AttrRuleRow {
                    object_type: "user".to_string(),
                    action: "write".to_string(),
                    rule_type: "allow".to_string(),
                    attributes: vec!["mail".to_string(), "telephoneNumber".to_string()],
                },
                AttrRuleRow {
                    object_type: "user".to_string(),
                    action: "read".to_string(),
                    rule_type: "deny".to_string(),
                    attributes: vec!["userPassword".to_string()],
                },
            ],
        }];

        let acl = compile(test_user(), rows);

        // Use the check_attribute method
        assert!(acl.check_attribute(
            "uid=other,ou=users,dc=example,dc=com",
            PermissionBitmap::from_bit(0),
            "user",
            "read",
            "cn"
        ));

        // userPassword should be denied
        assert!(!acl.check_attribute(
            "uid=other,ou=users,dc=example,dc=com",
            PermissionBitmap::from_bit(0),
            "user",
            "read",
            "userPassword"
        ));
    }

    #[test]
    fn test_compile_high_bits() {
        let rows = vec![AclRow {
            policy_name: "High Bits".to_string(),
            perm_low: 0,
            perm_high: 0b11, // bits 64, 65
            scope_dn: "".to_string(),
            scope_type: "subtree".to_string(),
            self_only: false,
            deny: false,
            priority: 0,
            attr_rules: vec![],
        }];

        let acl = compile(test_user(), rows);

        assert!(acl.global_allow().has_bit(64));
        assert!(acl.global_allow().has_bit(65));
        assert!(!acl.global_allow().has_bit(0));
    }

    #[test]
    fn test_priority_ordering_in_compiled() {
        let rows = vec![
            AclRow {
                policy_name: "High Priority".to_string(),
                perm_low: 0b1,
                perm_high: 0,
                scope_dn: "ou=test,dc=example,dc=com".to_string(),
                scope_type: "subtree".to_string(),
                self_only: false,
                deny: false,
                priority: 100,
                attr_rules: vec![],
            },
            AclRow {
                policy_name: "Low Priority".to_string(),
                perm_low: 0b10,
                perm_high: 0,
                scope_dn: "ou=test,dc=example,dc=com".to_string(),
                scope_type: "subtree".to_string(),
                self_only: false,
                deny: false,
                priority: 1,
                attr_rules: vec![],
            },
        ];

        let acl = compile(test_user(), rows);

        // Should be sorted by priority ascending
        assert_eq!(acl.scoped_entries().len(), 2);
        assert_eq!(acl.scoped_entries()[0].priority, 1);
        assert_eq!(acl.scoped_entries()[1].priority, 100);
    }
}
