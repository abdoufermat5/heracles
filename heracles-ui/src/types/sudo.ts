/**
 * Sudo Plugin Types
 * 
 * TypeScript type definitions for sudo roles management
 */

// ============================================================================
// Sudo Role Types
// ============================================================================

export interface SudoRoleData {
  dn: string
  cn: string
  description?: string
  sudoUser: string[]
  sudoHost: string[]
  sudoCommand: string[]
  sudoRunAsUser: string[]
  sudoRunAsGroup: string[]
  sudoOption: string[]
  sudoOrder: number
  sudoNotBefore?: string
  sudoNotAfter?: string
  isDefault: boolean
  isValid: boolean
}

export interface SudoRoleCreate {
  cn: string
  description?: string
  sudoUser?: string[]
  sudoHost?: string[]
  sudoCommand?: string[]
  sudoRunAsUser?: string[]
  sudoRunAsGroup?: string[]
  sudoOption?: string[]
  sudoOrder?: number
  sudoNotBefore?: string
  sudoNotAfter?: string
}

export interface SudoRoleUpdate {
  description?: string
  sudoUser?: string[]
  sudoHost?: string[]
  sudoCommand?: string[]
  sudoRunAsUser?: string[]
  sudoRunAsGroup?: string[]
  sudoOption?: string[]
  sudoOrder?: number
  sudoNotBefore?: string
  sudoNotAfter?: string
}

export interface SudoRoleListResponse {
  roles: SudoRoleData[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

// ============================================================================
// Sudo Role List Item (for table display)
// ============================================================================

export interface SudoRoleListItem {
  cn: string
  description?: string
  sudoUser: string[]
  sudoHost: string[]
  sudoCommand: string[]
  sudoOption: string[]
  sudoOrder: number
  isDefault: boolean
  isValid: boolean
}

// ============================================================================
// Common Sudo Options
// ============================================================================

export const SUDO_OPTIONS = [
  { value: 'NOPASSWD', label: 'No Password Required', description: 'Allow sudo without password' },
  { value: '!authenticate', label: 'Skip Authentication', description: 'Skip password authentication' },
  { value: 'PASSWD', label: 'Password Required', description: 'Always require password' },
  { value: 'NOEXEC', label: 'No Exec', description: 'Prevent executed commands from executing other commands' },
  { value: 'EXEC', label: 'Allow Exec', description: 'Allow executed commands to run other commands' },
  { value: 'SETENV', label: 'Set Environment', description: 'Allow user to set environment variables' },
  { value: 'NOSETENV', label: 'No Set Environment', description: 'Prevent setting environment variables' },
  { value: '!requiretty', label: 'No TTY Required', description: 'Allow sudo without a TTY' },
  { value: 'env_reset', label: 'Reset Environment', description: 'Reset environment to a default set' },
  { value: 'mail_badpass', label: 'Mail Bad Password', description: 'Send mail on bad password attempts' },
] as const

// ============================================================================
// Default Commands
// ============================================================================

export const COMMON_COMMANDS = [
  { value: 'ALL', label: 'All Commands', description: 'Allow all commands' },
  { value: '/usr/bin/systemctl', label: 'Systemctl', description: 'Service management' },
  { value: '/usr/bin/apt', label: 'APT', description: 'Package management (Debian)' },
  { value: '/usr/bin/yum', label: 'YUM', description: 'Package management (RHEL)' },
  { value: '/usr/bin/dnf', label: 'DNF', description: 'Package management (Fedora)' },
  { value: '/bin/cat', label: 'Cat', description: 'View files' },
  { value: '/bin/less', label: 'Less', description: 'Page through files' },
  { value: '/bin/tail', label: 'Tail', description: 'View end of files' },
  { value: '/usr/bin/vim', label: 'Vim', description: 'Text editor' },
  { value: '/usr/bin/nano', label: 'Nano', description: 'Text editor' },
  { value: '!/bin/su', label: 'Deny Su', description: 'Prevent switching user' },
  { value: '!/bin/bash', label: 'Deny Bash', description: 'Prevent running bash' },
] as const
