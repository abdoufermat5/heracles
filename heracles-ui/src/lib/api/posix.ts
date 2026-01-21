import { apiClient } from '../api-client'
import type {
  PosixAccountData,
  PosixAccountCreate,
  PosixAccountUpdate,
  PosixStatus,
  PosixGroupData,
  PosixGroupFullCreate,
  PosixGroupUpdate,
  AvailableShells,
  NextIds,
  PosixGroupListResponse,
  // MixedGroup types
  MixedGroupData,
  MixedGroupCreate,
  MixedGroupUpdate,
  MixedGroupListResponse,
} from '@/types/posix'

export const posixApi = {
  // User POSIX endpoints
  getUserPosix: (uid: string) =>
    apiClient.get<PosixStatus>(`/users/${uid}/posix`),

  activateUserPosix: (uid: string, data: PosixAccountCreate) =>
    apiClient.post<PosixAccountData>(`/users/${uid}/posix`, data),

  updateUserPosix: (uid: string, data: PosixAccountUpdate) =>
    apiClient.put<PosixAccountData>(`/users/${uid}/posix`, data),

  deactivateUserPosix: (uid: string, deletePersonalGroup?: boolean) =>
    apiClient.delete(`/users/${uid}/posix${deletePersonalGroup !== undefined ? `?delete_personal_group=${deletePersonalGroup}` : ''}`),

  // Standalone POSIX Group endpoints (posixGroup is a standalone entry, not a tab on groupOfNames)
  listPosixGroups: () =>
    apiClient.get<PosixGroupListResponse>('/posix/groups'),

  getPosixGroup: (cn: string) =>
    apiClient.get<PosixGroupData>(`/posix/groups/${cn}`),

  createPosixGroup: (data: PosixGroupFullCreate) =>
    apiClient.post<PosixGroupData>('/posix/groups', data),

  updatePosixGroup: (cn: string, data: PosixGroupUpdate) =>
    apiClient.put<PosixGroupData>(`/posix/groups/${cn}`, data),

  deletePosixGroup: (cn: string) =>
    apiClient.delete(`/posix/groups/${cn}`),

  addPosixGroupMember: (cn: string, uid: string) =>
    apiClient.post<PosixGroupData>(`/posix/groups/${cn}/members/${uid}`, {}),

  removePosixGroupMember: (cn: string, uid: string) =>
    apiClient.delete<PosixGroupData>(`/posix/groups/${cn}/members/${uid}`),

  // User group membership endpoints (from user perspective)
  getUserGroupMemberships: (uid: string) =>
    apiClient.get<string[]>(`/users/${uid}/posix/groups`),

  addUserToGroup: (uid: string, cn: string) =>
    apiClient.post<PosixGroupData>(`/users/${uid}/posix/groups/${cn}`, {}),

  removeUserFromGroup: (uid: string, cn: string) =>
    apiClient.delete(`/users/${uid}/posix/groups/${cn}`),

  // Utility endpoints
  getShells: () =>
    apiClient.get<AvailableShells>('/posix/shells'),

  getNextIds: () =>
    apiClient.get<NextIds>('/posix/next-ids'),

  // ============================================================================
  // MixedGroup endpoints (groupOfNames + posixGroup)
  // ============================================================================

  /**
   * List all MixedGroups
   */
  listMixedGroups: () =>
    apiClient.get<MixedGroupListResponse>('/posix/mixed-groups'),

  /**
   * Get a specific MixedGroup by CN
   */
  getMixedGroup: (cn: string) =>
    apiClient.get<MixedGroupData>(`/posix/mixed-groups/${cn}`),

  /**
   * Create a new MixedGroup
   */
  createMixedGroup: (data: MixedGroupCreate) =>
    apiClient.post<MixedGroupData>('/posix/mixed-groups', data),

  /**
   * Update a MixedGroup
   */
  updateMixedGroup: (cn: string, data: MixedGroupUpdate) =>
    apiClient.patch<MixedGroupData>(`/posix/mixed-groups/${cn}`, data),

  /**
   * Delete a MixedGroup
   */
  deleteMixedGroup: (cn: string) =>
    apiClient.delete(`/posix/mixed-groups/${cn}`),

  /**
   * Add a member (DN) to a MixedGroup
   */
  addMixedGroupMember: (cn: string, memberDn: string) =>
    apiClient.post<MixedGroupData>(`/posix/mixed-groups/${cn}/members?member_dn=${encodeURIComponent(memberDn)}`, {}),

  /**
   * Remove a member (DN) from a MixedGroup
   */
  removeMixedGroupMember: (cn: string, memberDn: string) =>
    apiClient.delete<MixedGroupData>(`/posix/mixed-groups/${cn}/members?member_dn=${encodeURIComponent(memberDn)}`),

  /**
   * Add a memberUid to a MixedGroup
   */
  addMixedGroupMemberUid: (cn: string, uid: string) =>
    apiClient.post<MixedGroupData>(`/posix/mixed-groups/${cn}/member-uids/${uid}`, {}),

  /**
   * Remove a memberUid from a MixedGroup
   */
  removeMixedGroupMemberUid: (cn: string, uid: string) =>
    apiClient.delete<MixedGroupData>(`/posix/mixed-groups/${cn}/member-uids/${uid}`),

  /**
   * Get next available GID for MixedGroups
   */
  getMixedGroupNextGid: () =>
    apiClient.get<{ value: number }>('/posix/mixed-groups/next-gid'),
}
