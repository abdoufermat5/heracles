/**
 * POSIX Plugin Types
 * 
 * TypeScript type definitions for POSIX accounts and groups
 */

// ============================================================================
// Enums
// ============================================================================

export type TrustMode = 'fullaccess' | 'byhost'

export type AccountStatus = 'active' | 'expired' | 'password_expired' | 'grace_time' | 'locked'

export type PrimaryGroupMode = 'select_existing' | 'create_personal'

// ============================================================================
// User POSIX Account Types
// ============================================================================

export interface PosixAccountData {
  uidNumber: number
  gidNumber: number
  homeDirectory: string
  loginShell: string
  gecos?: string
  // Shadow account fields
  shadowLastChange?: number
  shadowMin?: number
  shadowMax?: number
  shadowWarning?: number
  shadowInactive?: number
  shadowExpire?: number
  // System trust (hostObject)
  trustMode?: TrustMode
  host?: string[]
  // Primary group info
  primaryGroupCn?: string
  // Group memberships
  groupMemberships?: string[]
  // Computed account status
  accountStatus?: AccountStatus
}

export interface PosixStatus {
  active: boolean
  data?: PosixAccountData
}

export interface PosixGroupStatus {
  active: boolean
  data?: PosixGroupData
}

export interface PosixAccountCreate {
  // ID allocation
  uidNumber?: number | null
  forceUid?: boolean
  // Primary group configuration
  primaryGroupMode?: PrimaryGroupMode
  gidNumber?: number | null
  forceGid?: boolean
  // Basic attributes
  homeDirectory?: string | null
  loginShell?: string
  gecos?: string | null
  // System trust
  trustMode?: TrustMode
  host?: string[]
}

export interface PosixAccountUpdate {
  gidNumber?: number
  homeDirectory?: string
  loginShell?: string
  gecos?: string
  shadowMin?: number
  shadowMax?: number
  shadowWarning?: number
  shadowInactive?: number
  shadowExpire?: number
  // System trust
  trustMode?: TrustMode
  host?: string[]
  // Force password change
  mustChangePassword?: boolean
}

// ============================================================================
// Group POSIX Types
// ============================================================================

export interface PosixGroupData {
  cn: string
  gidNumber: number
  description?: string
  memberUid: string[]
  is_active?: boolean
  // System trust (hostObject)
  trustMode?: TrustMode
  host?: string[]
}

/** Schema for creating a new standalone POSIX group */
export interface PosixGroupFullCreate {
  cn: string
  gidNumber?: number
  forceGid?: boolean
  description?: string
  memberUid?: string[]
  // System trust (hostObject)
  trustMode?: TrustMode
  host?: string[]
}

/** Schema for updating an existing POSIX group */
export interface PosixGroupUpdate {
  description?: string
  memberUid?: string[]
  // System trust (hostObject)
  trustMode?: TrustMode | null
  host?: string[] | null
}

export interface PosixGroupListItem {
  cn: string
  gidNumber: number
  description?: string
  memberCount: number
}

export interface PosixGroupListResponse {
  groups: PosixGroupListItem[]
  total: number
}

// ============================================================================
// Utility Types
// ============================================================================

export interface ShellOption {
  value: string
  label: string
}

export interface AvailableShells {
  shells: ShellOption[]
  default: string
}

export interface NextIds {
  uidNumber: number
  gidNumber: number
  next_uid: number
  next_gid: number
}

// ============================================================================
// MixedGroup Types (groupOfNames + posixGroup)
// ============================================================================

/**
 * MixedGroup combines groupOfNames (LDAP) and posixGroup (UNIX).
 * 
 * This allows a group to be used for both:
 * - LDAP-based access control (member attribute with DNs)
 * - UNIX/POSIX permissions (memberUid attribute with UIDs)
 */
export interface MixedGroupData {
  cn: string
  gidNumber: number
  description?: string
  /** LDAP members (DNs) - from groupOfNames */
  member: string[]
  /** UNIX members (UIDs) - from posixGroup */
  memberUid: string[]
  /** Indicates this is a mixed group */
  isMixedGroup: boolean
  // System trust (hostObject)
  trustMode?: TrustMode
  host?: string[]
}

/** Schema for creating a new MixedGroup */
export interface MixedGroupCreate {
  cn: string
  gidNumber?: number
  forceGid?: boolean
  description?: string
  /** Initial LDAP members (DNs) */
  member?: string[]
  /** Initial UNIX members (UIDs) */
  memberUid?: string[]
  // System trust (hostObject)
  trustMode?: TrustMode
  host?: string[]
}

/** Schema for updating a MixedGroup */
export interface MixedGroupUpdate {
  description?: string
  /** Replace all LDAP members */
  member?: string[]
  /** Replace all UNIX members */
  memberUid?: string[]
  // System trust (hostObject)
  trustMode?: TrustMode | null
  host?: string[] | null
}

/** Summary item for MixedGroup listing */
export interface MixedGroupListItem {
  cn: string
  gidNumber: number
  description?: string
  /** Number of LDAP members */
  memberCount: number
  /** Number of UNIX members */
  memberUidCount: number
}

export interface MixedGroupListResponse {
  groups: MixedGroupListItem[]
}
