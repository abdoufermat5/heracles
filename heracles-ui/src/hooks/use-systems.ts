/**
 * Systems Plugin React Query Hooks
 *
 * Custom hooks for managing systems with TanStack Query
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { systemsApi } from '@/lib/api/systems'
import type {
  SystemCreate,
  SystemUpdate,
  SystemType,
  HostValidationRequest,
} from '@/types/systems'

// ============================================================================
// Query Keys
// ============================================================================

export const systemsQueryKeys = {
  all: ['systems'] as const,
  lists: () => [...systemsQueryKeys.all, 'list'] as const,
  list: (params?: {
    system_type?: SystemType
    page?: number
    page_size?: number
    search?: string
  }) => [...systemsQueryKeys.lists(), params] as const,
  details: () => [...systemsQueryKeys.all, 'detail'] as const,
  detail: (systemType: SystemType, cn: string) =>
    [...systemsQueryKeys.details(), systemType, cn] as const,
  hostnames: () => [...systemsQueryKeys.all, 'hostnames'] as const,
}

// ============================================================================
// Query Hooks
// ============================================================================

/**
 * Hook for listing systems
 */
export function useSystems(params?: {
  system_type?: SystemType
  page?: number
  page_size?: number
  search?: string
}) {
  return useQuery({
    queryKey: systemsQueryKeys.list(params),
    queryFn: () => systemsApi.list(params),
    staleTime: 30 * 1000, // 30 seconds
    placeholderData: (previousData) => previousData,
  })
}

/**
 * Hook for getting a single system
 */
export function useSystem(
  systemType: SystemType,
  cn: string,
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: systemsQueryKeys.detail(systemType, cn),
    queryFn: () => systemsApi.get(systemType, cn),
    enabled: options?.enabled ?? (!!systemType && !!cn),
    staleTime: 30 * 1000,
  })
}

/**
 * Hook for getting all hostnames
 */
export function useHostnames() {
  return useQuery({
    queryKey: systemsQueryKeys.hostnames(),
    queryFn: () => systemsApi.getAllHostnames(),
    staleTime: 60 * 1000, // 1 minute
  })
}

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * Hook for creating a system
 */
export function useCreateSystem() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: SystemCreate) => systemsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: systemsQueryKeys.lists() })
      queryClient.invalidateQueries({ queryKey: systemsQueryKeys.hostnames() })
    },
  })
}

/**
 * Hook for updating a system
 */
export function useUpdateSystem() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      systemType,
      cn,
      data,
    }: {
      systemType: SystemType
      cn: string
      data: SystemUpdate
    }) => systemsApi.update(systemType, cn, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: systemsQueryKeys.detail(variables.systemType, variables.cn),
      })
      queryClient.invalidateQueries({ queryKey: systemsQueryKeys.lists() })
    },
  })
}

/**
 * Hook for deleting a system
 */
export function useDeleteSystem() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ systemType, cn }: { systemType: SystemType; cn: string }) =>
      systemsApi.delete(systemType, cn),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: systemsQueryKeys.lists() })
      queryClient.invalidateQueries({ queryKey: systemsQueryKeys.hostnames() })
    },
  })
}

/**
 * Hook for validating hosts
 */
export function useValidateHosts() {
  return useMutation({
    mutationFn: (request: HostValidationRequest) =>
      systemsApi.validateHosts(request),
  })
}

// ============================================================================
// Convenience Hooks by Type
// ============================================================================

export function useServers(params?: {
  page?: number
  page_size?: number
  search?: string
}) {
  return useSystems({ ...params, system_type: 'server' })
}

export function useWorkstations(params?: {
  page?: number
  page_size?: number
  search?: string
}) {
  return useSystems({ ...params, system_type: 'workstation' })
}

export function useTerminals(params?: {
  page?: number
  page_size?: number
  search?: string
}) {
  return useSystems({ ...params, system_type: 'terminal' })
}

export function usePrinters(params?: {
  page?: number
  page_size?: number
  search?: string
}) {
  return useSystems({ ...params, system_type: 'printer' })
}

export function useComponents(params?: {
  page?: number
  page_size?: number
  search?: string
}) {
  return useSystems({ ...params, system_type: 'component' })
}

export function usePhones(params?: {
  page?: number
  page_size?: number
  search?: string
}) {
  return useSystems({ ...params, system_type: 'phone' })
}

export function useMobiles(params?: {
  page?: number
  page_size?: number
  search?: string
}) {
  return useSystems({ ...params, system_type: 'mobile' })
}
