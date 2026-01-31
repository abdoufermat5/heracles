/**
 * DNS Plugin API Client
 *
 * API client functions for DNS zone and record management.
 */

import { apiClient } from '../api-client'
import type {
  DnsZone,
  DnsZoneCreate,
  DnsZoneUpdate,
  DnsZoneListResponse,
  DnsRecord,
  DnsRecordCreate,
  DnsRecordUpdate,
} from '@/types/dns'

const BASE_PATH = '/dns'

// ============================================================================
// Zone API Functions
// ============================================================================

/**
 * List all DNS zones
 */
export async function listZones(params?: { base?: string }): Promise<DnsZoneListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.base) searchParams.set('base_dn', params.base)

  const query = searchParams.toString()
  const url = query ? `${BASE_PATH}/zones?${query}` : `${BASE_PATH}/zones`

  return apiClient.get<DnsZoneListResponse>(url)
}

/**
 * Get a single DNS zone by name
 */
export async function getZone(zoneName: string, baseDn?: string): Promise<DnsZone> {
  const query = baseDn ? `?base_dn=${encodeURIComponent(baseDn)}` : ''
  return apiClient.get<DnsZone>(
    `${BASE_PATH}/zones/${encodeURIComponent(zoneName)}${query}`
  )
}

/**
 * Create a new DNS zone
 */
export async function createZone(data: DnsZoneCreate, baseDn?: string): Promise<DnsZone> {
  const query = baseDn ? `?base_dn=${encodeURIComponent(baseDn)}` : ''
  return apiClient.post<DnsZone>(`${BASE_PATH}/zones${query}`, data)
}

/**
 * Update a DNS zone
 */
export async function updateZone(
  zoneName: string,
  data: DnsZoneUpdate,
  baseDn?: string
): Promise<DnsZone> {
  const query = baseDn ? `?base_dn=${encodeURIComponent(baseDn)}` : ''
  return apiClient.put<DnsZone>(
    `${BASE_PATH}/zones/${encodeURIComponent(zoneName)}${query}`,
    data
  )
}

/**
 * Delete a DNS zone
 */
export async function deleteZone(zoneName: string, baseDn?: string): Promise<void> {
  const query = baseDn ? `?base_dn=${encodeURIComponent(baseDn)}` : ''
  return apiClient.delete(
    `${BASE_PATH}/zones/${encodeURIComponent(zoneName)}${query}`
  )
}

// ============================================================================
// Record API Functions
// ============================================================================

/**
 * List all records in a zone
 */
export async function listRecords(zoneName: string): Promise<DnsRecord[]> {
  return apiClient.get<DnsRecord[]>(
    `${BASE_PATH}/zones/${encodeURIComponent(zoneName)}/records`
  )
}

/**
 * Create a new DNS record in a zone
 */
export async function createRecord(
  zoneName: string,
  data: DnsRecordCreate
): Promise<DnsRecord> {
  return apiClient.post<DnsRecord>(
    `${BASE_PATH}/zones/${encodeURIComponent(zoneName)}/records`,
    data
  )
}

/**
 * Update a DNS record
 */
export async function updateRecord(
  zoneName: string,
  name: string,
  recordType: string,
  oldValue: string,
  data: DnsRecordUpdate
): Promise<DnsRecord> {
  const params = new URLSearchParams({ old_value: oldValue })
  return apiClient.put<DnsRecord>(
    `${BASE_PATH}/zones/${encodeURIComponent(zoneName)}/records/${encodeURIComponent(name)}/${recordType}?${params}`,
    data
  )
}

/**
 * Delete a DNS record
 */
export async function deleteRecord(
  zoneName: string,
  name: string,
  recordType: string,
  value: string
): Promise<void> {
  const params = new URLSearchParams({ value })
  return apiClient.delete(
    `${BASE_PATH}/zones/${encodeURIComponent(zoneName)}/records/${encodeURIComponent(name)}/${recordType}?${params}`
  )
}

// ============================================================================
// Export API Object
// ============================================================================

export const dnsApi = {
  // Zones
  listZones,
  getZone,
  createZone,
  updateZone,
  deleteZone,
  // Records
  listRecords,
  createRecord,
  updateRecord,
  deleteRecord,
}
