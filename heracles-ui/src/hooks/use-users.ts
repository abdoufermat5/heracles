import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { usersApi } from '@/lib/api'
import type { UserCreateData, UserUpdateData, SetPasswordData, PaginationParams } from '@/types'
import { useMutationErrorHandler, commonErrorMessages } from './use-mutation-error-handler'

export const userKeys = {
  all: ['users'] as const,
  lists: () => [...userKeys.all, 'list'] as const,
  list: (params?: PaginationParams) => [...userKeys.lists(), params] as const,
  details: () => [...userKeys.all, 'detail'] as const,
  detail: (uid: string) => [...userKeys.details(), uid] as const,
  groups: (uid: string) => [...userKeys.detail(uid), 'groups'] as const,
  lockStatus: (uid: string) => [...userKeys.detail(uid), 'lock'] as const,
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

export function useUserLockStatus(uid: string) {
  return useQuery({
    queryKey: userKeys.lockStatus(uid),
    queryFn: () => usersApi.getLockStatus(uid),
    enabled: !!uid,
  })
}

export function useLockUser(uid: string) {
  const queryClient = useQueryClient()
  const handleError = useMutationErrorHandler()

  return useMutation({
    mutationFn: () => usersApi.lock(uid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userKeys.lockStatus(uid) })
      queryClient.invalidateQueries({ queryKey: userKeys.detail(uid) })
    },
    onError: handleError,
  })
}

export function useUnlockUser(uid: string) {
  const queryClient = useQueryClient()
  const handleError = useMutationErrorHandler()

  return useMutation({
    mutationFn: () => usersApi.unlock(uid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userKeys.lockStatus(uid) })
      queryClient.invalidateQueries({ queryKey: userKeys.detail(uid) })
    },
    onError: handleError,
  })
}

export function useCreateUser() {
  const queryClient = useQueryClient()
  const handleError = useMutationErrorHandler({
    messages: commonErrorMessages.create,
  })

  return useMutation({
    mutationFn: (data: UserCreateData) => usersApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userKeys.lists() })
    },
    onError: handleError,
  })
}

export function useUpdateUser(uid: string) {
  const queryClient = useQueryClient()
  const handleError = useMutationErrorHandler({
    messages: commonErrorMessages.update,
  })

  return useMutation({
    mutationFn: (data: UserUpdateData) => usersApi.update(uid, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userKeys.detail(uid) })
      queryClient.invalidateQueries({ queryKey: userKeys.lists() })
    },
    onError: handleError,
  })
}

export function useDeleteUser() {
  const queryClient = useQueryClient()
  const handleError = useMutationErrorHandler({
    messages: commonErrorMessages.delete,
  })

  return useMutation({
    mutationFn: (uid: string) => usersApi.delete(uid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userKeys.lists() })
    },
    onError: handleError,
  })
}

export function useSetUserPassword(uid: string) {
  const handleError = useMutationErrorHandler()

  return useMutation({
    mutationFn: (data: SetPasswordData) => usersApi.setPassword(uid, data),
    onError: handleError,
  })
}
