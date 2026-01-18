import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { posixApi } from '@/lib/api'
import type {
  PosixAccountCreate,
  PosixAccountUpdate,
  PosixGroupCreate,
  PosixGroupUpdate,
} from '@/types/posix'

// Query keys
export const posixKeys = {
  all: ['posix'] as const,
  user: (uid: string) => [...posixKeys.all, 'user', uid] as const,
  group: (cn: string) => [...posixKeys.all, 'group', cn] as const,
  shells: () => [...posixKeys.all, 'shells'] as const,
  nextIds: () => [...posixKeys.all, 'next-ids'] as const,
  posixGroups: () => [...posixKeys.all, 'posix-groups'] as const,
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
// Group POSIX Hooks
// ============================================================================

/**
 * Get POSIX status and data for a group
 */
export function useGroupPosix(cn: string) {
  return useQuery({
    queryKey: posixKeys.group(cn),
    queryFn: () => posixApi.getGroupPosix(cn),
    enabled: !!cn,
  })
}

/**
 * Activate POSIX for a group
 */
export function useActivateGroupPosix(cn: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: PosixGroupCreate) => posixApi.activateGroupPosix(cn, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: posixKeys.group(cn) })
      queryClient.invalidateQueries({ queryKey: posixKeys.nextIds() })
      queryClient.invalidateQueries({ queryKey: posixKeys.posixGroups() })
    },
  })
}

/**
 * Update POSIX attributes for a group
 */
export function useUpdateGroupPosix(cn: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: PosixGroupUpdate) => posixApi.updateGroupPosix(cn, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: posixKeys.group(cn) })
    },
  })
}

/**
 * Deactivate POSIX for a group
 */
export function useDeactivateGroupPosix(cn: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => posixApi.deactivateGroupPosix(cn),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: posixKeys.group(cn) })
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
    mutationFn: (uid: string) => posixApi.addGroupMember(cn, uid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: posixKeys.group(cn) })
    },
  })
}

/**
 * Remove member from POSIX group
 */
export function useRemovePosixGroupMember(cn: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (uid: string) => posixApi.removeGroupMember(cn, uid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: posixKeys.group(cn) })
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

/**
 * List all POSIX groups (for primary group selection)
 */
export function usePosixGroups() {
  return useQuery({
    queryKey: posixKeys.posixGroups(),
    queryFn: () => posixApi.listPosixGroups(),
  })
}
