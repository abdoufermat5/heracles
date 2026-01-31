/**
 * Systems Plugin API Client
 *
 * API client functions for system management
 */

import { apiClient } from '../api-client'
import type {
  SystemData,
  SystemCreate,
  SystemUpdate,
  SystemListResponse,
  SystemType,
  HostValidationRequest,
  HostValidationResponse,
} from '@/types/systems'

const BASE_PATH = '/systems'

// ============================================================================
// System API Functions
// ============================================================================

/**
 * List all systems with optional filtering
 */
export async function listSystems(params?: {
  system_type?: SystemType
  page?: number
  page_size?: number
  search?: string
  base?: string
}): Promise<SystemListResponse> {
  const searchParams = new URLSearchParams()
  // Backend uses 'type' as alias for system_type parameter
  if (params?.system_type) searchParams.set('type', params.system_type)
  if (params?.page) searchParams.set('page', params.page.toString())
  if (params?.page_size) searchParams.set('page_size', params.page_size.toString())
  if (params?.search) searchParams.set('search', params.search)
  if (params?.base) searchParams.set('base_dn', params.base)

  const query = searchParams.toString()
  const url = query ? `${BASE_PATH}?${query}` : BASE_PATH

  return apiClient.get<SystemListResponse>(url)
}

/**
 * Get a single system by type and CN
 */
export async function getSystem(
  systemType: SystemType,
  cn: string,
  baseDn?: string
): Promise<SystemData> {
  const query = baseDn ? `?base_dn=${encodeURIComponent(baseDn)}` : ''
  return apiClient.get<SystemData>(
    `${BASE_PATH}/${systemType}/${encodeURIComponent(cn)}${query}`
  )
}

/**
 * Create a new system
 */
export async function createSystem(data: SystemCreate, baseDn?: string): Promise<SystemData> {
  const query = baseDn ? `?base_dn=${encodeURIComponent(baseDn)}` : ''
  return apiClient.post<SystemData>(`${BASE_PATH}${query}`, data)
}

/**
 * Update an existing system
 */
export async function updateSystem(
  systemType: SystemType,
  cn: string,
  data: SystemUpdate,
  baseDn?: string
): Promise<SystemData> {
  const query = baseDn ? `?base_dn=${encodeURIComponent(baseDn)}` : ''
  return apiClient.put<SystemData>(
    `${BASE_PATH}/${systemType}/${encodeURIComponent(cn)}${query}`,
    data
  )
}

/**
 * Delete a system
 */
export async function deleteSystem(
  systemType: SystemType,
  cn: string,
  baseDn?: string
): Promise<void> {
  const query = baseDn ? `?base_dn=${encodeURIComponent(baseDn)}` : ''
  return apiClient.delete(
    `${BASE_PATH}/${systemType}/${encodeURIComponent(cn)}${query}`
  )
}

/**
 * Validate hosts against existing systems
 */
export async function validateHosts(
  request: HostValidationRequest
): Promise<HostValidationResponse> {
  return apiClient.post<HostValidationResponse>(
    `${BASE_PATH}/validate-hosts`,
    request
  )
}

/**
 * Get all hostnames (for autocomplete/validation)
 */
export async function getAllHostnames(): Promise<string[]> {
  return apiClient.get<string[]>(`${BASE_PATH}/hostnames`)
}

// ============================================================================
// Convenience functions by type
// ============================================================================

export async function listServers(params?: {
  page?: number
  page_size?: number
  search?: string
}) {
  return listSystems({ ...params, system_type: 'server' })
}

export async function listWorkstations(params?: {
  page?: number
  page_size?: number
  search?: string
}) {
  return listSystems({ ...params, system_type: 'workstation' })
}

export async function listTerminals(params?: {
  page?: number
  page_size?: number
  search?: string
}) {
  return listSystems({ ...params, system_type: 'terminal' })
}

export async function listPrinters(params?: {
  page?: number
  page_size?: number
  search?: string
}) {
  return listSystems({ ...params, system_type: 'printer' })
}

export async function listComponents(params?: {
  page?: number
  page_size?: number
  search?: string
}) {
  return listSystems({ ...params, system_type: 'component' })
}

export async function listPhones(params?: {
  page?: number
  page_size?: number
  search?: string
}) {
  return listSystems({ ...params, system_type: 'phone' })
}

export async function listMobiles(params?: {
  page?: number
  page_size?: number
  search?: string
}) {
  return listSystems({ ...params, system_type: 'mobile' })
}

// ============================================================================
// Export API Object
// ============================================================================

export const systemsApi = {
  list: listSystems,
  get: getSystem,
  create: createSystem,
  update: updateSystem,
  delete: deleteSystem,
  validateHosts,
  getAllHostnames,
  // By type
  listServers,
  listWorkstations,
  listTerminals,
  listPrinters,
  listComponents,
  listPhones,
  listMobiles,
}
