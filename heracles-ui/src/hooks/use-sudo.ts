/**
 * Sudo Plugin React Query Hooks
 * 
 * Custom hooks for managing sudo roles with TanStack Query
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { sudoApi } from '@/lib/api/sudo'
import type {
  SudoRoleCreate,
  SudoRoleUpdate,
} from '@/types/sudo'

// ============================================================================
// Query Keys
// ============================================================================

export const sudoQueryKeys = {
  all: ['sudo'] as const,
  roles: () => [...sudoQueryKeys.all, 'roles'] as const,
  roleList: (params?: { page?: number; page_size?: number; search?: string }) =>
    [...sudoQueryKeys.roles(), 'list', params] as const,
  role: (cn: string) => [...sudoQueryKeys.roles(), cn] as const,
  defaults: () => [...sudoQueryKeys.all, 'defaults'] as const,
}

// ============================================================================
// Query Hooks
// ============================================================================

/**
 * Hook for listing sudo roles
 */
export function useSudoRoles(params?: {
  page?: number
  page_size?: number
  search?: string
}) {
  return useQuery({
    queryKey: sudoQueryKeys.roleList(params),
    queryFn: () => sudoApi.listRoles(params),
    staleTime: 30 * 1000, // 30 seconds
    placeholderData: (previousData) => previousData,
  })
}

/**
 * Hook for getting a single sudo role
 */
export function useSudoRole(cn: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: sudoQueryKeys.role(cn),
    queryFn: () => sudoApi.getRole(cn),
    enabled: options?.enabled ?? !!cn,
    staleTime: 30 * 1000,
  })
}

/**
 * Hook for getting sudo defaults
 */
export function useSudoDefaults() {
  return useQuery({
    queryKey: sudoQueryKeys.defaults(),
    queryFn: () => sudoApi.getDefaults(),
    staleTime: 30 * 1000,
  })
}

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * Hook for creating a sudo role
 */
export function useCreateSudoRole() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: SudoRoleCreate) => sudoApi.createRole(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sudoQueryKeys.roles() })
    },
  })
}

/**
 * Hook for updating a sudo role
 */
export function useUpdateSudoRole() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ cn, data }: { cn: string; data: SudoRoleUpdate }) =>
      sudoApi.updateRole(cn, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: sudoQueryKeys.role(variables.cn) })
      queryClient.invalidateQueries({ queryKey: sudoQueryKeys.roles() })
    },
  })
}

/**
 * Hook for deleting a sudo role
 */
export function useDeleteSudoRole() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (cn: string) => sudoApi.deleteRole(cn),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sudoQueryKeys.roles() })
    },
  })
}

/**
 * Hook for updating sudo defaults
 */
export function useUpdateSudoDefaults() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: { sudoOption: string[] }) => sudoApi.updateDefaults(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sudoQueryKeys.defaults() })
    },
  })
}
