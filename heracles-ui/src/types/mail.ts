/**
 * Mail Plugin Types
 *
 * TypeScript type definitions for mail account management
 */

// ============================================================================
// Enums
// ============================================================================

export type DeliveryMode = 'normal' | 'forward_only' | 'local_only'

// ============================================================================
// User Mail Account Types
// ============================================================================

export interface MailAccountCreate {
  mail: string
  mailServer?: string
  quotaMb?: number
  alternateAddresses?: string[]
  forwardingAddresses?: string[]
}

export interface MailAccountRead {
  mail: string
  mailServer?: string
  quotaMb?: number
  quotaUsedMb?: number
  alternateAddresses: string[]
  forwardingAddresses: string[]
  deliveryMode: DeliveryMode
  vacationEnabled: boolean
  vacationMessage?: string
  vacationStart?: string
  vacationEnd?: string
}

export interface MailAccountUpdate {
  mail?: string
  mailServer?: string
  quotaMb?: number
  alternateAddresses?: string[]
  forwardingAddresses?: string[]
  deliveryMode?: DeliveryMode
  vacationEnabled?: boolean
  vacationMessage?: string
  vacationStart?: string
  vacationEnd?: string
}

export interface UserMailStatus {
  uid: string
  dn: string
  active: boolean
  data: MailAccountRead | null
}

// ============================================================================
// Group Mail Types
// ============================================================================

export interface MailGroupCreate {
  mail: string
  mailServer?: string
  alternateAddresses?: string[]
  forwardingAddresses?: string[]
  localOnly?: boolean
  maxMessageSizeKb?: number
}

export interface MailGroupRead {
  mail: string
  mailServer?: string
  alternateAddresses: string[]
  forwardingAddresses: string[]
  localOnly: boolean
  maxMessageSizeKb?: number
  memberEmails: string[]
}

export interface MailGroupUpdate {
  mail?: string
  mailServer?: string
  alternateAddresses?: string[]
  forwardingAddresses?: string[]
  localOnly?: boolean
  maxMessageSizeKb?: number
}

export interface GroupMailStatus {
  cn: string
  dn: string
  active: boolean
  data: MailGroupRead | null
}

// ============================================================================
// Helper Functions
// ============================================================================

export function formatQuota(quotaMb?: number): string {
  if (quotaMb === undefined || quotaMb === null) {
    return 'Unlimited'
  }
  if (quotaMb >= 1024) {
    return `${(quotaMb / 1024).toFixed(1)} GB`
  }
  return `${quotaMb} MB`
}

export function formatQuotaUsage(usedMb?: number, totalMb?: number): string {
  if (usedMb === undefined || usedMb === null) {
    return 'Unknown'
  }
  const used = formatQuota(usedMb)
  const total = formatQuota(totalMb)
  return `${used} / ${total}`
}

export function getQuotaPercentage(usedMb?: number, totalMb?: number): number {
  if (!usedMb || !totalMb) {
    return 0
  }
  return Math.min(100, Math.round((usedMb / totalMb) * 100))
}

export function formatDeliveryMode(mode: DeliveryMode): string {
  switch (mode) {
    case 'normal':
      return 'Normal'
    case 'forward_only':
      return 'Forward Only'
    case 'local_only':
      return 'Local Only'
    default:
      return mode
  }
}

export function formatDate(dateStr?: string): string {
  if (!dateStr || dateStr.length !== 8) {
    return ''
  }
  const year = dateStr.slice(0, 4)
  const month = dateStr.slice(4, 6)
  const day = dateStr.slice(6, 8)
  return `${year}-${month}-${day}`
}

export function toDateString(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}${month}${day}`
}
