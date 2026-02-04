import { apiClient } from '../api-client'
import type {
  Department,
  DepartmentListResponse,
  DepartmentTreeResponse,
  DepartmentCreateData,
  DepartmentUpdateData,
  DepartmentListParams,
} from '@/types'

export const departmentsApi = {
  /**
   * Get full department hierarchy as a tree
   */
  getTree: async (): Promise<DepartmentTreeResponse> => {
    return apiClient.get<DepartmentTreeResponse>('/departments/tree')
  },

  /**
   * List departments with optional filtering
   */
  list: async (params?: DepartmentListParams): Promise<DepartmentListResponse> => {
    return apiClient.get<DepartmentListResponse>('/departments', params as Record<string, string | number | undefined>)
  },

  /**
   * Get a single department by DN
   */
  get: async (dn: string): Promise<Department> => {
    const encodedDn = encodeURIComponent(dn)
    return apiClient.get<Department>(`/departments/${encodedDn}`)
  },

  /**
   * Create a new department
   */
  create: async (data: DepartmentCreateData): Promise<Department> => {
    return apiClient.post<Department>('/departments', data)
  },

  /**
   * Update a department
   */
  update: async (dn: string, data: DepartmentUpdateData): Promise<Department> => {
    const encodedDn = encodeURIComponent(dn)
    return apiClient.patch<Department>(`/departments/${encodedDn}`, data)
  },

  /**
   * Delete a department
   */
  delete: async (dn: string, recursive?: boolean): Promise<void> => {
    const encodedDn = encodeURIComponent(dn)
    const params = recursive ? { recursive: 'true' } : undefined
    await apiClient.delete(`/departments/${encodedDn}${params ? `?recursive=${params.recursive}` : ''}`)
  },
}
