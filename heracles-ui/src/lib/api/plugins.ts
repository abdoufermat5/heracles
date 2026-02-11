import { apiClient } from '../api-client'

export interface PluginTabInfo {
  id: string
  label: string
  icon: string
  required: boolean
  pluginName: string | null
}

export interface PluginTabsResponse {
  tabs: PluginTabInfo[]
  total: number
}

export const pluginsApi = {
  getTabs: async (objectType: string): Promise<PluginTabsResponse> => {
    return apiClient.get<PluginTabsResponse>(`/tabs/${objectType}`)
  },
}
