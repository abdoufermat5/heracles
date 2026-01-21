import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { posixApi } from '@/lib/api'
import type {
  PosixAccountCreate,
  PosixAccountUpdate,
  PosixGroupFullCreate,
  PosixGroupUpdate,
  MixedGroupCreate,
  MixedGroupUpdate,
} from '@/types/posix'

// Query keys
export const posixKeys = {
  all: ['posix'] as const,
  user: (uid: string) => [...posixKeys.all, 'user', uid] as const,
  posixGroups: () => [...posixKeys.all, 'posix-groups'] as const,
  posixGroup: (cn: string) => [...posixKeys.all, 'posix-group', cn] as const,
  mixedGroups: () => [...posixKeys.all, 'mixed-groups'] as const,
  mixedGroup: (cn: string) => [...posixKeys.all, 'mixed-group', cn] as const,
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
    mutationFn: (deletePersonalGroup?: boolean) => posixApi.deactivateUserPosix(uid, deletePersonalGroup),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: posixKeys.user(uid) })
      queryClient.invalidateQueries({ queryKey: posixKeys.posixGroups() })
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

// ============================================================================
// User Group Membership Hooks (from user perspective)
// ============================================================================

/**
 * Get groups a user belongs to
 */
export function useUserGroupMemberships(uid: string) {
  return useQuery({
    queryKey: [...posixKeys.user(uid), 'groups'] as const,
    queryFn: () => posixApi.getUserGroupMemberships(uid),
    enabled: !!uid,
  })
}

/**
 * Add user to a group (from user perspective)
 */
export function useAddUserToGroup(uid: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (cn: string) => posixApi.addUserToGroup(uid, cn),
    onSuccess: (_, cn) => {
      queryClient.invalidateQueries({ queryKey: posixKeys.user(uid) })
      queryClient.invalidateQueries({ queryKey: posixKeys.posixGroup(cn) })
      queryClient.invalidateQueries({ queryKey: posixKeys.posixGroups() })
    },
  })
}

/**
 * Remove user from a group (from user perspective)
 */
export function useRemoveUserFromGroup(uid: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (cn: string) => posixApi.removeUserFromGroup(uid, cn),
    onSuccess: (_, cn) => {
      queryClient.invalidateQueries({ queryKey: posixKeys.user(uid) })
      queryClient.invalidateQueries({ queryKey: posixKeys.posixGroup(cn) })
      queryClient.invalidateQueries({ queryKey: posixKeys.posixGroups() })
    },
  })
}

// ============================================================================
// MixedGroup Hooks (groupOfNames + posixGroup)
// ============================================================================

/**
 * List all MixedGroups
 */
export function useMixedGroups() {
  return useQuery({
    queryKey: posixKeys.mixedGroups(),
    queryFn: () => posixApi.listMixedGroups(),
  })
}

/**
 * Get a single MixedGroup by cn
 */
export function useMixedGroup(cn: string) {
  return useQuery({
    queryKey: posixKeys.mixedGroup(cn),
    queryFn: () => posixApi.getMixedGroup(cn),
    enabled: !!cn,
  })
}

/**
 * Create a new MixedGroup
 */
export function useCreateMixedGroup() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: MixedGroupCreate) => posixApi.createMixedGroup(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: posixKeys.mixedGroups() })
      queryClient.invalidateQueries({ queryKey: posixKeys.nextIds() })
    },
  })
}

/**
 * Update a MixedGroup
 */
export function useUpdateMixedGroup(cn: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: MixedGroupUpdate) => posixApi.updateMixedGroup(cn, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: posixKeys.mixedGroup(cn) })
      queryClient.invalidateQueries({ queryKey: posixKeys.mixedGroups() })
    },
  })
}

/**
 * Delete a MixedGroup
 */
export function useDeleteMixedGroup() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (cn: string) => posixApi.deleteMixedGroup(cn),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: posixKeys.mixedGroups() })
    },
  })
}

/**
 * Add a member (DN) to a MixedGroup
 */
export function useAddMixedGroupMember(cn: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (memberDn: string) => posixApi.addMixedGroupMember(cn, memberDn),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: posixKeys.mixedGroup(cn) })
      queryClient.invalidateQueries({ queryKey: posixKeys.mixedGroups() })
    },
  })
}

/**
 * Remove a member (DN) from a MixedGroup
 */
export function useRemoveMixedGroupMember(cn: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (memberDn: string) => posixApi.removeMixedGroupMember(cn, memberDn),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: posixKeys.mixedGroup(cn) })
      queryClient.invalidateQueries({ queryKey: posixKeys.mixedGroups() })
    },
  })
}

/**
 * Add a memberUid to a MixedGroup
 */
export function useAddMixedGroupMemberUid(cn: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (uid: string) => posixApi.addMixedGroupMemberUid(cn, uid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: posixKeys.mixedGroup(cn) })
      queryClient.invalidateQueries({ queryKey: posixKeys.mixedGroups() })
    },
  })
}

/**
 * Remove a memberUid from a MixedGroup
 */
export function useRemoveMixedGroupMemberUid(cn: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (uid: string) => posixApi.removeMixedGroupMemberUid(cn, uid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: posixKeys.mixedGroup(cn) })
      queryClient.invalidateQueries({ queryKey: posixKeys.mixedGroups() })
    },
  })
}

/**
 * Get next available GID for MixedGroups
 */
export function useMixedGroupNextGid() {
  return useQuery({
    queryKey: [...posixKeys.mixedGroups(), 'next-gid'] as const,
    queryFn: () => posixApi.getMixedGroupNextGid(),
  })
}
