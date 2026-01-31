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
export function useUserPosix(uid: string, baseDn?: string) {
  return useQuery({
    queryKey: [...posixKeys.user(uid), { baseDn }] as const,
    queryFn: () => posixApi.getUserPosix(uid, baseDn),
    enabled: !!uid,
  })
}

/**
 * Activate POSIX for a user
 */
export function useActivateUserPosix(uid: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ data, baseDn }: { data: PosixAccountCreate; baseDn?: string }) =>
      posixApi.activateUserPosix(uid, data, baseDn),
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
    mutationFn: ({ data, baseDn }: { data: PosixAccountUpdate; baseDn?: string }) =>
      posixApi.updateUserPosix(uid, data, baseDn),
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
    mutationFn: ({ deletePersonalGroup, baseDn }: { deletePersonalGroup?: boolean; baseDn?: string }) =>
      posixApi.deactivateUserPosix(uid, deletePersonalGroup, baseDn),
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
export function usePosixGroups(params?: { base?: string }) {
  return useQuery({
    queryKey: [...posixKeys.posixGroups(), params] as const,
    queryFn: () => posixApi.listPosixGroups(params),
  })
}

/**
 * Get a single POSIX group by cn
 */
export function usePosixGroup(cn: string, baseDn?: string) {
  return useQuery({
    queryKey: [...posixKeys.posixGroup(cn), { baseDn }] as const,
    queryFn: () => posixApi.getPosixGroup(cn, baseDn),
    enabled: !!cn,
  })
}

/**
 * Create a new standalone POSIX group
 */
export function useCreatePosixGroup() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ data, baseDn }: { data: PosixGroupFullCreate; baseDn?: string }) =>
      posixApi.createPosixGroup(data, baseDn),
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
    mutationFn: ({ data, baseDn }: { data: PosixGroupUpdate; baseDn?: string }) =>
      posixApi.updatePosixGroup(cn, data, baseDn),
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
    mutationFn: ({ cn, baseDn }: { cn: string; baseDn?: string }) =>
      posixApi.deletePosixGroup(cn, baseDn),
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
    mutationFn: ({ uid, baseDn }: { uid: string; baseDn?: string }) =>
      posixApi.addPosixGroupMember(cn, uid, baseDn),
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
    mutationFn: ({ uid, baseDn }: { uid: string; baseDn?: string }) =>
      posixApi.removePosixGroupMember(cn, uid, baseDn),
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
export function useUserGroupMemberships(uid: string, baseDn?: string) {
  return useQuery({
    queryKey: [...posixKeys.user(uid), 'groups', { baseDn }] as const,
    queryFn: () => posixApi.getUserGroupMemberships(uid, baseDn),
    enabled: !!uid,
  })
}

/**
 * Add user to a group (from user perspective)
 */
export function useAddUserToGroup(uid: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ cn, baseDn }: { cn: string; baseDn?: string }) =>
      posixApi.addUserToGroup(uid, cn, baseDn),
    onSuccess: (_, { cn }) => {
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
    mutationFn: ({ cn, baseDn }: { cn: string; baseDn?: string }) =>
      posixApi.removeUserFromGroup(uid, cn, baseDn),
    onSuccess: (_, { cn }) => {
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
export function useMixedGroups(params?: { base?: string }) {
  return useQuery({
    queryKey: [...posixKeys.mixedGroups(), params] as const,
    queryFn: () => posixApi.listMixedGroups(params),
  })
}

/**
 * Get a single MixedGroup by cn
 */
export function useMixedGroup(cn: string, baseDn?: string) {
  return useQuery({
    queryKey: [...posixKeys.mixedGroup(cn), { baseDn }] as const,
    queryFn: () => posixApi.getMixedGroup(cn, baseDn),
    enabled: !!cn,
  })
}

/**
 * Create a new MixedGroup
 */
export function useCreateMixedGroup() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ data, baseDn }: { data: MixedGroupCreate; baseDn?: string }) =>
      posixApi.createMixedGroup(data, baseDn),
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
    mutationFn: ({ data, baseDn }: { data: MixedGroupUpdate; baseDn?: string }) =>
      posixApi.updateMixedGroup(cn, data, baseDn),
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
    mutationFn: ({ cn, baseDn }: { cn: string; baseDn?: string }) =>
      posixApi.deleteMixedGroup(cn, baseDn),
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
    mutationFn: ({ memberDn, baseDn }: { memberDn: string; baseDn?: string }) =>
      posixApi.addMixedGroupMember(cn, memberDn, baseDn),
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
    mutationFn: ({ memberDn, baseDn }: { memberDn: string; baseDn?: string }) =>
      posixApi.removeMixedGroupMember(cn, memberDn, baseDn),
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
