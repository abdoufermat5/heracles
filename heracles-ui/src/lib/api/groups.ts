import { apiClient } from '../api-client'
import type { Group, GroupListResponse, GroupCreateData, GroupUpdateData, PaginationParams } from '@/types'

export const groupsApi = {
  list: async (params?: PaginationParams): Promise<GroupListResponse> => {
    return apiClient.get<GroupListResponse>('/groups', params)
  },

  get: async (cn: string): Promise<Group> => {
    return apiClient.get<Group>(`/groups/${cn}`)
  },

  create: async (data: GroupCreateData): Promise<Group> => {
    return apiClient.post<Group>('/groups', data)
  },

  update: async (cn: string, data: GroupUpdateData): Promise<Group> => {
    return apiClient.patch<Group>(`/groups/${cn}`, data)
  },

  delete: async (cn: string): Promise<void> => {
    await apiClient.delete(`/groups/${cn}`)
  },

  addMember: async (cn: string, uid: string): Promise<void> => {
    await apiClient.post(`/groups/${cn}/members`, { uid })
  },

  removeMember: async (cn: string, uid: string): Promise<void> => {
    await apiClient.delete(`/groups/${cn}/members/${uid}`)
  },

  getMembers: async (cn: string): Promise<string[]> => {
    return apiClient.get<string[]>(`/groups/${cn}/members`)
  },
}
