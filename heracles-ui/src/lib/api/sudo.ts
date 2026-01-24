/**
 * Sudo Plugin API Client
 * 
 * API client functions for sudo roles management
 */

import { apiClient } from '../api-client'
import type {
  SudoRoleData,
  SudoRoleCreate,
  SudoRoleUpdate,
  SudoRoleListResponse,
} from '@/types/sudo'

const BASE_PATH = '/sudo'

// ============================================================================
// Sudo Role API Functions
// ============================================================================

/**
 * List all sudo roles with optional pagination
 */
export async function listSudoRoles(params?: {
  page?: number
  page_size?: number
  search?: string
}): Promise<SudoRoleListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set('page', params.page.toString())
  if (params?.page_size) searchParams.set('page_size', params.page_size.toString())
  if (params?.search) searchParams.set('search', params.search)
  
  const query = searchParams.toString()
  const url = query ? `${BASE_PATH}/roles?${query}` : `${BASE_PATH}/roles`
  
  return apiClient.get<SudoRoleListResponse>(url)
}

/**
 * Get a single sudo role by CN
 */
export async function getSudoRole(cn: string): Promise<SudoRoleData> {
  return apiClient.get<SudoRoleData>(`${BASE_PATH}/roles/${encodeURIComponent(cn)}`)
}

/**
 * Create a new sudo role
 */
export async function createSudoRole(data: SudoRoleCreate): Promise<SudoRoleData> {
  return apiClient.post<SudoRoleData>(`${BASE_PATH}/roles`, data)
}

/**
 * Update an existing sudo role
 */
export async function updateSudoRole(cn: string, data: SudoRoleUpdate): Promise<SudoRoleData> {
  return apiClient.put<SudoRoleData>(`${BASE_PATH}/roles/${encodeURIComponent(cn)}`, data)
}

/**
 * Delete a sudo role
 */
export async function deleteSudoRole(cn: string): Promise<void> {
  return apiClient.delete(`${BASE_PATH}/roles/${encodeURIComponent(cn)}`)
}

/**
 * Get default role (sudo-defaults)
 */
export async function getDefaultRole(): Promise<SudoRoleData> {
  return apiClient.get<SudoRoleData>(`${BASE_PATH}/defaults`)
}

/**
 * Update default role options
 */
export async function updateDefaultRole(data: { sudoOption: string[] }): Promise<SudoRoleData> {
  return apiClient.put<SudoRoleData>(`${BASE_PATH}/defaults`, data)
}

// ============================================================================
// Export API Object
// ============================================================================

export const sudoApi = {
  listRoles: listSudoRoles,
  getRole: getSudoRole,
  createRole: createSudoRole,
  updateRole: updateSudoRole,
  deleteRole: deleteSudoRole,
  getDefaults: getDefaultRole,
  updateDefaults: updateDefaultRole,
}
