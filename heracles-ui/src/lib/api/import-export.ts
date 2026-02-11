import { apiClient } from '../api-client'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ObjectType = 'user' | 'group' | 'custom'
export type ExportFormat = 'csv' | 'ldif'
export type CsvSeparator = ',' | ';' | '\t'

export interface ImportValidationError {
  row: number
  field: string
  message: string
}

export interface ImportPreviewRow {
  row: number
  attributes: Record<string, string>
  valid: boolean
  errors: string[]
}

export interface ImportPreviewResponse {
  headers: string[]
  rows: ImportPreviewRow[]
  total_rows: number
  valid_rows: number
  invalid_rows: number
}

export interface ImportResultResponse {
  total_rows: number
  created: number
  updated: number
  skipped: number
  errors: ImportValidationError[]
}

export interface LdifImportResultResponse {
  total_entries: number
  created: number
  updated: number
  skipped: number
  errors: ImportValidationError[]
}

export interface ColumnMapping {
  csv_column: string
  ldap_attribute: string
}

export interface FixedValue {
  attribute: string
  value: string
}

export interface CsvImportConfig {
  object_type?: ObjectType
  separator?: CsvSeparator
  template_id?: string
  column_mapping?: ColumnMapping[]
  fixed_values?: FixedValue[]
  default_password?: string
  department_dn?: string
  object_classes?: string[]
  rdn_attribute?: string
}

export interface ExportRequest {
  format: ExportFormat
  object_type?: ObjectType | null
  fields?: string[]
  department_dn?: string
  filter?: string
  ldif_wrap?: number
}

export interface PluginFieldInfo {
  name: string
  label: string
  required: boolean
  description: string | null
  plugin_name: string
}

export interface PluginFieldGroup {
  plugin_name: string
  plugin_label: string
  fields: PluginFieldInfo[]
}

export interface AvailableFieldsResponse {
  object_type: string
  required_fields: string[]
  optional_fields: string[]
  all_fields: string[]
  plugin_fields: PluginFieldGroup[]
}

export interface ImportTemplateInfo {
  id: string
  name: string
  description?: string
  department_dn?: string
}

export interface ImportTemplateListResponse {
  templates: ImportTemplateInfo[]
}

// ---------------------------------------------------------------------------
// API Client
// ---------------------------------------------------------------------------

function getCsrfToken(): string {
  const match = document.cookie.match(/(?:^|; )csrf_token=([^;]+)/)
  return match ? decodeURIComponent(match[1]) : ''
}

export const importExportApi = {
  // ---- Metadata ----

  getAvailableFields: async (objectType: ObjectType): Promise<AvailableFieldsResponse> => {
    return apiClient.get<AvailableFieldsResponse>(`/import-export/fields/${objectType}`)
  },

  getTemplates: async (departmentDn?: string): Promise<ImportTemplateListResponse> => {
    const params = new URLSearchParams()
    if (departmentDn) params.set('departmentDn', departmentDn)
    const qs = params.toString()
    return apiClient.get<ImportTemplateListResponse>(`/import-export/templates${qs ? `?${qs}` : ''}`)
  },

  // ---- CSV Import ----

  previewImport: async (
    file: File,
    separator: CsvSeparator = ',',
    objectType: ObjectType = 'user',
  ): Promise<ImportPreviewResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('separator', separator)
    formData.append('object_type', objectType)
    return apiClient.upload<ImportPreviewResponse>('/import-export/import/preview', formData)
  },

  importCsv: async (
    file: File,
    config: CsvImportConfig = {},
  ): Promise<ImportResultResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('config', JSON.stringify(config))
    return apiClient.upload<ImportResultResponse>('/import-export/import/csv', formData)
  },

  // Legacy import (backward compat)
  importUsers: async (
    file: File,
    options?: { departmentDn?: string; defaultPassword?: string },
  ): Promise<ImportResultResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    const params = new URLSearchParams()
    if (options?.departmentDn) params.set('departmentDn', options.departmentDn)
    if (options?.defaultPassword) params.set('defaultPassword', options.defaultPassword)
    const qs = params.toString()
    const url = `/import-export/import${qs ? `?${qs}` : ''}`
    return apiClient.upload<ImportResultResponse>(url, formData)
  },

  // ---- LDIF Import ----

  importLdif: async (
    file: File,
    overwrite: boolean = false,
  ): Promise<LdifImportResultResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('overwrite', String(overwrite))
    return apiClient.upload<LdifImportResultResponse>('/import-export/import/ldif', formData)
  },

  // ---- Export ----

  exportEntries: async (request: ExportRequest): Promise<string> => {
    const csrfToken = getCsrfToken()
    const resp = await fetch(`/api/v1/import-export/export`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrfToken,
      },
      credentials: 'include',
      body: JSON.stringify(request),
    })
    if (!resp.ok) throw new Error(`Export failed: ${resp.statusText}`)
    return resp.text()
  },

  // Legacy alias
  exportUsers: async (request: ExportRequest): Promise<string> => {
    return importExportApi.exportEntries(request)
  },
}
