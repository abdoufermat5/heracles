import { apiClient } from '../api-client'
import type {
  GeneralAuditListResponse,
  GeneralAuditFilters,
} from '@/types/audit'

type ApiParams = Record<string, string | number | undefined>

export const auditApi = {
  listLogs: async (filters?: GeneralAuditFilters): Promise<GeneralAuditListResponse> => {
    const params: ApiParams = {}
    if (filters) {
      if (filters.page) params.page = filters.page
      if (filters.page_size) params.pageSize = filters.page_size
      if (filters.actor_dn) params.actorDn = filters.actor_dn
      if (filters.action) params.action = filters.action
      if (filters.entity_type) params.entityType = filters.entity_type
      if (filters.entity_id) params.entityId = filters.entity_id
      if (filters.department_dn) params.departmentDn = filters.department_dn
      if (filters.status) params.status = filters.status
      if (filters.from_ts) params.fromTs = filters.from_ts
      if (filters.to_ts) params.toTs = filters.to_ts
      if (filters.search) params.search = filters.search
    }
    return apiClient.get<GeneralAuditListResponse>('/audit/logs', params)
  },

  getEntityHistory: async (
    entityType: string,
    entityId: string,
    limit = 50,
  ): Promise<{ entries: GeneralAuditListResponse['entries'] }> => {
    return apiClient.get(`/audit/logs/${entityType}/${encodeURIComponent(entityId)}`, { limit })
  },
}
