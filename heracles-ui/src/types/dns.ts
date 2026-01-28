/**
 * DNS Plugin Types
 *
 * TypeScript type definitions for DNS zone and record management.
 */

// ============================================================================
// Enums
// ============================================================================

export type RecordType = 'A' | 'AAAA' | 'MX' | 'NS' | 'CNAME' | 'PTR' | 'TXT' | 'SRV'

export type ZoneType = 'forward' | 'reverse-ipv4' | 'reverse-ipv6'

// ============================================================================
// SOA Record
// ============================================================================

export interface SoaRecord {
  primaryNs: string
  adminEmail: string
  serial: number
  refresh: number
  retry: number
  expire: number
  minimum: number
}

// ============================================================================
// Zone Types
// ============================================================================

export interface DnsZoneCreate {
  zoneName: string
  soaPrimaryNs: string
  soaAdminEmail: string
  defaultTtl?: number
  soaRefresh?: number
  soaRetry?: number
  soaExpire?: number
  soaMinimum?: number
}

export interface DnsZoneUpdate {
  soaPrimaryNs?: string
  soaAdminEmail?: string
  soaRefresh?: number
  soaRetry?: number
  soaExpire?: number
  soaMinimum?: number
  defaultTtl?: number
}

export interface DnsZone {
  dn: string
  zoneName: string
  zoneType: ZoneType
  soa: SoaRecord
  defaultTtl: number
  recordCount: number
}

export interface DnsZoneListItem {
  dn: string
  zoneName: string
  zoneType: ZoneType
  recordCount: number
}

export interface DnsZoneListResponse {
  zones: DnsZoneListItem[]
  total: number
}

// ============================================================================
// Record Types
// ============================================================================

export interface DnsRecordCreate {
  name: string
  recordType: RecordType
  value: string
  ttl?: number
  priority?: number
}

export interface DnsRecordUpdate {
  value?: string
  ttl?: number
  priority?: number
}

export interface DnsRecord {
  dn: string
  name: string
  recordType: RecordType
  value: string
  ttl?: number
  priority?: number
}

// ============================================================================
// Record Type Helpers
// ============================================================================

export const RECORD_TYPES: RecordType[] = ['A', 'AAAA', 'MX', 'NS', 'CNAME', 'PTR', 'TXT', 'SRV']

export const RECORD_TYPE_LABELS: Record<RecordType, string> = {
  A: 'A (IPv4)',
  AAAA: 'AAAA (IPv6)',
  MX: 'MX (Mail)',
  NS: 'NS (Nameserver)',
  CNAME: 'CNAME (Alias)',
  PTR: 'PTR (Pointer)',
  TXT: 'TXT (Text)',
  SRV: 'SRV (Service)',
}

export const RECORD_TYPE_DESCRIPTIONS: Record<RecordType, string> = {
  A: 'Maps a hostname to an IPv4 address',
  AAAA: 'Maps a hostname to an IPv6 address',
  MX: 'Specifies mail servers for the domain',
  NS: 'Delegates a DNS zone to use authoritative name servers',
  CNAME: 'Creates an alias from one name to another',
  PTR: 'Maps an IP address to a hostname (reverse DNS)',
  TXT: 'Stores text data for various purposes (SPF, DKIM, etc.)',
  SRV: 'Specifies the location of services',
}

export const ZONE_TYPE_LABELS: Record<ZoneType, string> = {
  forward: 'Forward',
  'reverse-ipv4': 'Reverse (IPv4)',
  'reverse-ipv6': 'Reverse (IPv6)',
}

/**
 * Check if a record type requires priority
 */
export function recordRequiresPriority(type: RecordType): boolean {
  return type === 'MX' || type === 'SRV'
}

/**
 * Get placeholder text for a record value based on type
 */
export function getRecordValuePlaceholder(type: RecordType): string {
  switch (type) {
    case 'A':
      return '192.168.1.10'
    case 'AAAA':
      return '2001:db8::1'
    case 'MX':
      return 'mail.example.org.'
    case 'NS':
      return 'ns1.example.org.'
    case 'CNAME':
      return 'www.example.org.'
    case 'PTR':
      return 'host.example.org.'
    case 'TXT':
      return 'v=spf1 include:_spf.google.com ~all'
    case 'SRV':
      return '10 5060 sip.example.org.'
    default:
      return ''
  }
}
