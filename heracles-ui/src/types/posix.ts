/**
 * POSIX Plugin Types
 * 
 * TypeScript type definitions for POSIX accounts and groups
 */

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
  uidNumber?: number | null
  gidNumber: number
  homeDirectory?: string | null
  loginShell?: string
  gecos?: string | null
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
}

// ============================================================================
// Group POSIX Types
// ============================================================================

export interface PosixGroupData {
  cn: string
  gidNumber: number
  description?: string
  memberUid?: string[]
}

export interface PosixGroupCreate {
  gidNumber?: number
}

export interface PosixGroupUpdate {
  gidNumber?: number
  description?: string
}

export interface PosixGroupSummary {
  cn: string
  gidNumber: number
  description?: string
}

export interface PosixGroupListItem {
  cn: string
  gidNumber: number
  description?: string
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
