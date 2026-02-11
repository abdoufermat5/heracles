import { apiClient } from '../api-client'

export interface TemplateResponse {
  id: string
  name: string
  description: string | null
  defaults: Record<string, unknown>
  pluginActivations: Record<string, Record<string, unknown>> | null
  variables: Record<string, { default?: string; description?: string }> | null
  department_dn: string | null
  display_order: number
  created_by: string | null
  created_at: string
  updated_at: string
}

export interface TemplateListResponse {
  templates: TemplateResponse[]
  total: number
}

export interface TemplateCreate {
  name: string
  description?: string
  defaults: Record<string, unknown>
  pluginActivations?: Record<string, Record<string, unknown>>
  variables?: Record<string, { default?: string; description?: string }>
  departmentDn?: string
  displayOrder?: number
}

export interface TemplateUpdate {
  name?: string
  description?: string
  defaults?: Record<string, unknown>
  pluginActivations?: Record<string, Record<string, unknown>>
  variables?: Record<string, { default?: string; description?: string }>
  departmentDn?: string
  displayOrder?: number
}

export interface TemplatePreview {
  template_id: string
  template_name: string
  resolved_defaults: Record<string, unknown>
  missing_variables: string[]
}

export interface PluginTemplateFieldDef {
  key: string
  label: string
  fieldType: string
  defaultValue: unknown
  options: string[] | null
  description: string | null
}

export interface PluginTemplateSection {
  label: string
  icon: string | null
  objectClasses: string[]
  fields: PluginTemplateFieldDef[]
}

export type PluginTemplateFields = Record<string, PluginTemplateSection>

type ApiParams = Record<string, string | number | undefined>

export const templatesApi = {
  list: async (departmentDn?: string): Promise<TemplateListResponse> => {
    const params: ApiParams = {}
    if (departmentDn) params.departmentDn = departmentDn
    return apiClient.get<TemplateListResponse>('/templates', params)
  },

  get: async (id: string): Promise<TemplateResponse> => {
    return apiClient.get<TemplateResponse>(`/templates/${id}`)
  },

  create: async (data: TemplateCreate): Promise<TemplateResponse> => {
    return apiClient.post<TemplateResponse>('/templates', data)
  },

  update: async (id: string, data: TemplateUpdate): Promise<TemplateResponse> => {
    return apiClient.put<TemplateResponse>(`/templates/${id}`, data)
  },

  delete: async (id: string): Promise<void> => {
    return apiClient.delete(`/templates/${id}`)
  },

  preview: async (id: string, values: Record<string, string>): Promise<TemplatePreview> => {
    return apiClient.post<TemplatePreview>(`/templates/${id}/preview`, values)
  },

  pluginFields: async (objectType: string = 'user'): Promise<PluginTemplateFields> => {
    return apiClient.get<PluginTemplateFields>('/templates/plugin-fields', { object_type: objectType })
  },
}
