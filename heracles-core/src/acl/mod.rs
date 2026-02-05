//! # ACL - Access Control List Engine
//!
//! High-performance ACL system using u128 bitmaps for permission evaluation.
//!
//! This module provides:
//! - `PermissionBitmap`: u128 bitmap for fast permission checks
//! - `AttributeFilter`: Group-based attribute-level access control
//! - `UserAcl`: Precompiled per-user ACL for runtime evaluation
//! - `compile`: Compile raw database rows into UserAcl
//!
//! ## Architecture
//!
//! Two-layer ACL system:
//! 1. **Object-level** (bitmap): "CAN this user do X on object type Y?" - O(1)
//! 2. **Attribute-level** (groups): "WHICH fields of Y can they touch?" - O(1)
//!
//! ## Example
//!
//! ```rust,ignore
//! use heracles_core::acl::{PermissionBitmap, UserAcl};
//!
//! // Create required permissions bitmap
//! let required = PermissionBitmap::from_bit(0)  // user:read
//!     .union(PermissionBitmap::from_bit(1));    // user:write
//!
//! // Check if user has permissions
//! let allowed = user_acl.check("uid=john,ou=users,dc=example,dc=com", required);
//! ```

mod bitmap;
mod attributes;
mod engine;
mod compiler;

pub use bitmap::PermissionBitmap;
pub use attributes::{AttributeFilter, ObjectAttributeAcl};
pub use engine::{UserAcl, AclVerdict, ScopedEntry};
pub use compiler::{AclRow, AttrRuleRow, compile};
