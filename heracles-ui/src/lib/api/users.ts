import { apiClient } from '../api-client'
import type { User, UserListResponse, UserCreateData, UserUpdateData, SetPasswordData, PaginationParams } from '@/types'

export interface LockStatus {
  uid: string
  locked: boolean
}

export const usersApi = {
  list: async (params?: PaginationParams): Promise<UserListResponse> => {
    return apiClient.get<UserListResponse>('/users', params)
  },

  get: async (uid: string): Promise<User> => {
    return apiClient.get<User>(`/users/${uid}`)
  },

  create: async (data: UserCreateData): Promise<User> => {
    return apiClient.post<User>('/users', data)
  },

  update: async (uid: string, data: UserUpdateData): Promise<User> => {
    return apiClient.patch<User>(`/users/${uid}`, data)
  },

  delete: async (uid: string): Promise<void> => {
    await apiClient.delete(`/users/${uid}`)
  },

  setPassword: async (uid: string, data: SetPasswordData): Promise<void> => {
    await apiClient.post(`/users/${uid}/password`, data)
  },

  getGroups: async (uid: string): Promise<string[]> => {
    return apiClient.get<string[]>(`/users/${uid}/groups`)
  },

  getLockStatus: async (uid: string): Promise<LockStatus> => {
    return apiClient.get<LockStatus>(`/users/${uid}/locked`)
  },

  lock: async (uid: string): Promise<void> => {
    await apiClient.post(`/users/${uid}/lock`)
  },

  unlock: async (uid: string): Promise<void> => {
    await apiClient.post(`/users/${uid}/unlock`)
  },

  uploadPhoto: async (uid: string, photoBase64: string): Promise<void> => {
    await apiClient.put(`/users/${uid}/photo`, { photo: photoBase64 })
  },

  deletePhoto: async (uid: string): Promise<void> => {
    await apiClient.delete(`/users/${uid}/photo`)
  },
}
