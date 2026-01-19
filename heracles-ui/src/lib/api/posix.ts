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
} from '@/types/posix'

export const posixApi = {
  // User POSIX endpoints
  getUserPosix: (uid: string) =>
    apiClient.get<PosixStatus>(`/users/${uid}/posix`),

  activateUserPosix: (uid: string, data: PosixAccountCreate) =>
    apiClient.post<PosixAccountData>(`/users/${uid}/posix`, data),

  updateUserPosix: (uid: string, data: PosixAccountUpdate) =>
    apiClient.put<PosixAccountData>(`/users/${uid}/posix`, data),

  deactivateUserPosix: (uid: string) =>
    apiClient.delete(`/users/${uid}/posix`),

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

  // Utility endpoints
  getShells: () =>
    apiClient.get<AvailableShells>('/posix/shells'),

  getNextIds: () =>
    apiClient.get<NextIds>('/posix/next-ids'),
}
