/**
 * Mail Plugin API Client
 *
 * API client functions for mail account management
 */

import { apiClient } from '../api-client'
import type {
  MailAccountCreate,
  MailAccountUpdate,
  UserMailStatus,
  MailGroupCreate,
  MailGroupUpdate,
  GroupMailStatus,
} from '@/types/mail'

const BASE_PATH = '/mail'

// ============================================================================
// User Mail API
// ============================================================================

/**
 * Get mail status for a user
 */
export async function getUserMailStatus(uid: string): Promise<UserMailStatus> {
  return apiClient.get<UserMailStatus>(
    `${BASE_PATH}/users/${encodeURIComponent(uid)}`
  )
}

/**
 * Activate mail for a user
 */
export async function activateUserMail(
  uid: string,
  data: MailAccountCreate
): Promise<UserMailStatus> {
  return apiClient.post<UserMailStatus>(
    `${BASE_PATH}/users/${encodeURIComponent(uid)}/activate`,
    data
  )
}

/**
 * Update mail for a user
 */
export async function updateUserMail(
  uid: string,
  data: MailAccountUpdate
): Promise<UserMailStatus> {
  return apiClient.patch<UserMailStatus>(
    `${BASE_PATH}/users/${encodeURIComponent(uid)}`,
    data
  )
}

/**
 * Deactivate mail for a user
 */
export async function deactivateUserMail(uid: string): Promise<UserMailStatus> {
  return apiClient.post<UserMailStatus>(
    `${BASE_PATH}/users/${encodeURIComponent(uid)}/deactivate`,
    {}
  )
}

// ============================================================================
// Group Mail API
// ============================================================================

/**
 * Get mail status for a group
 */
export async function getGroupMailStatus(cn: string): Promise<GroupMailStatus> {
  return apiClient.get<GroupMailStatus>(
    `${BASE_PATH}/groups/${encodeURIComponent(cn)}`
  )
}

/**
 * Activate mailing list for a group
 */
export async function activateGroupMail(
  cn: string,
  data: MailGroupCreate
): Promise<GroupMailStatus> {
  return apiClient.post<GroupMailStatus>(
    `${BASE_PATH}/groups/${encodeURIComponent(cn)}/activate`,
    data
  )
}

/**
 * Update mailing list for a group
 */
export async function updateGroupMail(
  cn: string,
  data: MailGroupUpdate
): Promise<GroupMailStatus> {
  return apiClient.patch<GroupMailStatus>(
    `${BASE_PATH}/groups/${encodeURIComponent(cn)}`,
    data
  )
}

/**
 * Deactivate mailing list for a group
 */
export async function deactivateGroupMail(
  cn: string
): Promise<GroupMailStatus> {
  return apiClient.post<GroupMailStatus>(
    `${BASE_PATH}/groups/${encodeURIComponent(cn)}/deactivate`,
    {}
  )
}

// ============================================================================
// Export API Object
// ============================================================================

export const mailApi = {
  // User mail
  getUserStatus: getUserMailStatus,
  activateUser: activateUserMail,
  updateUser: updateUserMail,
  deactivateUser: deactivateUserMail,
  // Group mail
  getGroupStatus: getGroupMailStatus,
  activateGroup: activateGroupMail,
  updateGroup: updateGroupMail,
  deactivateGroup: deactivateGroupMail,
}
