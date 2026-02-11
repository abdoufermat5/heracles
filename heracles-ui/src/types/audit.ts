/**
 * Audit Log Types
 * ================
 * Types for the general-purpose audit log system.
 */

export interface GeneralAuditEntry {
  id: number
  timestamp: string
  actor_dn: string
  actor_name: string | null
  action: string
  entity_type: string
  entity_id: string | null
  entity_name: string | null
  changes: Record<string, unknown> | null
  department_dn: string | null
  ip_address: string | null
  status: string
  error_message: string | null
}

export interface GeneralAuditListResponse {
  entries: GeneralAuditEntry[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export interface GeneralAuditFilters {
  page?: number
  page_size?: number
  actor_dn?: string
  action?: string
  entity_type?: string
  entity_id?: string
  department_dn?: string
  status?: string
  from_ts?: string
  to_ts?: string
  search?: string
}
