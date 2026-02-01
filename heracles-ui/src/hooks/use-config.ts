/**
 * Configuration Hooks
 * ===================
 *
 * React Query hooks for the configuration system.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { configApi } from "@/lib/api/config";
import type {
  ConfigUpdateRequest,
  ConfigBulkUpdateRequest,
  PluginConfigUpdateRequest,
  ConfigHistoryParams,
  ConfigUpdateResult,
  PluginConfig,
  ConfigSetting,
} from "@/types/config";
import { toast } from "sonner";

// Query keys
export const configKeys = {
  all: ["config"] as const,
  categories: () => [...configKeys.all, "categories"] as const,
  category: (name: string) => [...configKeys.categories(), name] as const,
  plugins: () => [...configKeys.all, "plugins"] as const,
  plugin: (name: string) => [...configKeys.plugins(), name] as const,
  history: (params?: ConfigHistoryParams) =>
    [...configKeys.all, "history", params] as const,
};

/**
 * Hook to fetch all configuration (categories + plugins)
 */
export function useConfig() {
  return useQuery({
    queryKey: configKeys.all,
    queryFn: configApi.getAll,
  });
}

/**
 * Hook to fetch all configuration categories
 */
export function useConfigCategories() {
  return useQuery({
    queryKey: configKeys.categories(),
    queryFn: configApi.getCategories,
  });
}

/**
 * Hook to fetch a specific category with settings
 */
export function useConfigCategory(name: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: configKeys.category(name),
    queryFn: () => configApi.getCategory(name),
    enabled: options?.enabled ?? !!name,
  });
}

/**
 * Hook to update a single setting
 */
export function useUpdateSetting() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      category,
      key,
      data,
    }: {
      category: string;
      key: string;
      data: ConfigUpdateRequest;
    }) => configApi.updateSetting(category, key, data),
    onSuccess: (
      _result: ConfigSetting,
      variables: { category: string; key: string; data: ConfigUpdateRequest }
    ) => {
      // Invalidate category and full config
      queryClient.invalidateQueries({
        queryKey: configKeys.category(variables.category),
      });
      queryClient.invalidateQueries({ queryKey: configKeys.all });
      
      toast.success("Setting updated successfully");
    },
    onError: (error: Error) => {
      toast.error(`Failed to update setting: ${error.message}`);
    },
  });
}

/**
 * Hook to bulk update multiple settings
 */
export function useBulkUpdateSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ConfigBulkUpdateRequest) => configApi.bulkUpdateSettings(data),
    onSuccess: (result: ConfigUpdateResult) => {
      // Invalidate all config queries
      queryClient.invalidateQueries({ queryKey: configKeys.all });
      
      if (result.requiresRestart) {
        toast.warning("Settings saved. Some changes require a restart to take effect.");
      } else {
        toast.success("Settings saved successfully");
      }
    },
    onError: (error: Error) => {
      toast.error(`Failed to save settings: ${error.message}`);
    },
  });
}

/**
 * Hook to fetch all plugin configurations
 */
export function usePluginConfigs() {
  return useQuery({
    queryKey: configKeys.plugins(),
    queryFn: configApi.getPluginConfigs,
  });
}

/**
 * Hook to fetch a specific plugin's configuration
 */
export function usePluginConfig(name: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: configKeys.plugin(name),
    queryFn: () => configApi.getPluginConfig(name),
    enabled: options?.enabled ?? !!name,
  });
}

/**
 * Hook to update a plugin's configuration
 */
export function useUpdatePluginConfig() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      name,
      data,
    }: {
      name: string;
      data: PluginConfigUpdateRequest;
    }) => configApi.updatePluginConfig(name, data),
    onSuccess: (
      result: PluginConfig,
      variables: { name: string; data: PluginConfigUpdateRequest }
    ) => {
      // Invalidate plugin and full config
      queryClient.invalidateQueries({
        queryKey: configKeys.plugin(variables.name),
      });
      queryClient.invalidateQueries({ queryKey: configKeys.plugins() });
      queryClient.invalidateQueries({ queryKey: configKeys.all });
      
      toast.success(`Plugin "${result.displayName}" configuration updated`);
    },
    onError: (error: Error) => {
      toast.error(`Failed to update plugin configuration: ${error.message}`);
    },
  });
}

/**
 * Hook to enable a plugin
 */
export function useEnablePlugin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (name: string) => configApi.enablePlugin(name),
    onSuccess: (result: PluginConfig, name: string) => {
      queryClient.invalidateQueries({ queryKey: configKeys.plugin(name) });
      queryClient.invalidateQueries({ queryKey: configKeys.plugins() });
      queryClient.invalidateQueries({ queryKey: configKeys.all });
      
      toast.success(`Plugin "${result.displayName}" enabled`);
    },
    onError: (error: Error) => {
      toast.error(`Failed to enable plugin: ${error.message}`);
    },
  });
}

/**
 * Hook to disable a plugin
 */
export function useDisablePlugin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (name: string) => configApi.disablePlugin(name),
    onSuccess: (result: PluginConfig, name: string) => {
      queryClient.invalidateQueries({ queryKey: configKeys.plugin(name) });
      queryClient.invalidateQueries({ queryKey: configKeys.plugins() });
      queryClient.invalidateQueries({ queryKey: configKeys.all });
      
      toast.warning(`Plugin "${result.displayName}" disabled`);
    },
    onError: (error: Error) => {
      toast.error(`Failed to disable plugin: ${error.message}`);
    },
  });
}

/**
 * Hook to toggle plugin enabled state
 */
export function useTogglePlugin() {
  const enableMutation = useEnablePlugin();
  const disableMutation = useDisablePlugin();

  return {
    mutate: (name: string, enabled: boolean) => {
      if (enabled) {
        enableMutation.mutate(name);
      } else {
        disableMutation.mutate(name);
      }
    },
    isPending: enableMutation.isPending || disableMutation.isPending,
  };
}

/**
 * Hook to fetch configuration history
 */
export function useConfigHistory(params?: ConfigHistoryParams) {
  return useQuery({
    queryKey: configKeys.history(params),
    queryFn: () => configApi.getHistory(params),
  });
}
