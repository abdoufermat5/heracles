/**
 * Configuration Hooks
 * ===================
 *
 * React Query hooks for the configuration system.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { configApi } from "@/lib/api/config";
import { usePluginStore } from "@/stores";
import type {
  ConfigUpdateRequest,
  ConfigBulkUpdateRequest,
  PluginConfigUpdateRequest,
  PluginConfigUpdateResponse,
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
 * 
 * Returns a response that may include:
 * - requiresConfirmation: true if migration is needed
 * - migrationCheck: details about affected entries
 * - success: true if update was successful
 * - migrations: results of any migrations performed
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
      result: PluginConfigUpdateResponse,
      variables: { name: string; data: PluginConfigUpdateRequest }
    ) => {
      // Only show success toast and invalidate if the update was successful
      // (not when migration confirmation is required)
      if (result.requiresConfirmation) {
        // Don't show toast - the UI will handle showing a confirmation dialog
        return;
      }
      
      // Invalidate plugin and full config
      queryClient.invalidateQueries({
        queryKey: configKeys.plugin(variables.name),
      });
      queryClient.invalidateQueries({ queryKey: configKeys.plugins() });
      queryClient.invalidateQueries({ queryKey: configKeys.all });
      
      const migrationCount = result.migrations?.reduce(
        (sum, m) => sum + m.entriesMigrated, 0
      ) || 0;
      
      if (migrationCount > 0) {
        toast.success(`Plugin "${variables.name}" configuration updated with ${migrationCount} entries migrated`);
      } else {
        toast.success(`Plugin "${variables.name}" configuration updated`);
      }
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
  const fetchPlugins = usePluginStore((state) => state.fetchPlugins);

  return useMutation({
    mutationFn: (name: string) => configApi.enablePlugin(name),
    onSuccess: async (_result: { message: string }, name: string) => {
      // Force refetch all plugins into Zustand store to ensure UI is in sync
      await fetchPlugins(true);
      
      queryClient.invalidateQueries({ queryKey: configKeys.plugin(name) });
      queryClient.invalidateQueries({ queryKey: configKeys.plugins() });
      queryClient.invalidateQueries({ queryKey: configKeys.all });
      
      toast.success(`Plugin "${name}" enabled`);
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
  const fetchPlugins = usePluginStore((state) => state.fetchPlugins);

  return useMutation({
    mutationFn: (name: string) => configApi.disablePlugin(name),
    onSuccess: async (_result: { message: string }, name: string) => {
      // Force refetch all plugins into Zustand store to ensure UI is in sync
      await fetchPlugins(true);
      
      queryClient.invalidateQueries({ queryKey: configKeys.plugin(name) });
      queryClient.invalidateQueries({ queryKey: configKeys.plugins() });
      queryClient.invalidateQueries({ queryKey: configKeys.all });
      
      toast.warning(`Plugin "${name}" disabled`);
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

// =============================================================================
// RDN Migration Hooks
// =============================================================================

/**
 * Hook to check the impact of an RDN change
 */
export function useCheckRdnChange() {
  return useMutation({
    mutationFn: (data: {
      oldRdn: string;
      newRdn: string;
      baseDn?: string;
      objectClassFilter?: string;
    }) => configApi.checkRdnChange(data),
    onError: (error: Error) => {
      toast.error(`Failed to check RDN change: ${error.message}`);
    },
  });
}

/**
 * Hook to migrate entries after RDN change
 */
export function useMigrateRdn() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      oldRdn: string;
      newRdn: string;
      baseDn?: string;
      mode: "modrdn" | "copy_delete" | "leave_orphaned";
      objectClassFilter?: string;
      confirmed: boolean;
    }) => configApi.migrateRdn(data),
    onSuccess: (result) => {
      // Invalidate relevant queries
      queryClient.invalidateQueries({ queryKey: ["users"] });
      queryClient.invalidateQueries({ queryKey: ["groups"] });
      queryClient.invalidateQueries({ queryKey: configKeys.all });

      if (result.success) {
        toast.success(
          `Migration completed: ${result.entriesMigrated} entries moved successfully`
        );
      } else {
        toast.warning(
          `Migration completed with issues: ${result.entriesFailed} entries failed`
        );
      }
    },
    onError: (error: Error) => {
      toast.error(`Migration failed: ${error.message}`);
    },
  });
}

/**
 * Hook to update a setting with RDN migration support
 */
export function useUpdateSettingWithMigration() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      category,
      key,
      data,
    }: {
      category: string;
      key: string;
      data: {
        value: unknown;
        reason?: string;
        confirmed: boolean;
        migrateEntries: boolean;
      };
    }) => configApi.updateSettingWithMigration(category, key, data),
    onSuccess: (result, variables) => {
      if (result.success) {
        // Invalidate queries
        queryClient.invalidateQueries({
          queryKey: configKeys.category(variables.category),
        });
        queryClient.invalidateQueries({ queryKey: configKeys.all });

        // Show appropriate message
        if (result.migrationResult) {
          toast.success(
            `Setting updated. ${result.migrationResult.entriesMigrated} entries migrated.`
          );
        } else {
          toast.success(result.message);
        }
      }
      // Note: requiresConfirmation case is handled by the calling component
    },
    onError: (error: Error) => {
      toast.error(`Failed to update setting: ${error.message}`);
    },
  });
}

