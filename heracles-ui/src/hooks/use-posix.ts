import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { posixApi } from '@/lib/api'
import type {
  PosixAccountCreate,
  PosixAccountUpdate,
  PosixGroupFullCreate,
  PosixGroupUpdate,
} from '@/types/posix'

// Query keys
export const posixKeys = {
  all: ['posix'] as const,
  user: (uid: string) => [...posixKeys.all, 'user', uid] as const,
  posixGroups: () => [...posixKeys.all, 'posix-groups'] as const,
  posixGroup: (cn: string) => [...posixKeys.all, 'posix-group', cn] as const,
  shells: () => [...posixKeys.all, 'shells'] as const,
  nextIds: () => [...posixKeys.all, 'next-ids'] as const,
}

// ============================================================================
// User POSIX Hooks
// ============================================================================

/**
 * Get POSIX status and data for a user
 */
export function useUserPosix(uid: string) {
  return useQuery({
    queryKey: posixKeys.user(uid),
    queryFn: () => posixApi.getUserPosix(uid),
    enabled: !!uid,
  })
}

/**
 * Activate POSIX for a user
 */
export function useActivateUserPosix(uid: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: PosixAccountCreate) => posixApi.activateUserPosix(uid, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: posixKeys.user(uid) })
      queryClient.invalidateQueries({ queryKey: posixKeys.nextIds() })
    },
  })
}

/**
 * Update POSIX attributes for a user
 */
export function useUpdateUserPosix(uid: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: PosixAccountUpdate) => posixApi.updateUserPosix(uid, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: posixKeys.user(uid) })
    },
  })
}

/**
 * Deactivate POSIX for a user
 */
export function useDeactivateUserPosix(uid: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => posixApi.deactivateUserPosix(uid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: posixKeys.user(uid) })
    },
  })
}

// ============================================================================
// Standalone POSIX Group Hooks
// ============================================================================

/**
 * List all POSIX groups
 */
export function usePosixGroups() {
  return useQuery({
    queryKey: posixKeys.posixGroups(),
    queryFn: () => posixApi.listPosixGroups(),
  })
}

/**
 * Get a single POSIX group by cn
 */
export function usePosixGroup(cn: string) {
  return useQuery({
    queryKey: posixKeys.posixGroup(cn),
    queryFn: () => posixApi.getPosixGroup(cn),
    enabled: !!cn,
  })
}

/**
 * Create a new standalone POSIX group
 */
export function useCreatePosixGroup() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: PosixGroupFullCreate) => posixApi.createPosixGroup(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: posixKeys.posixGroups() })
      queryClient.invalidateQueries({ queryKey: posixKeys.nextIds() })
    },
  })
}

/**
 * Update a POSIX group
 */
export function useUpdatePosixGroup(cn: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: PosixGroupUpdate) => posixApi.updatePosixGroup(cn, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: posixKeys.posixGroup(cn) })
      queryClient.invalidateQueries({ queryKey: posixKeys.posixGroups() })
    },
  })
}

/**
 * Delete a POSIX group
 */
export function useDeletePosixGroup() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (cn: string) => posixApi.deletePosixGroup(cn),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: posixKeys.posixGroups() })
    },
  })
}

/**
 * Add member to POSIX group
 */
export function useAddPosixGroupMember(cn: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (uid: string) => posixApi.addPosixGroupMember(cn, uid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: posixKeys.posixGroup(cn) })
      queryClient.invalidateQueries({ queryKey: posixKeys.posixGroups() })
    },
  })
}

/**
 * Remove member from POSIX group
 */
export function useRemovePosixGroupMember(cn: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (uid: string) => posixApi.removePosixGroupMember(cn, uid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: posixKeys.posixGroup(cn) })
      queryClient.invalidateQueries({ queryKey: posixKeys.posixGroups() })
    },
  })
}

// ============================================================================
// Utility Hooks
// ============================================================================

/**
 * Get available login shells
 */
export function useAvailableShells() {
  return useQuery({
    queryKey: posixKeys.shells(),
    queryFn: () => posixApi.getShells(),
    staleTime: 1000 * 60 * 60, // 1 hour - shells rarely change
  })
}

/**
 * Get next available UID and GID
 */
export function useNextIds() {
  return useQuery({
    queryKey: posixKeys.nextIds(),
    queryFn: () => posixApi.getNextIds(),
  })
}
