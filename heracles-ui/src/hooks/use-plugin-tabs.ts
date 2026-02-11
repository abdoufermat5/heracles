import { useQuery } from '@tanstack/react-query'
import { pluginsApi } from '@/lib/api/plugins'

export const pluginTabKeys = {
  all: ['plugin-tabs'] as const,
  byType: (objectType: string) => [...pluginTabKeys.all, objectType] as const,
}

/**
 * Fetch the list of available plugin tabs for an object type.
 * Results are cached and shared across components.
 */
export function usePluginTabs(objectType: string) {
  return useQuery({
    queryKey: pluginTabKeys.byType(objectType),
    queryFn: () => pluginsApi.getTabs(objectType),
    staleTime: 1000 * 60 * 10, // tabs rarely change — cache 10 min
  })
}
