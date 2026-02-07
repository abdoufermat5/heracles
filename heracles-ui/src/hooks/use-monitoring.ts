import { useQuery } from '@tanstack/react-query'
import { monitoringApi } from '@/lib/api'

export const monitoringKeys = {
  all: ['monitoring'] as const,
  health: () => [...monitoringKeys.all, 'health'] as const,
  stats: () => [...monitoringKeys.all, 'stats'] as const,
}

export function useHealth() {
  return useQuery({
    queryKey: monitoringKeys.health(),
    queryFn: () => monitoringApi.health(),
    refetchInterval: 60_000,
  })
}

export function useStats() {
  return useQuery({
    queryKey: monitoringKeys.stats(),
    queryFn: () => monitoringApi.stats(),
  })
}
