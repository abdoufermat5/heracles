/**
 * Mail Plugin React Query Hooks
 *
 * Custom hooks for managing mail accounts with TanStack Query
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { mailApi } from '@/lib/api/mail'
import type {
  MailAccountCreate,
  MailAccountUpdate,
  MailGroupCreate,
  MailGroupUpdate,
} from '@/types/mail'

// ============================================================================
// Query Keys
// ============================================================================

export const mailQueryKeys = {
  all: ['mail'] as const,
  users: () => [...mailQueryKeys.all, 'users'] as const,
  user: (uid: string) => [...mailQueryKeys.users(), uid] as const,
  groups: () => [...mailQueryKeys.all, 'groups'] as const,
  group: (cn: string) => [...mailQueryKeys.groups(), cn] as const,
}

// ============================================================================
// User Mail Query Hooks
// ============================================================================

/**
 * Hook for getting user mail status
 */
export function useUserMailStatus(uid: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: mailQueryKeys.user(uid),
    queryFn: () => mailApi.getUserStatus(uid),
    enabled: options?.enabled ?? !!uid,
    staleTime: 30 * 1000,
  })
}

// ============================================================================
// User Mail Mutation Hooks
// ============================================================================

/**
 * Hook for activating mail for a user
 */
export function useActivateUserMail() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ uid, data }: { uid: string; data: MailAccountCreate }) =>
      mailApi.activateUser(uid, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: mailQueryKeys.user(variables.uid),
      })
    },
  })
}

/**
 * Hook for updating mail for a user
 */
export function useUpdateUserMail() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ uid, data }: { uid: string; data: MailAccountUpdate }) =>
      mailApi.updateUser(uid, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: mailQueryKeys.user(variables.uid),
      })
    },
  })
}

/**
 * Hook for deactivating mail for a user
 */
export function useDeactivateUserMail() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (uid: string) => mailApi.deactivateUser(uid),
    onSuccess: (_, uid) => {
      queryClient.invalidateQueries({ queryKey: mailQueryKeys.user(uid) })
    },
  })
}

// ============================================================================
// Group Mail Query Hooks
// ============================================================================

/**
 * Hook for getting group mail status
 */
export function useGroupMailStatus(cn: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: mailQueryKeys.group(cn),
    queryFn: () => mailApi.getGroupStatus(cn),
    enabled: options?.enabled ?? !!cn,
    staleTime: 30 * 1000,
  })
}

// ============================================================================
// Group Mail Mutation Hooks
// ============================================================================

/**
 * Hook for activating mailing list for a group
 */
export function useActivateGroupMail() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ cn, data }: { cn: string; data: MailGroupCreate }) =>
      mailApi.activateGroup(cn, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: mailQueryKeys.group(variables.cn),
      })
    },
  })
}

/**
 * Hook for updating mailing list for a group
 */
export function useUpdateGroupMail() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ cn, data }: { cn: string; data: MailGroupUpdate }) =>
      mailApi.updateGroup(cn, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: mailQueryKeys.group(variables.cn),
      })
    },
  })
}

/**
 * Hook for deactivating mailing list for a group
 */
export function useDeactivateGroupMail() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (cn: string) => mailApi.deactivateGroup(cn),
    onSuccess: (_, cn) => {
      queryClient.invalidateQueries({ queryKey: mailQueryKeys.group(cn) })
    },
  })
}
