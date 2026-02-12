//! Permission Bitmap using u128 for fast permission checks.
//!
//! Supports up to 128 distinct permissions encoded as bit positions.
//! Operations are O(1) CPU instructions (AND, OR, XOR).

use serde::{Deserialize, Serialize};
use std::fmt;

/// A set of permissions encoded as a u128 bitmap.
///
/// Supports up to 128 permissions. Each permission is assigned a stable
/// bit position by PostgreSQL on first sync. Bit positions never change
/// to ensure bitmap stability across restarts.
///
/// # Example
///
/// ```rust
/// use heracles_core::acl::PermissionBitmap;
///
/// // Create from individual bits
/// let user_read = PermissionBitmap::from_bit(0);
/// let user_write = PermissionBitmap::from_bit(1);
///
/// // Combine permissions
/// let required = user_read.union(user_write);
///
/// // Check if user has all required permissions
/// let user_perms = PermissionBitmap::from_bit(0)
///     .union(PermissionBitmap::from_bit(1))
///     .union(PermissionBitmap::from_bit(2));
/// assert!(user_perms.has(required));
/// ```
#[derive(Clone, Copy, Default, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct PermissionBitmap {
    bits: u128,
}

impl PermissionBitmap {
    /// Empty bitmap (no permissions).
    pub const EMPTY: Self = Self { bits: 0 };

    /// Full bitmap (all 128 permissions set).
    pub const ALL: Self = Self { bits: u128::MAX };

    /// Create a new empty bitmap.
    #[inline]
    pub const fn new() -> Self {
        Self { bits: 0 }
    }

    /// Create a bitmap with a single bit set at the given position.
    ///
    /// # Panics
    ///
    /// Panics if `pos >= 128`.
    ///
    /// # Example
    ///
    /// ```rust
    /// use heracles_core::acl::PermissionBitmap;
    ///
    /// let perm = PermissionBitmap::from_bit(5);
    /// assert!(perm.has(PermissionBitmap::from_bit(5)));
    /// assert!(!perm.has(PermissionBitmap::from_bit(6)));
    /// ```
    #[inline]
    pub const fn from_bit(pos: u8) -> Self {
        assert!(pos < 128, "bit position must be 0-127");
        Self { bits: 1u128 << pos }
    }

    /// Create a bitmap from a raw u128 value.
    #[inline]
    pub const fn from_raw(bits: u128) -> Self {
        Self { bits }
    }

    /// Reconstruct from two i64 halves (PostgreSQL BIGINT columns).
    ///
    /// PostgreSQL stores the bitmap split into two BIGINT columns:
    /// - `perm_low`: bits 0-63
    /// - `perm_high`: bits 64-127
    ///
    /// # Example
    ///
    /// ```rust
    /// use heracles_core::acl::PermissionBitmap;
    ///
    /// let perm = PermissionBitmap::from_bit(65);
    /// let (low, high) = perm.to_halves();
    /// let reconstructed = PermissionBitmap::from_halves(low, high);
    /// assert_eq!(perm, reconstructed);
    /// ```
    #[inline]
    pub const fn from_halves(low: i64, high: i64) -> Self {
        let lo = low as u64 as u128;
        let hi = (high as u64 as u128) << 64;
        Self { bits: lo | hi }
    }

    /// Split into two i64 halves for PostgreSQL storage.
    ///
    /// Returns `(perm_low, perm_high)` suitable for BIGINT columns.
    #[inline]
    pub const fn to_halves(self) -> (i64, i64) {
        let lo = self.bits as u64 as i64;
        let hi = (self.bits >> 64) as u64 as i64;
        (lo, hi)
    }

    /// Get the raw u128 value.
    #[inline]
    pub const fn as_raw(self) -> u128 {
        self.bits
    }

    /// Check if ALL bits in `required` are set in this bitmap.
    ///
    /// This is the primary permission check: "Does user have ALL required permissions?"
    ///
    /// # Example
    ///
    /// ```rust
    /// use heracles_core::acl::PermissionBitmap;
    ///
    /// let user = PermissionBitmap::from_bit(0).union(PermissionBitmap::from_bit(1));
    /// let required = PermissionBitmap::from_bit(0);
    /// assert!(user.has(required));
    ///
    /// let more_required = PermissionBitmap::from_bit(0)
    ///     .union(PermissionBitmap::from_bit(2));
    /// assert!(!user.has(more_required)); // Missing bit 2
    /// ```
    #[inline]
    pub const fn has(self, required: Self) -> bool {
        self.bits & required.bits == required.bits
    }

    /// Check if ANY bit in `required` is set in this bitmap.
    ///
    /// Useful for "OR" permission checks: "Does user have ANY of these permissions?"
    #[inline]
    pub const fn has_any(self, required: Self) -> bool {
        self.bits & required.bits != 0
    }

    /// Check if a specific bit position is set.
    #[inline]
    pub const fn has_bit(self, pos: u8) -> bool {
        if pos >= 128 {
            return false;
        }
        self.bits & (1u128 << pos) != 0
    }

    /// Union (OR) two bitmaps - combines permissions.
    ///
    /// # Example
    ///
    /// ```rust
    /// use heracles_core::acl::PermissionBitmap;
    ///
    /// let a = PermissionBitmap::from_bit(0);
    /// let b = PermissionBitmap::from_bit(1);
    /// let combined = a.union(b);
    /// assert!(combined.has(a));
    /// assert!(combined.has(b));
    /// ```
    #[inline]
    pub const fn union(self, other: Self) -> Self {
        Self {
            bits: self.bits | other.bits,
        }
    }

    /// Intersection (AND) two bitmaps - common permissions only.
    #[inline]
    pub const fn intersection(self, other: Self) -> Self {
        Self {
            bits: self.bits & other.bits,
        }
    }

    /// Subtract (AND NOT) — remove bits present in `other`.
    ///
    /// Useful for applying deny rules: `allowed.subtract(denied)`
    ///
    /// # Example
    ///
    /// ```rust
    /// use heracles_core::acl::PermissionBitmap;
    ///
    /// let allowed = PermissionBitmap::from_bit(0).union(PermissionBitmap::from_bit(1));
    /// let denied = PermissionBitmap::from_bit(1);
    /// let effective = allowed.subtract(denied);
    /// assert!(effective.has(PermissionBitmap::from_bit(0)));
    /// assert!(!effective.has(PermissionBitmap::from_bit(1)));
    /// ```
    #[inline]
    pub const fn subtract(self, other: Self) -> Self {
        Self {
            bits: self.bits & !other.bits,
        }
    }

    /// Check if the bitmap is empty (no permissions set).
    #[inline]
    pub const fn is_empty(self) -> bool {
        self.bits == 0
    }

    /// Count the number of set bits (permissions).
    #[inline]
    pub const fn count(self) -> u32 {
        self.bits.count_ones()
    }

    /// Set a bit at the given position.
    #[inline]
    pub const fn set_bit(self, pos: u8) -> Self {
        if pos >= 128 {
            return self;
        }
        Self {
            bits: self.bits | (1u128 << pos),
        }
    }

    /// Clear a bit at the given position.
    #[inline]
    pub const fn clear_bit(self, pos: u8) -> Self {
        if pos >= 128 {
            return self;
        }
        Self {
            bits: self.bits & !(1u128 << pos),
        }
    }

    /// Create a bitmap from multiple bit positions.
    pub fn from_bits(positions: &[u8]) -> Self {
        let mut bitmap = Self::EMPTY;
        for &pos in positions {
            if pos < 128 {
                bitmap = bitmap.set_bit(pos);
            }
        }
        bitmap
    }

    /// Get all set bit positions.
    pub fn to_bits(self) -> Vec<u8> {
        let mut positions = Vec::new();
        let mut bits = self.bits;
        let mut pos = 0u8;
        while bits != 0 {
            if bits & 1 != 0 {
                positions.push(pos);
            }
            bits >>= 1;
            pos += 1;
        }
        positions
    }
}

impl fmt::Debug for PermissionBitmap {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "PermissionBitmap({:#034x})", self.bits)
    }
}

impl fmt::Display for PermissionBitmap {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        if self.is_empty() {
            write!(f, "(none)")
        } else {
            let bits = self.to_bits();
            write!(
                f,
                "bits[{}]",
                bits.iter()
                    .map(|b| b.to_string())
                    .collect::<Vec<_>>()
                    .join(",")
            )
        }
    }
}

impl std::ops::BitOr for PermissionBitmap {
    type Output = Self;

    fn bitor(self, rhs: Self) -> Self::Output {
        self.union(rhs)
    }
}

impl std::ops::BitAnd for PermissionBitmap {
    type Output = Self;

    fn bitand(self, rhs: Self) -> Self::Output {
        self.intersection(rhs)
    }
}

impl std::ops::BitOrAssign for PermissionBitmap {
    fn bitor_assign(&mut self, rhs: Self) {
        *self = self.union(rhs);
    }
}

impl std::ops::BitAndAssign for PermissionBitmap {
    fn bitand_assign(&mut self, rhs: Self) {
        *self = self.intersection(rhs);
    }
}

impl std::ops::Not for PermissionBitmap {
    type Output = Self;

    fn not(self) -> Self::Output {
        Self { bits: !self.bits }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_empty_bitmap() {
        let empty = PermissionBitmap::EMPTY;
        assert!(empty.is_empty());
        assert_eq!(empty.count(), 0);
    }

    #[test]
    fn test_all_bitmap() {
        let all = PermissionBitmap::ALL;
        assert!(!all.is_empty());
        assert_eq!(all.count(), 128);
    }

    #[test]
    fn test_from_bit() {
        let perm = PermissionBitmap::from_bit(0);
        assert!(perm.has_bit(0));
        assert!(!perm.has_bit(1));
        assert_eq!(perm.count(), 1);

        let perm127 = PermissionBitmap::from_bit(127);
        assert!(perm127.has_bit(127));
        assert!(!perm127.has_bit(126));
    }

    #[test]
    #[should_panic(expected = "bit position must be 0-127")]
    fn test_from_bit_out_of_range() {
        PermissionBitmap::from_bit(128);
    }

    #[test]
    fn test_halves_roundtrip() {
        let original = PermissionBitmap::from_bit(0)
            .union(PermissionBitmap::from_bit(63))
            .union(PermissionBitmap::from_bit(64))
            .union(PermissionBitmap::from_bit(127));

        let (low, high) = original.to_halves();
        let reconstructed = PermissionBitmap::from_halves(low, high);

        assert_eq!(original, reconstructed);
    }

    #[test]
    fn test_has_all() {
        let user = PermissionBitmap::from_bits(&[0, 1, 2, 5]);
        let required = PermissionBitmap::from_bits(&[0, 1]);

        assert!(user.has(required));
        assert!(!user.has(PermissionBitmap::from_bits(&[0, 3]))); // Missing 3
    }

    #[test]
    fn test_has_any() {
        let user = PermissionBitmap::from_bits(&[0, 1, 2]);

        assert!(user.has_any(PermissionBitmap::from_bits(&[1, 5, 10])));
        assert!(!user.has_any(PermissionBitmap::from_bits(&[5, 10, 15])));
    }

    #[test]
    fn test_union() {
        let a = PermissionBitmap::from_bits(&[0, 1]);
        let b = PermissionBitmap::from_bits(&[1, 2]);
        let combined = a.union(b);

        assert!(combined.has_bit(0));
        assert!(combined.has_bit(1));
        assert!(combined.has_bit(2));
        assert!(!combined.has_bit(3));
        assert_eq!(combined.count(), 3);
    }

    #[test]
    fn test_subtract() {
        let allowed = PermissionBitmap::from_bits(&[0, 1, 2, 3]);
        let denied = PermissionBitmap::from_bits(&[1, 3]);
        let effective = allowed.subtract(denied);

        assert!(effective.has_bit(0));
        assert!(!effective.has_bit(1));
        assert!(effective.has_bit(2));
        assert!(!effective.has_bit(3));
    }

    #[test]
    fn test_to_bits() {
        let perm = PermissionBitmap::from_bits(&[0, 5, 10, 127]);
        let bits = perm.to_bits();
        assert_eq!(bits, vec![0, 5, 10, 127]);
    }

    #[test]
    fn test_bitops() {
        let a = PermissionBitmap::from_bit(0);
        let b = PermissionBitmap::from_bit(1);

        let or = a | b;
        assert!(or.has_bit(0));
        assert!(or.has_bit(1));

        let and = or & PermissionBitmap::from_bit(0);
        assert!(and.has_bit(0));
        assert!(!and.has_bit(1));
    }

    #[test]
    fn test_display() {
        let empty = PermissionBitmap::EMPTY;
        assert_eq!(empty.to_string(), "(none)");

        let perm = PermissionBitmap::from_bits(&[0, 5, 10]);
        assert_eq!(perm.to_string(), "bits[0,5,10]");
    }

    #[test]
    fn test_serde_roundtrip() {
        let original = PermissionBitmap::from_bits(&[0, 64, 127]);
        let json = serde_json::to_string(&original).unwrap();
        let restored: PermissionBitmap = serde_json::from_str(&json).unwrap();
        assert_eq!(original, restored);
    }
}
