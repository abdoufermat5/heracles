import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { groupsApi } from '@/lib/api'
import type { GroupCreateData, GroupUpdateData, PaginationParams } from '@/types'

export const groupKeys = {
  all: ['groups'] as const,
  lists: () => [...groupKeys.all, 'list'] as const,
  list: (params?: PaginationParams) => [...groupKeys.lists(), params] as const,
  details: () => [...groupKeys.all, 'detail'] as const,
  detail: (cn: string) => [...groupKeys.details(), cn] as const,
  members: (cn: string) => [...groupKeys.detail(cn), 'members'] as const,
}

export function useGroups(params?: PaginationParams) {
  return useQuery({
    queryKey: groupKeys.list(params),
    queryFn: () => groupsApi.list(params),
  })
}

export function useGroup(cn: string) {
  return useQuery({
    queryKey: groupKeys.detail(cn),
    queryFn: () => groupsApi.get(cn),
    enabled: !!cn,
  })
}

export function useGroupMembers(cn: string) {
  return useQuery({
    queryKey: groupKeys.members(cn),
    queryFn: () => groupsApi.getMembers(cn),
    enabled: !!cn,
  })
}

export function useCreateGroup() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: GroupCreateData) => groupsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: groupKeys.lists() })
    },
  })
}

export function useUpdateGroup(cn: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: GroupUpdateData) => groupsApi.update(cn, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: groupKeys.detail(cn) })
      queryClient.invalidateQueries({ queryKey: groupKeys.lists() })
    },
  })
}

export function useDeleteGroup() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (cn: string) => groupsApi.delete(cn),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: groupKeys.lists() })
    },
  })
}

export function useAddGroupMember(cn: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (uid: string) => groupsApi.addMember(cn, uid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: groupKeys.members(cn) })
    },
  })
}

export function useRemoveGroupMember(cn: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (uid: string) => groupsApi.removeMember(cn, uid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: groupKeys.members(cn) })
    },
  })
}
