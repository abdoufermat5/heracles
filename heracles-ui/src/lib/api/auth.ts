import { apiClient } from '../api-client'
import { TOKEN_STORAGE_KEY, REFRESH_TOKEN_KEY } from '@/config/constants'
import type { TokenResponse, UserInfo, LoginCredentials, PasswordChangeData } from '@/types'

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<TokenResponse> => {
    const response = await apiClient.post<TokenResponse>('/auth/login', credentials)
    localStorage.setItem(TOKEN_STORAGE_KEY, response.access_token)
    localStorage.setItem(REFRESH_TOKEN_KEY, response.refresh_token)
    return response
  },

  logout: async (): Promise<void> => {
    try {
      await apiClient.post('/auth/logout')
    } finally {
      apiClient.clearTokens()
    }
  },

  logoutAll: async (): Promise<void> => {
    try {
      await apiClient.post('/auth/logout-all')
    } finally {
      apiClient.clearTokens()
    }
  },

  refresh: async (refreshToken: string): Promise<TokenResponse> => {
    return apiClient.post<TokenResponse>('/auth/refresh', { refresh_token: refreshToken })
  },

  getCurrentUser: async (): Promise<UserInfo> => {
    return apiClient.get<UserInfo>('/auth/me')
  },

  changePassword: async (data: PasswordChangeData): Promise<void> => {
    await apiClient.post('/auth/password/change', data)
  },

  requestPasswordReset: async (email: string): Promise<void> => {
    await apiClient.post('/auth/password/reset/request', { email })
  },
}
