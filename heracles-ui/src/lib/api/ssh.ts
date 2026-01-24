/**
 * SSH Plugin API Client
 * 
 * API client functions for SSH key management
 */

import { apiClient } from '../api-client'
import type {
  SSHKeyRead,
  SSHKeyCreate,
  UserSSHStatus,
  UserSSHActivate,
  UserSSHKeysUpdate,
} from '@/types/ssh'
import { encodeFingerprint } from '@/types/ssh'

const BASE_PATH = '/ssh'

// ============================================================================
// User SSH Status
// ============================================================================

/**
 * Get SSH status for a user
 */
export async function getUserSSHStatus(uid: string): Promise<UserSSHStatus> {
  return apiClient.get<UserSSHStatus>(`${BASE_PATH}/users/${encodeURIComponent(uid)}`)
}

/**
 * Activate SSH for a user
 */
export async function activateUserSSH(uid: string, data?: UserSSHActivate): Promise<UserSSHStatus> {
  return apiClient.post<UserSSHStatus>(
    `${BASE_PATH}/users/${encodeURIComponent(uid)}/activate`,
    data || {}
  )
}

/**
 * Deactivate SSH for a user
 */
export async function deactivateUserSSH(uid: string): Promise<UserSSHStatus> {
  return apiClient.post<UserSSHStatus>(
    `${BASE_PATH}/users/${encodeURIComponent(uid)}/deactivate`,
    {}
  )
}

// ============================================================================
// SSH Key Management
// ============================================================================

/**
 * List SSH keys for a user
 */
export async function listUserSSHKeys(uid: string): Promise<SSHKeyRead[]> {
  return apiClient.get<SSHKeyRead[]>(`${BASE_PATH}/users/${encodeURIComponent(uid)}/keys`)
}

/**
 * Add SSH key to a user
 */
export async function addUserSSHKey(uid: string, data: SSHKeyCreate): Promise<UserSSHStatus> {
  return apiClient.post<UserSSHStatus>(
    `${BASE_PATH}/users/${encodeURIComponent(uid)}/keys`,
    data
  )
}

/**
 * Update all SSH keys for a user
 */
export async function updateUserSSHKeys(uid: string, data: UserSSHKeysUpdate): Promise<UserSSHStatus> {
  return apiClient.put<UserSSHStatus>(
    `${BASE_PATH}/users/${encodeURIComponent(uid)}/keys`,
    data
  )
}

/**
 * Remove SSH key from a user
 */
export async function removeUserSSHKey(uid: string, fingerprint: string): Promise<void> {
  const encodedFp = encodeFingerprint(fingerprint)
  return apiClient.delete(
    `${BASE_PATH}/users/${encodeURIComponent(uid)}/keys/${encodeURIComponent(encodedFp)}`
  )
}

/**
 * Find user by SSH key
 */
export async function findUserBySSHKey(params: { key?: string; fingerprint?: string }): Promise<string | null> {
  const searchParams = new URLSearchParams()
  if (params.key) searchParams.set('key', params.key)
  if (params.fingerprint) searchParams.set('fingerprint', params.fingerprint)
  
  try {
    return await apiClient.get<string>(`${BASE_PATH}/lookup?${searchParams}`)
  } catch {
    return null
  }
}

// ============================================================================
// Export API Object
// ============================================================================

export const sshApi = {
  getUserStatus: getUserSSHStatus,
  activate: activateUserSSH,
  deactivate: deactivateUserSSH,
  listKeys: listUserSSHKeys,
  addKey: addUserSSHKey,
  updateKeys: updateUserSSHKeys,
  removeKey: removeUserSSHKey,
  findUserByKey: findUserBySSHKey,
}
