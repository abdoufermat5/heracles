import { apiClient } from '../api-client'
import type { Role, RoleListResponse, RoleCreateData, RoleUpdateData, PaginationParams } from '@/types'

export const rolesApi = {
    list: async (params?: PaginationParams): Promise<RoleListResponse> => {
        return apiClient.get<RoleListResponse>('/roles', params)
    },

    get: async (cn: string): Promise<Role> => {
        return apiClient.get<Role>(`/roles/${cn}`)
    },

    create: async (data: RoleCreateData): Promise<Role> => {
        return apiClient.post<Role>('/roles', data)
    },

    update: async (cn: string, data: RoleUpdateData): Promise<Role> => {
        return apiClient.patch<Role>(`/roles/${cn}`, data)
    },

    delete: async (cn: string): Promise<void> => {
        await apiClient.delete(`/roles/${cn}`)
    },

    addMember: async (cn: string, uid: string): Promise<void> => {
        await apiClient.post(`/roles/${cn}/members`, { uid })
    },

    removeMember: async (cn: string, uid: string): Promise<void> => {
        await apiClient.delete(`/roles/${cn}/members/${uid}`)
    },
}
