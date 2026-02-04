// API Configuration
export const API_BASE_URL = import.meta.env.VITE_API_BASE_PREFIX || '/api/v1'

// App Configuration
export const APP_NAME = 'Heracles'
export const APP_DESCRIPTION = 'Identity Management System'
export const APP_VERSION = '0.8.0-beta'

// Pagination
export const DEFAULT_PAGE_SIZE = 20
export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100]

// Session
export const SESSION_STORAGE_KEY = 'heracles_session'
export const TOKEN_STORAGE_KEY = 'heracles_token'
export const REFRESH_TOKEN_KEY = 'heracles_refresh_token'

// Routes - Re-exported from routes.ts for backward compatibility
export {
  ROUTES,
  PLUGIN_ROUTES,
  userDetailPath,
  groupDetailPath,
  posixGroupPath,
  mixedGroupPath,
  sudoRolePath,
  withCreateQuery,
} from './routes'

// LDAP Attribute Labels
export const LDAP_LABELS = {
  uid: 'Username',
  cn: 'Common Name',
  sn: 'Last Name',
  givenName: 'First Name',
  displayName: 'Display Name',
  mail: 'Email',
  telephoneNumber: 'Phone',
  title: 'Title',
  description: 'Description',
  uidNumber: 'UID Number',
  gidNumber: 'GID Number',
  homeDirectory: 'Home Directory',
  loginShell: 'Login Shell',
} as const
