/**
 * SSH Plugin React Query Hooks
 * 
 * Custom hooks for managing SSH keys with TanStack Query
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { sshApi } from '@/lib/api/ssh'
import type {
  SSHKeyCreate,
  UserSSHActivate,
  UserSSHKeysUpdate,
} from '@/types/ssh'

// ============================================================================
// Query Keys
// ============================================================================

export const sshQueryKeys = {
  all: ['ssh'] as const,
  user: (uid: string) => [...sshQueryKeys.all, 'user', uid] as const,
  userStatus: (uid: string) => [...sshQueryKeys.user(uid), 'status'] as const,
  userKeys: (uid: string) => [...sshQueryKeys.user(uid), 'keys'] as const,
}

// ============================================================================
// Query Hooks
// ============================================================================

/**
 * Hook for getting user SSH status
 */
export function useUserSSHStatus(uid: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: sshQueryKeys.userStatus(uid),
    queryFn: () => sshApi.getUserStatus(uid),
    enabled: options?.enabled ?? !!uid,
    staleTime: 30 * 1000,
  })
}

/**
 * Hook for listing user SSH keys
 */
export function useUserSSHKeys(uid: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: sshQueryKeys.userKeys(uid),
    queryFn: () => sshApi.listKeys(uid),
    enabled: options?.enabled ?? !!uid,
    staleTime: 30 * 1000,
  })
}

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * Hook for activating SSH for a user
 */
export function useActivateUserSSH() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ uid, data }: { uid: string; data?: UserSSHActivate }) =>
      sshApi.activate(uid, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: sshQueryKeys.user(variables.uid) })
    },
  })
}

/**
 * Hook for deactivating SSH for a user
 */
export function useDeactivateUserSSH() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (uid: string) => sshApi.deactivate(uid),
    onSuccess: (_, uid) => {
      queryClient.invalidateQueries({ queryKey: sshQueryKeys.user(uid) })
    },
  })
}

/**
 * Hook for adding an SSH key
 */
export function useAddSSHKey() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ uid, data }: { uid: string; data: SSHKeyCreate }) =>
      sshApi.addKey(uid, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: sshQueryKeys.user(variables.uid) })
    },
  })
}

/**
 * Hook for removing an SSH key
 */
export function useRemoveSSHKey() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ uid, fingerprint }: { uid: string; fingerprint: string }) =>
      sshApi.removeKey(uid, fingerprint),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: sshQueryKeys.user(variables.uid) })
    },
  })
}

/**
 * Hook for bulk updating SSH keys
 */
export function useUpdateSSHKeys() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ uid, data }: { uid: string; data: UserSSHKeysUpdate }) =>
      sshApi.updateKeys(uid, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: sshQueryKeys.user(variables.uid) })
    },
  })
}
