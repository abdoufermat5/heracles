/**
 * Plugin Store
 * ============
 *
 * Zustand store for managing plugin enabled/disabled state.
 * This centralizes plugin configuration state to avoid repeated API calls
 * and ensures consistent plugin visibility across the UI.
 */

import { create } from 'zustand'
import { configApi } from '@/lib/api/config'
import type { PluginConfig } from '@/types/config'

/**
 * Plugin name constants for type safety
 */
export const PLUGIN_NAMES = {
  POSIX: 'posix',
  SSH: 'ssh',
  MAIL: 'mail',
  SUDO: 'sudo',
  SYSTEMS: 'systems',
  DNS: 'dns',
  DHCP: 'dhcp',
} as const

export type PluginName = (typeof PLUGIN_NAMES)[keyof typeof PLUGIN_NAMES]

interface PluginState {
  /** All plugin configurations from API */
  plugins: PluginConfig[]
  /** Loading state */
  isLoading: boolean
  /** Error state */
  error: string | null
  /** Whether initial fetch has completed */
  isInitialized: boolean

  // Actions
  /** Fetch all plugin configs from API (force=true to bypass loading check) */
  fetchPlugins: (force?: boolean) => Promise<void>
  /** Check if a specific plugin is enabled */
  isPluginEnabled: (name: string) => boolean
  /** Get plugin config by name */
  getPlugin: (name: string) => PluginConfig | undefined
  /** Update a single plugin in the store (from API response) */
  updatePlugin: (plugin: PluginConfig) => void
  /** Update local state when a plugin is toggled (called after mutation success) */
  setPluginEnabled: (name: string, enabled: boolean) => void
  /** Clear error state */
  clearError: () => void
}

export const usePluginStore = create<PluginState>((set, get) => ({
  plugins: [],
  isLoading: false,
  error: null,
  isInitialized: false,

  fetchPlugins: async (force = false) => {
    // Skip if already loading (unless forced)
    if (get().isLoading && !force) return

    set({ isLoading: true, error: null })
    try {
      const plugins = await configApi.getPluginConfigs()
      set({ plugins: plugins || [], isLoading: false, isInitialized: true })
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch plugin configs',
        isLoading: false,
        isInitialized: true, // Mark as initialized even on error to prevent infinite retries
      })
    }
  },

  isPluginEnabled: (name: string) => {
    const plugins = get().plugins
    // Guard against undefined plugins (shouldn't happen but defensive)
    if (!plugins) return true
    const plugin = plugins.find((p) => p.name === name)
    // Default to true if plugin not found (graceful degradation)
    // This ensures features work even if config API fails
    return plugin?.enabled ?? true
  },

  getPlugin: (name: string) => {
    const plugins = get().plugins
    if (!plugins) return undefined
    return plugins.find((p) => p.name === name)
  },

  updatePlugin: (plugin: PluginConfig) => {
    set((state) => {
      const plugins = state.plugins || []
      const existingIndex = plugins.findIndex((p) => p.name === plugin.name)
      if (existingIndex >= 0) {
        // Replace existing plugin with updated data
        const updatedPlugins = [...plugins]
        updatedPlugins[existingIndex] = plugin
        return { plugins: updatedPlugins }
      } else {
        // Add new plugin
        return { plugins: [...plugins, plugin] }
      }
    })
  },

  setPluginEnabled: (name: string, enabled: boolean) => {
    set((state) => ({
      plugins: (state.plugins || []).map((p) =>
        p.name === name ? { ...p, enabled } : p
      ),
    }))
  },

  clearError: () => set({ error: null }),
}))

/**
 * Hook to initialize plugin store on app load.
 * Call this once in App.tsx or a top-level provider.
 */
export function useInitializePlugins() {
  const { fetchPlugins, isInitialized, isLoading } = usePluginStore()

  // Fetch plugins on first render if not already initialized
  if (!isInitialized && !isLoading) {
    fetchPlugins()
  }
}
