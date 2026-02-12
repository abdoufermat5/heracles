//! LDAP filter building utilities.

use crate::ldap::dn::escape_filter_value;
use std::fmt;

/// Represents an LDAP filter.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum LdapFilter {
    /// Equality match: (attr=value)
    Equals(String, String),
    /// Presence check: (attr=*)
    Present(String),
    /// Substring match: (attr=*value*)
    Substring(String, Option<String>, Vec<String>, Option<String>),
    /// Greater than or equal: (attr>=value)
    GreaterOrEqual(String, String),
    /// Less than or equal: (attr<=value)
    LessOrEqual(String, String),
    /// Approximate match: (attr~=value)
    Approx(String, String),
    /// Negation: (!(filter))
    Not(Box<LdapFilter>),
    /// Conjunction: (&(filter1)(filter2)...)
    And(Vec<LdapFilter>),
    /// Disjunction: (|(filter1)(filter2)...)
    Or(Vec<LdapFilter>),
    /// Raw filter string (use with caution - should be pre-escaped)
    Raw(String),
}

impl LdapFilter {
    /// Creates an equality filter: (attr=value)
    pub fn eq(attr: impl Into<String>, value: impl Into<String>) -> Self {
        Self::Equals(attr.into(), value.into())
    }

    /// Creates a presence filter: (attr=*)
    pub fn present(attr: impl Into<String>) -> Self {
        Self::Present(attr.into())
    }

    /// Creates a substring filter: (attr=*value*)
    pub fn contains(attr: impl Into<String>, value: impl Into<String>) -> Self {
        Self::Substring(attr.into(), None, vec![value.into()], None)
    }

    /// Creates a starts-with filter: (attr=value*)
    pub fn starts_with(attr: impl Into<String>, value: impl Into<String>) -> Self {
        Self::Substring(attr.into(), Some(value.into()), vec![], None)
    }

    /// Creates an ends-with filter: (attr=*value)
    pub fn ends_with(attr: impl Into<String>, value: impl Into<String>) -> Self {
        Self::Substring(attr.into(), None, vec![], Some(value.into()))
    }

    /// Creates a greater-or-equal filter: (attr>=value)
    pub fn gte(attr: impl Into<String>, value: impl Into<String>) -> Self {
        Self::GreaterOrEqual(attr.into(), value.into())
    }

    /// Creates a less-or-equal filter: (attr<=value)
    pub fn lte(attr: impl Into<String>, value: impl Into<String>) -> Self {
        Self::LessOrEqual(attr.into(), value.into())
    }

    /// Creates an approximate match filter: (attr~=value)
    pub fn approx(attr: impl Into<String>, value: impl Into<String>) -> Self {
        Self::Approx(attr.into(), value.into())
    }

    /// Creates a negation: (!(filter))
    pub fn not(filter: LdapFilter) -> Self {
        Self::Not(Box::new(filter))
    }

    /// Creates a conjunction: (&(filter1)(filter2)...)
    pub fn and(filters: Vec<LdapFilter>) -> Self {
        Self::And(filters)
    }

    /// Creates a disjunction: (|(filter1)(filter2)...)
    pub fn or(filters: Vec<LdapFilter>) -> Self {
        Self::Or(filters)
    }

    /// Creates a raw filter (should be already escaped).
    pub fn raw(filter: impl Into<String>) -> Self {
        Self::Raw(filter.into())
    }

    /// Returns the filter as a properly escaped string.
    pub fn to_string_escaped(&self) -> String {
        self.to_string()
    }
}

impl fmt::Display for LdapFilter {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            LdapFilter::Equals(attr, value) => {
                write!(f, "({}={})", attr, escape_filter_value(value))
            }
            LdapFilter::Present(attr) => write!(f, "({}=*)", attr),
            LdapFilter::Substring(attr, initial, any, final_) => {
                write!(f, "({}=", attr)?;
                if let Some(init) = initial {
                    write!(f, "{}", escape_filter_value(init))?;
                }
                write!(f, "*")?;
                for part in any {
                    write!(f, "{}*", escape_filter_value(part))?;
                }
                if let Some(fin) = final_ {
                    write!(f, "{}", escape_filter_value(fin))?;
                }
                write!(f, ")")
            }
            LdapFilter::GreaterOrEqual(attr, value) => {
                write!(f, "({}>={})", attr, escape_filter_value(value))
            }
            LdapFilter::LessOrEqual(attr, value) => {
                write!(f, "({}<={})", attr, escape_filter_value(value))
            }
            LdapFilter::Approx(attr, value) => {
                write!(f, "({}~={})", attr, escape_filter_value(value))
            }
            LdapFilter::Not(inner) => write!(f, "(!{})", inner),
            LdapFilter::And(filters) => {
                write!(f, "(&")?;
                for filter in filters {
                    write!(f, "{}", filter)?;
                }
                write!(f, ")")
            }
            LdapFilter::Or(filters) => {
                write!(f, "(|")?;
                for filter in filters {
                    write!(f, "{}", filter)?;
                }
                write!(f, ")")
            }
            LdapFilter::Raw(s) => write!(f, "{}", s),
        }
    }
}

/// Builder for constructing LDAP filters.
#[derive(Debug, Default)]
pub struct FilterBuilder {
    filters: Vec<LdapFilter>,
}

impl FilterBuilder {
    /// Creates a new filter builder.
    pub fn new() -> Self {
        Self::default()
    }

    /// Adds an equality filter.
    pub fn eq(mut self, attr: impl Into<String>, value: impl Into<String>) -> Self {
        self.filters.push(LdapFilter::eq(attr, value));
        self
    }

    /// Adds a presence filter.
    pub fn present(mut self, attr: impl Into<String>) -> Self {
        self.filters.push(LdapFilter::present(attr));
        self
    }

    /// Adds a contains (substring) filter.
    pub fn contains(mut self, attr: impl Into<String>, value: impl Into<String>) -> Self {
        self.filters.push(LdapFilter::contains(attr, value));
        self
    }

    /// Adds a starts-with filter.
    pub fn starts_with(mut self, attr: impl Into<String>, value: impl Into<String>) -> Self {
        self.filters.push(LdapFilter::starts_with(attr, value));
        self
    }

    /// Adds an ends-with filter.
    pub fn ends_with(mut self, attr: impl Into<String>, value: impl Into<String>) -> Self {
        self.filters.push(LdapFilter::ends_with(attr, value));
        self
    }

    /// Adds an objectClass filter.
    pub fn object_class(mut self, class: impl Into<String>) -> Self {
        self.filters.push(LdapFilter::eq("objectClass", class));
        self
    }

    /// Adds a nested filter.
    pub fn filter(mut self, filter: LdapFilter) -> Self {
        self.filters.push(filter);
        self
    }

    /// Builds an AND filter from all added filters.
    pub fn build_and(self) -> LdapFilter {
        if self.filters.len() == 1 {
            self.filters.into_iter().next().unwrap()
        } else {
            LdapFilter::and(self.filters)
        }
    }

    /// Builds an OR filter from all added filters.
    pub fn build_or(self) -> LdapFilter {
        if self.filters.len() == 1 {
            self.filters.into_iter().next().unwrap()
        } else {
            LdapFilter::or(self.filters)
        }
    }
}

/// Common LDAP filter patterns.
pub mod patterns {
    use super::*;

    /// Filter for standard LDAP users.
    pub fn hrc_user() -> LdapFilter {
        FilterBuilder::new()
            .object_class("inetOrgPerson")
            .object_class("hrcAcl")
            .build_and()
    }

    /// Filter for POSIX users.
    pub fn posix_user() -> LdapFilter {
        FilterBuilder::new()
            .object_class("posixAccount")
            .build_and()
    }

    /// Filter for groups.
    pub fn posix_group() -> LdapFilter {
        LdapFilter::eq("objectClass", "posixGroup")
    }

    /// Filter for organizational units.
    pub fn organizational_unit() -> LdapFilter {
        LdapFilter::eq("objectClass", "organizationalUnit")
    }

    /// Filter to find user by uid.
    pub fn user_by_uid(uid: &str) -> LdapFilter {
        FilterBuilder::new()
            .object_class("inetOrgPerson")
            .eq("uid", uid)
            .build_and()
    }

    /// Filter to find user by mail.
    pub fn user_by_mail(mail: &str) -> LdapFilter {
        FilterBuilder::new()
            .object_class("inetOrgPerson")
            .eq("mail", mail)
            .build_and()
    }

    /// Filter for systems/servers.
    pub fn system() -> LdapFilter {
        LdapFilter::or(vec![
            LdapFilter::eq("objectClass", "hrcServer"),
            LdapFilter::eq("objectClass", "hrcWorkstation"),
            LdapFilter::eq("objectClass", "hrcTerminal"),
            LdapFilter::eq("objectClass", "hrcPrinter"),
            LdapFilter::eq("objectClass", "hrcPhone"),
            LdapFilter::eq("objectClass", "hrcMobilePhone"),
        ])
    }

    /// Filter for DNS zones.
    pub fn dns_zone() -> LdapFilter {
        LdapFilter::eq("objectClass", "dNSZone")
    }

    /// Filter for DHCP subnets.
    pub fn dhcp_subnet() -> LdapFilter {
        LdapFilter::eq("objectClass", "dhcpSubnet")
    }

    /// Filter for sudo rules.
    pub fn sudo_rule() -> LdapFilter {
        LdapFilter::eq("objectClass", "sudoRole")
    }

    /// Filter for SSH public keys.
    pub fn user_with_ssh_key() -> LdapFilter {
        FilterBuilder::new()
            .object_class("ldapPublicKey")
            .present("sshPublicKey")
            .build_and()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_equality_filter() {
        let filter = LdapFilter::eq("uid", "testuser");
        assert_eq!(filter.to_string(), "(uid=testuser)");
    }

    #[test]
    fn test_equality_filter_escape() {
        let filter = LdapFilter::eq("cn", "Test (User)");
        assert_eq!(filter.to_string(), "(cn=Test \\28User\\29)");
    }

    #[test]
    fn test_presence_filter() {
        let filter = LdapFilter::present("mail");
        assert_eq!(filter.to_string(), "(mail=*)");
    }

    #[test]
    fn test_substring_contains() {
        let filter = LdapFilter::contains("cn", "test");
        assert_eq!(filter.to_string(), "(cn=*test*)");
    }

    #[test]
    fn test_substring_starts_with() {
        let filter = LdapFilter::starts_with("cn", "test");
        assert_eq!(filter.to_string(), "(cn=test*)");
    }

    #[test]
    fn test_substring_ends_with() {
        let filter = LdapFilter::ends_with("mail", "@example.com");
        assert_eq!(filter.to_string(), "(mail=*@example.com)");
    }

    #[test]
    fn test_and_filter() {
        let filter = LdapFilter::and(vec![
            LdapFilter::eq("objectClass", "inetOrgPerson"),
            LdapFilter::eq("uid", "test"),
        ]);
        assert_eq!(
            filter.to_string(),
            "(&(objectClass=inetOrgPerson)(uid=test))"
        );
    }

    #[test]
    fn test_or_filter() {
        let filter = LdapFilter::or(vec![
            LdapFilter::eq("uid", "user1"),
            LdapFilter::eq("uid", "user2"),
        ]);
        assert_eq!(filter.to_string(), "(|(uid=user1)(uid=user2))");
    }

    #[test]
    fn test_not_filter() {
        let filter = LdapFilter::not(LdapFilter::eq("disabled", "true"));
        assert_eq!(filter.to_string(), "(!(disabled=true))");
    }

    #[test]
    fn test_complex_filter() {
        let filter = LdapFilter::and(vec![
            LdapFilter::eq("objectClass", "inetOrgPerson"),
            LdapFilter::or(vec![
                LdapFilter::eq("uid", "admin"),
                LdapFilter::starts_with("cn", "Admin"),
            ]),
            LdapFilter::not(LdapFilter::eq("accountLocked", "true")),
        ]);
        assert_eq!(
            filter.to_string(),
            "(&(objectClass=inetOrgPerson)(|(uid=admin)(cn=Admin*))(!(accountLocked=true)))"
        );
    }

    #[test]
    fn test_filter_builder() {
        let filter = FilterBuilder::new()
            .object_class("inetOrgPerson")
            .eq("uid", "testuser")
            .present("mail")
            .build_and();

        assert_eq!(
            filter.to_string(),
            "(&(objectClass=inetOrgPerson)(uid=testuser)(mail=*))"
        );
    }

    #[test]
    fn test_pattern_hrc_user() {
        let filter = patterns::hrc_user();
        assert!(filter.to_string().contains("inetOrgPerson"));
        assert!(filter.to_string().contains("hrcAcl"));
    }

    #[test]
    fn test_pattern_user_by_uid() {
        let filter = patterns::user_by_uid("john.doe");
        assert_eq!(
            filter.to_string(),
            "(&(objectClass=inetOrgPerson)(uid=john.doe))"
        );
    }

    #[test]
    fn test_greater_or_equal() {
        let filter = LdapFilter::gte("uidNumber", "1000");
        assert_eq!(filter.to_string(), "(uidNumber>=1000)");
    }

    #[test]
    fn test_less_or_equal() {
        let filter = LdapFilter::lte("uidNumber", "65000");
        assert_eq!(filter.to_string(), "(uidNumber<=65000)");
    }
}
