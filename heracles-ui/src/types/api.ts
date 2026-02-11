// API Types

export interface User {
  dn: string
  uid: string
  cn: string
  sn: string
  givenName: string
  displayName?: string
  mail?: string
  telephoneNumber?: string
  title?: string
  description?: string
  uidNumber?: number
  gidNumber?: number
  homeDirectory?: string
  loginShell?: string
  memberOf?: string[]
  objectClass?: string[]
  createTimestamp?: string
  modifyTimestamp?: string
  entryUUID?: string
}

export interface UserListResponse {
  users: User[]
  total: number
  page: number
  page_size: number
}

export interface Group {
  dn: string
  cn: string
  description?: string
  gidNumber?: number
  memberUid?: string[]
  member?: string[]
  members?: string[]
  objectClass?: string[]
}

export interface GroupListResponse {
  groups: Group[]
  total: number
  page: number
  page_size: number
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface UserInfo {
  dn: string
  uid: string
  cn: string
  displayName?: string
  mail?: string
  groups: string[]
  is_admin: boolean
}

export interface ApiError {
  detail: string
  status_code?: number
}

// Form types
export interface UserCreateData {
  uid: string
  cn: string
  givenName: string
  sn: string
  mail?: string
  telephoneNumber?: string
  title?: string
  description?: string
  uidNumber?: number
  gidNumber?: number
  homeDirectory?: string
  loginShell?: string
  password: string
  departmentDn?: string
  templateId?: string
}

export interface UserUpdateData {
  givenName?: string
  sn?: string
  mail?: string
  telephoneNumber?: string
  title?: string
  description?: string
  uidNumber?: number
  gidNumber?: number
  homeDirectory?: string
  loginShell?: string
}

export interface GroupCreateData {
  cn: string
  description?: string
  gidNumber?: number
  departmentDn?: string
}

export interface GroupUpdateData {
  description?: string
  gidNumber?: number
}

export interface LoginCredentials {
  username: string
  password: string
}

export interface PasswordChangeData {
  current_password: string
  new_password: string
}

export interface SetPasswordData {
  password: string
}

// Pagination
export interface PaginationParams {
  page?: number
  page_size?: number
  search?: string
  [key: string]: string | number | undefined
}
