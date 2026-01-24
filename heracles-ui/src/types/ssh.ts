/**
 * SSH Plugin Types
 * 
 * TypeScript type definitions for SSH key management
 */

// ============================================================================
// SSH Key Types
// ============================================================================

export const SSH_KEY_TYPES = [
  'ssh-rsa',
  'ssh-dss',
  'ssh-ed25519',
  'ecdsa-sha2-nistp256',
  'ecdsa-sha2-nistp384',
  'ecdsa-sha2-nistp521',
  'sk-ssh-ed25519@openssh.com',
  'sk-ecdsa-sha2-nistp256@openssh.com',
] as const

export type SSHKeyType = typeof SSH_KEY_TYPES[number]

// ============================================================================
// SSH Key Schemas
// ============================================================================

export interface SSHKeyRead {
  key: string
  keyType: SSHKeyType | 'unknown'
  fingerprint: string
  comment?: string
  bits?: number
  addedAt?: string
}

export interface SSHKeyCreate {
  key: string
  comment?: string
}

export interface SSHKeyUpdate {
  comment?: string
}

// ============================================================================
// User SSH Status
// ============================================================================

export interface UserSSHStatus {
  uid: string
  dn: string
  hasSsh: boolean
  keys: SSHKeyRead[]
  keyCount: number
}

export interface UserSSHActivate {
  initialKey?: string
}

export interface UserSSHKeysUpdate {
  keys: string[]
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get a friendly name for SSH key type
 */
export function getKeyTypeName(keyType: string): string {
  switch (keyType) {
    case 'ssh-rsa':
      return 'RSA'
    case 'ssh-dss':
      return 'DSA'
    case 'ssh-ed25519':
      return 'Ed25519'
    case 'ecdsa-sha2-nistp256':
      return 'ECDSA P-256'
    case 'ecdsa-sha2-nistp384':
      return 'ECDSA P-384'
    case 'ecdsa-sha2-nistp521':
      return 'ECDSA P-521'
    case 'sk-ssh-ed25519@openssh.com':
      return 'Ed25519-SK'
    case 'sk-ecdsa-sha2-nistp256@openssh.com':
      return 'ECDSA-SK P-256'
    default:
      return keyType
  }
}

/**
 * Get key strength badge variant
 */
export function getKeyStrengthVariant(keyType: string, bits?: number): 'default' | 'secondary' | 'destructive' | 'outline' {
  // Ed25519 is always strong
  if (keyType === 'ssh-ed25519' || keyType === 'sk-ssh-ed25519@openssh.com') {
    return 'default'
  }
  
  // ECDSA variants
  if (keyType.includes('ecdsa')) {
    return 'default'
  }
  
  // RSA - depends on bits
  if (keyType === 'ssh-rsa' && bits) {
    if (bits >= 4096) return 'default'
    if (bits >= 2048) return 'secondary'
    return 'destructive' // < 2048 is weak
  }
  
  // DSA is deprecated
  if (keyType === 'ssh-dss') {
    return 'destructive'
  }
  
  return 'outline'
}

/**
 * Truncate fingerprint for display
 */
export function truncateFingerprint(fingerprint: string): string {
  if (!fingerprint) return ''
  // SHA256:abcdefghijklmnopqrstuvwxyz... -> SHA256:abcdef...xyz
  if (fingerprint.length > 20) {
    const prefix = fingerprint.slice(0, 15)
    const suffix = fingerprint.slice(-6)
    return `${prefix}...${suffix}`
  }
  return fingerprint
}

/**
 * URL-encode fingerprint for API calls
 */
export function encodeFingerprint(fingerprint: string): string {
  // Replace + with - and / with _ for URL safety
  return fingerprint
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/^SHA256:/, '')
}
