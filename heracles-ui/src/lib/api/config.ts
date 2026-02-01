/**
 * Configuration API Client
 * ========================
 *
 * API client functions for the configuration endpoints.
 */

import { apiClient } from "../api-client";
import type {
  GlobalConfigResponse,
  ConfigCategory,
  ConfigCategoriesResponse,
  ConfigSetting,
  ConfigUpdateRequest,
  ConfigBulkUpdateRequest,
  PluginConfig,
  PluginConfigUpdateRequest,
  ConfigHistoryParams,
  ConfigHistoryResponse,
  ConfigUpdateResult,
} from "@/types/config";

const CONFIG_BASE = "/config";

export const configApi = {
  /**
   * Fetch all configuration (categories + plugins)
   */
  getAll: async (): Promise<GlobalConfigResponse> => {
    return apiClient.get<GlobalConfigResponse>(CONFIG_BASE);
  },

  /**
   * Fetch all configuration categories
   */
  getCategories: async (): Promise<ConfigCategory[]> => {
    const response = await apiClient.get<ConfigCategoriesResponse>(
      `${CONFIG_BASE}/categories`
    );
    return response.categories;
  },

  /**
   * Fetch a specific category with its settings
   */
  getCategory: async (name: string): Promise<ConfigCategory> => {
    return apiClient.get<ConfigCategory>(`${CONFIG_BASE}/categories/${name}`);
  },

  /**
   * Update a single setting
   */
  updateSetting: async (
    category: string,
    key: string,
    data: ConfigUpdateRequest
  ): Promise<ConfigSetting> => {
    return apiClient.patch<ConfigSetting>(
      `${CONFIG_BASE}/settings/${category}/${key}`,
      data
    );
  },

  /**
   * Bulk update multiple settings
   */
  bulkUpdateSettings: async (
    data: ConfigBulkUpdateRequest
  ): Promise<ConfigUpdateResult> => {
    return apiClient.put<ConfigUpdateResult>(`${CONFIG_BASE}/settings`, data);
  },

  /**
   * Fetch all plugin configurations
   */
  getPluginConfigs: async (): Promise<PluginConfig[]> => {
    const response = await apiClient.get<{ plugins: PluginConfig[] }>(
      `${CONFIG_BASE}/plugins`
    );
    return response.plugins;
  },

  /**
   * Fetch a specific plugin's configuration
   */
  getPluginConfig: async (name: string): Promise<PluginConfig> => {
    return apiClient.get<PluginConfig>(`${CONFIG_BASE}/plugins/${name}`);
  },

  /**
   * Update a plugin's configuration
   */
  updatePluginConfig: async (
    name: string,
    data: PluginConfigUpdateRequest
  ): Promise<PluginConfig> => {
    return apiClient.patch<PluginConfig>(
      `${CONFIG_BASE}/plugins/${name}`,
      data
    );
  },

  /**
   * Enable a plugin
   */
  enablePlugin: async (name: string): Promise<PluginConfig> => {
    return apiClient.post<PluginConfig>(
      `${CONFIG_BASE}/plugins/${name}/enable`
    );
  },

  /**
   * Disable a plugin
   */
  disablePlugin: async (name: string): Promise<PluginConfig> => {
    return apiClient.post<PluginConfig>(
      `${CONFIG_BASE}/plugins/${name}/disable`
    );
  },

  /**
   * Fetch configuration change history
   */
  getHistory: async (
    params?: ConfigHistoryParams
  ): Promise<ConfigHistoryResponse> => {
    const queryParams: Record<string, string> = {};

    if (params?.entityType) {
      queryParams.entity_type = params.entityType;
    }
    if (params?.entityId) {
      queryParams.entity_id = params.entityId;
    }
    if (params?.limit) {
      queryParams.limit = params.limit.toString();
    }
    if (params?.offset) {
      queryParams.offset = params.offset.toString();
    }

    return apiClient.get<ConfigHistoryResponse>(
      `${CONFIG_BASE}/history`,
      Object.keys(queryParams).length > 0 ? queryParams : undefined
    );
  },
};
