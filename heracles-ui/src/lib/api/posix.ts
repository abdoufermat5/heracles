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
  getUserPosix: (uid: string, baseDn?: string) => {
    const params = baseDn ? `?base_dn=${encodeURIComponent(baseDn)}` : ''
    return apiClient.get<PosixStatus>(`/users/${uid}/posix${params}`)
  },

  activateUserPosix: (uid: string, data: PosixAccountCreate, baseDn?: string) => {
    const params = baseDn ? `?base_dn=${encodeURIComponent(baseDn)}` : ''
    return apiClient.post<PosixAccountData>(`/users/${uid}/posix${params}`, data)
  },

  updateUserPosix: (uid: string, data: PosixAccountUpdate, baseDn?: string) => {
    const params = baseDn ? `?base_dn=${encodeURIComponent(baseDn)}` : ''
    return apiClient.put<PosixAccountData>(`/users/${uid}/posix${params}`, data)
  },

  deactivateUserPosix: (uid: string, deletePersonalGroup?: boolean, baseDn?: string) => {
    const searchParams = new URLSearchParams()
    if (deletePersonalGroup !== undefined) searchParams.set('delete_personal_group', deletePersonalGroup.toString())
    if (baseDn) searchParams.set('base_dn', baseDn)
    const query = searchParams.toString()
    return apiClient.delete(`/users/${uid}/posix${query ? `?${query}` : ''}`)
  },

  // Standalone POSIX Group endpoints (posixGroup is a standalone entry, not a tab on groupOfNames)
  listPosixGroups: (params?: { base?: string }) => {
    const queryParams: Record<string, string | undefined> = {}
    if (params?.base) queryParams.base_dn = params.base
    return apiClient.get<PosixGroupListResponse>('/posix/groups', queryParams)
  },

  getPosixGroup: (cn: string, baseDn?: string) => {
    const params = baseDn ? `?base_dn=${encodeURIComponent(baseDn)}` : ''
    return apiClient.get<PosixGroupData>(`/posix/groups/${cn}${params}`)
  },

  createPosixGroup: (data: PosixGroupFullCreate, baseDn?: string) => {
    const params = baseDn ? `?base_dn=${encodeURIComponent(baseDn)}` : ''
    return apiClient.post<PosixGroupData>(`/posix/groups${params}`, data)
  },

  updatePosixGroup: (cn: string, data: PosixGroupUpdate, baseDn?: string) => {
    const params = baseDn ? `?base_dn=${encodeURIComponent(baseDn)}` : ''
    return apiClient.put<PosixGroupData>(`/posix/groups/${cn}${params}`, data)
  },

  deletePosixGroup: (cn: string, baseDn?: string) => {
    const params = baseDn ? `?base_dn=${encodeURIComponent(baseDn)}` : ''
    return apiClient.delete(`/posix/groups/${cn}${params}`)
  },

  addPosixGroupMember: (cn: string, uid: string, baseDn?: string) => {
    const params = baseDn ? `?base_dn=${encodeURIComponent(baseDn)}` : ''
    return apiClient.post<PosixGroupData>(`/posix/groups/${cn}/members/${uid}${params}`, {})
  },

  removePosixGroupMember: (cn: string, uid: string, baseDn?: string) => {
    const params = baseDn ? `?base_dn=${encodeURIComponent(baseDn)}` : ''
    return apiClient.delete<PosixGroupData>(`/posix/groups/${cn}/members/${uid}${params}`)
  },

  // User group membership endpoints (from user perspective)
  getUserGroupMemberships: (uid: string, baseDn?: string) => {
    const params = baseDn ? `?base_dn=${encodeURIComponent(baseDn)}` : ''
    return apiClient.get<string[]>(`/users/${uid}/posix/groups${params}`)
  },

  addUserToGroup: (uid: string, cn: string, baseDn?: string) => {
    const params = baseDn ? `?base_dn=${encodeURIComponent(baseDn)}` : ''
    return apiClient.post<PosixGroupData>(`/users/${uid}/posix/groups/${cn}${params}`, {})
  },

  removeUserFromGroup: (uid: string, cn: string, baseDn?: string) => {
    const params = baseDn ? `?base_dn=${encodeURIComponent(baseDn)}` : ''
    return apiClient.delete(`/users/${uid}/posix/groups/${cn}${params}`)
  },

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
  listMixedGroups: (params?: { base?: string }) => {
    const queryParams: Record<string, string | undefined> = {}
    if (params?.base) queryParams.base_dn = params.base
    return apiClient.get<MixedGroupListResponse>('/posix/mixed-groups', queryParams)
  },

  /**
   * Get a specific MixedGroup by CN
   */
  getMixedGroup: (cn: string, baseDn?: string) => {
    const params = baseDn ? `?base_dn=${encodeURIComponent(baseDn)}` : ''
    return apiClient.get<MixedGroupData>(`/posix/mixed-groups/${cn}${params}`)
  },

  /**
   * Create a new MixedGroup
   */
  createMixedGroup: (data: MixedGroupCreate, baseDn?: string) => {
    const params = baseDn ? `?base_dn=${encodeURIComponent(baseDn)}` : ''
    return apiClient.post<MixedGroupData>(`/posix/mixed-groups${params}`, data)
  },

  /**
   * Update a MixedGroup
   */
  updateMixedGroup: (cn: string, data: MixedGroupUpdate, baseDn?: string) => {
    const params = baseDn ? `?base_dn=${encodeURIComponent(baseDn)}` : ''
    return apiClient.patch<MixedGroupData>(`/posix/mixed-groups/${cn}${params}`, data)
  },

  /**
   * Delete a MixedGroup
   */
  deleteMixedGroup: (cn: string, baseDn?: string) => {
    const params = baseDn ? `?base_dn=${encodeURIComponent(baseDn)}` : ''
    return apiClient.delete(`/posix/mixed-groups/${cn}${params}`)
  },

  /**
   * Add a member (DN) to a MixedGroup
   */
  addMixedGroupMember: (cn: string, memberDn: string, baseDn?: string) => {
    const params = new URLSearchParams()
    params.set('member_dn', memberDn)
    if (baseDn) params.set('base_dn', baseDn)
    return apiClient.post<MixedGroupData>(`/posix/mixed-groups/${cn}/members?${params.toString()}`, {})
  },

  /**
   * Remove a member (DN) from a MixedGroup
   */
  removeMixedGroupMember: (cn: string, memberDn: string, baseDn?: string) => {
    const params = new URLSearchParams()
    params.set('member_dn', memberDn)
    if (baseDn) params.set('base_dn', baseDn)
    return apiClient.delete<MixedGroupData>(`/posix/mixed-groups/${cn}/members?${params.toString()}`)
  },

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
