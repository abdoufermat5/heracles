import { apiClient } from '../api-client'

export interface HealthServiceStatus {
  status: 'ok' | 'error'
  message?: string
}

export interface HealthResponse {
  status: 'ok' | 'degraded'
  services: {
    ldap?: HealthServiceStatus
    redis?: HealthServiceStatus
    database?: HealthServiceStatus
  }
}

export interface StatsResponse {
  users: number
  groups: number
  roles: number
  departments: number
}

export const monitoringApi = {
  health: async (): Promise<HealthResponse> => {
    return apiClient.get<HealthResponse>('/health')
  },
  stats: async (): Promise<StatsResponse> => {
    return apiClient.get<StatsResponse>('/stats')
  },
}
