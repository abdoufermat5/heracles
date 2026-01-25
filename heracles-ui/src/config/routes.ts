/**
 * Application Routes Configuration
 *
 * Centralized route definitions for the application.
 * Use these constants instead of hardcoding route strings.
 */

// Core Routes (existing)
export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  DASHBOARD: '/dashboard',
  USERS: '/users',
  USER_DETAIL: '/users/:uid',
  USER_CREATE: '/users/new',
  GROUPS: '/groups',
  GROUP_DETAIL: '/groups/:cn',
  GROUP_CREATE: '/groups/new',
  SYSTEMS: '/systems',
  SETTINGS: '/settings',
} as const

// Plugin Routes
export const PLUGIN_ROUTES = {
  POSIX: {
    GROUPS: '/posix/groups',
    GROUP_DETAIL: '/posix/groups/:cn',
    MIXED_GROUPS: '/posix/mixed-groups',
    MIXED_GROUP_DETAIL: '/posix/mixed-groups/:cn',
  },
  SUDO: {
    ROLES: '/sudo/roles',
    ROLE_DETAIL: '/sudo/roles/:cn',
  },
  SYSTEMS: {
    LIST: '/systems',
    DETAIL: '/systems/:type/:cn',
    SERVERS: '/systems/servers',
    WORKSTATIONS: '/systems/workstations',
    TERMINALS: '/systems/terminals',
    PRINTERS: '/systems/printers',
    COMPONENTS: '/systems/components',
    PHONES: '/systems/phones',
    MOBILES: '/systems/mobiles',
  },
  SSH: {
    // SSH routes will be added when SSH pages are implemented
  },
} as const

// Route Builder Functions
// Use these to construct dynamic routes with parameters

/**
 * Build the user detail route
 * @param uid - User UID
 */
export function userDetailPath(uid: string): string {
  return ROUTES.USER_DETAIL.replace(':uid', encodeURIComponent(uid))
}

/**
 * Build the group detail route
 * @param cn - Group CN
 */
export function groupDetailPath(cn: string): string {
  return ROUTES.GROUP_DETAIL.replace(':cn', encodeURIComponent(cn))
}

/**
 * Build the POSIX group detail route
 * @param cn - Group CN
 */
export function posixGroupPath(cn: string): string {
  return PLUGIN_ROUTES.POSIX.GROUP_DETAIL.replace(':cn', encodeURIComponent(cn))
}

/**
 * Build the Mixed group detail route
 * @param cn - Group CN
 */
export function mixedGroupPath(cn: string): string {
  return PLUGIN_ROUTES.POSIX.MIXED_GROUP_DETAIL.replace(
    ':cn',
    encodeURIComponent(cn)
  )
}

/**
 * Build the Sudo role detail route
 * @param cn - Role CN
 */
export function sudoRolePath(cn: string): string {
  return PLUGIN_ROUTES.SUDO.ROLE_DETAIL.replace(':cn', encodeURIComponent(cn))
}

/**
 * Build the System detail route
 * @param type - System type
 * @param cn - System CN (hostname)
 */
export function systemDetailPath(type: string, cn: string): string {
  return PLUGIN_ROUTES.SYSTEMS.DETAIL
    .replace(':type', encodeURIComponent(type))
    .replace(':cn', encodeURIComponent(cn))
}

// Query parameters for create dialogs
export const CREATE_QUERY = '?create=true'

/**
 * Build route with create query parameter
 * @param route - Base route
 */
export function withCreateQuery(route: string): string {
  return `${route}${CREATE_QUERY}`
}
