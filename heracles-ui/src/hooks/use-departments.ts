import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { departmentsApi } from '@/lib/api'
import { useDepartmentStore } from '@/stores'
import type { DepartmentCreateData, DepartmentUpdateData, DepartmentListParams } from '@/types'
import { useMutationErrorHandler, commonErrorMessages } from './use-mutation-error-handler'

export const departmentKeys = {
  all: ['departments'] as const,
  tree: () => [...departmentKeys.all, 'tree'] as const,
  lists: () => [...departmentKeys.all, 'list'] as const,
  list: (params?: DepartmentListParams) => [...departmentKeys.lists(), params] as const,
  details: () => [...departmentKeys.all, 'detail'] as const,
  detail: (dn: string) => [...departmentKeys.details(), dn] as const,
}

/**
 * Fetch the full department tree
 * Cached for 5 minutes
 */
export function useDepartmentTree() {
  const setTree = useDepartmentStore((state) => state.setTree)

  return useQuery({
    queryKey: departmentKeys.tree(),
    queryFn: async () => {
      const response = await departmentsApi.getTree()
      setTree(response.tree)
      return response
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * List departments with optional filtering
 */
export function useDepartments(params?: DepartmentListParams) {
  return useQuery({
    queryKey: departmentKeys.list(params),
    queryFn: () => departmentsApi.list(params),
  })
}

/**
 * Get a single department by DN
 */
export function useDepartment(dn: string) {
  return useQuery({
    queryKey: departmentKeys.detail(dn),
    queryFn: () => departmentsApi.get(dn),
    enabled: !!dn,
  })
}

/**
 * Create a new department
 */
export function useCreateDepartment() {
  const queryClient = useQueryClient()
  const handleError = useMutationErrorHandler({
    messages: commonErrorMessages.create,
  })

  return useMutation({
    mutationFn: (data: DepartmentCreateData) => departmentsApi.create(data),
    onSuccess: () => {
      // Invalidate tree and lists
      queryClient.invalidateQueries({ queryKey: departmentKeys.tree() })
      queryClient.invalidateQueries({ queryKey: departmentKeys.lists() })
    },
    onError: handleError,
  })
}

/**
 * Update a department
 */
export function useUpdateDepartment(dn: string) {
  const queryClient = useQueryClient()
  const handleError = useMutationErrorHandler({
    messages: commonErrorMessages.update,
  })

  return useMutation({
    mutationFn: (data: DepartmentUpdateData) => departmentsApi.update(dn, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: departmentKeys.detail(dn) })
      queryClient.invalidateQueries({ queryKey: departmentKeys.tree() })
      queryClient.invalidateQueries({ queryKey: departmentKeys.lists() })
    },
    onError: handleError,
  })
}

/**
 * Delete a department
 */
export function useDeleteDepartment() {
  const queryClient = useQueryClient()
  const handleError = useMutationErrorHandler({
    messages: commonErrorMessages.delete,
  })

  return useMutation({
    mutationFn: ({ dn, recursive }: { dn: string; recursive?: boolean }) =>
      departmentsApi.delete(dn, recursive),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: departmentKeys.tree() })
      queryClient.invalidateQueries({ queryKey: departmentKeys.lists() })
    },
    onError: handleError,
  })
}
