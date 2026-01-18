import { apiClient } from '../api-client'
import type {
  PosixAccountData,
  PosixAccountCreate,
  PosixAccountUpdate,
  PosixStatus,
  PosixGroupData,
  PosixGroupCreate,
  PosixGroupUpdate,
  PosixGroupStatus,
  AvailableShells,
  NextIds,
  PosixGroupListItem,
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

  // Group POSIX endpoints
  getGroupPosix: (cn: string) =>
    apiClient.get<PosixGroupStatus>(`/groups/${cn}/posix`),

  activateGroupPosix: (cn: string, data: PosixGroupCreate) =>
    apiClient.post<PosixGroupData>(`/groups/${cn}/posix`, data),

  updateGroupPosix: (cn: string, data: PosixGroupUpdate) =>
    apiClient.put<PosixGroupData>(`/groups/${cn}/posix`, data),

  deactivateGroupPosix: (cn: string) =>
    apiClient.delete(`/groups/${cn}/posix`),

  addGroupMember: (cn: string, uid: string) =>
    apiClient.post<PosixGroupData>(`/groups/${cn}/posix/members/${uid}`, {}),

  removeGroupMember: (cn: string, uid: string) =>
    apiClient.delete<PosixGroupData>(`/groups/${cn}/posix/members/${uid}`),

  // Utility endpoints
  getShells: () =>
    apiClient.get<AvailableShells>('/posix/shells'),

  getNextIds: () =>
    apiClient.get<NextIds>('/posix/next-ids'),

  listPosixGroups: () =>
    apiClient.get<{ groups: PosixGroupListItem[]; total: number }>('/posix/groups'),
}
