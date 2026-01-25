/**
 * Systems Plugin Types
 *
 * TypeScript type definitions for system management
 */

// ============================================================================
// System Types
// ============================================================================

export const SYSTEM_TYPES = [
  'server',
  'workstation',
  'terminal',
  'printer',
  'component',
  'phone',
  'mobile',
] as const

export type SystemType = (typeof SYSTEM_TYPES)[number]

export const SYSTEM_TYPE_LABELS: Record<SystemType, string> = {
  server: 'Server',
  workstation: 'Workstation',
  terminal: 'Terminal',
  printer: 'Printer',
  component: 'Component',
  phone: 'Phone',
  mobile: 'Mobile Phone',
}

export const SYSTEM_TYPE_ICONS: Record<SystemType, string> = {
  server: 'Server',
  workstation: 'Monitor',
  terminal: 'MonitorSmartphone',
  printer: 'Printer',
  component: 'Cpu',
  phone: 'Phone',
  mobile: 'Smartphone',
}

// ============================================================================
// Lock Mode
// ============================================================================

export const LOCK_MODES = ['locked', 'unlocked'] as const
export type LockMode = (typeof LOCK_MODES)[number]

export const LOCK_MODE_LABELS: Record<LockMode, string> = {
  locked: 'Locked',
  unlocked: 'Active',
}

// ============================================================================
// System Data Types
// ============================================================================

/**
 * Full system data as returned by the API
 * Note: Field names match LDAP attribute aliases from the API
 */
export interface SystemData {
  dn: string
  cn: string
  systemType: SystemType
  description?: string
  ipHostNumber?: string[]
  macAddress?: string[]
  hrcMode?: LockMode
  l?: string  // location
  // Printer specific
  labeledURI?: string
  hrcPrinterWindowsInfFile?: string
  hrcPrinterWindowsDriverDir?: string
  hrcPrinterWindowsDriverName?: string
  // Phone specific
  telephoneNumber?: string
  serialNumber?: string
  // Mobile specific
  hrcMobileIMEI?: string
  hrcMobileOS?: string
  hrcMobilePUK?: string
  // Component specific
  owner?: string
}

export interface SystemCreate {
  cn: string
  system_type: SystemType
  description?: string
  ip_addresses?: string[]
  mac_addresses?: string[]
  mode?: LockMode
  location?: string
  // Printer specific
  labeled_uri?: string
  windows_inf_file?: string
  windows_driver_dir?: string
  windows_driver_name?: string
  // Phone specific
  telephone_number?: string
  serial_number?: string
  // Mobile specific
  imei?: string
  operating_system?: string
  puk?: string
  // Component specific
  owner?: string
}

export interface SystemUpdate {
  description?: string
  ip_addresses?: string[]
  mac_addresses?: string[]
  mode?: LockMode
  location?: string
  // Printer specific
  labeled_uri?: string
  windows_inf_file?: string
  windows_driver_dir?: string
  windows_driver_name?: string
  // Phone specific
  telephone_number?: string
  serial_number?: string
  // Mobile specific
  imei?: string
  operating_system?: string
  puk?: string
  // Component specific
  owner?: string
}

export interface SystemListItem {
  dn: string
  cn: string
  systemType: SystemType
  description?: string
  ipHostNumber?: string[]
  macAddress?: string[]
  l?: string  // location
  hrcMode?: LockMode
}

export interface SystemListResponse {
  systems: SystemListItem[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

// ============================================================================
// Host Validation
// ============================================================================

export interface HostValidationRequest {
  hosts: string[]
}

export interface HostValidationResponse {
  valid_hosts: string[]
  invalid_hosts: string[]
  all_valid: boolean
}

// ============================================================================
// Mobile OS Options
// ============================================================================

export const MOBILE_OS_OPTIONS = [
  { value: 'iOS', label: 'iOS (iPhone/iPad)' },
  { value: 'Android', label: 'Android' },
  { value: 'Windows', label: 'Windows Mobile' },
  { value: 'Other', label: 'Other' },
] as const
