import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { usersApi } from '@/lib/api'
import type { UserCreateData, UserUpdateData, SetPasswordData, PaginationParams } from '@/types'

export const userKeys = {
  all: ['users'] as const,
  lists: () => [...userKeys.all, 'list'] as const,
  list: (params?: PaginationParams) => [...userKeys.lists(), params] as const,
  details: () => [...userKeys.all, 'detail'] as const,
  detail: (uid: string) => [...userKeys.details(), uid] as const,
  groups: (uid: string) => [...userKeys.detail(uid), 'groups'] as const,
}

export function useUsers(params?: PaginationParams) {
  return useQuery({
    queryKey: userKeys.list(params),
    queryFn: () => usersApi.list(params),
  })
}

export function useUser(uid: string) {
  return useQuery({
    queryKey: userKeys.detail(uid),
    queryFn: () => usersApi.get(uid),
    enabled: !!uid,
  })
}

export function useUserGroups(uid: string) {
  return useQuery({
    queryKey: userKeys.groups(uid),
    queryFn: () => usersApi.getGroups(uid),
    enabled: !!uid,
    retry: false, // Don't retry if endpoint doesn't exist
  })
}

export function useCreateUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: UserCreateData) => usersApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userKeys.lists() })
    },
  })
}

export function useUpdateUser(uid: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: UserUpdateData) => usersApi.update(uid, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userKeys.detail(uid) })
      queryClient.invalidateQueries({ queryKey: userKeys.lists() })
    },
  })
}

export function useDeleteUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (uid: string) => usersApi.delete(uid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userKeys.lists() })
    },
  })
}

export function useSetUserPassword(uid: string) {
  return useMutation({
    mutationFn: (data: SetPasswordData) => usersApi.setPassword(uid, data),
  })
}
