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
  ROLES: '/roles',
  ROLE_DETAIL: '/roles/:cn',
  ROLE_CREATE: '/roles/create',
  DEPARTMENTS: '/departments',
  DEPARTMENT_DETAIL: '/departments/:dn',
  DEPARTMENT_CREATE: '/departments/new',
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
  DNS: {
    ZONES: '/dns',
    ZONE_DETAIL: '/dns/:zoneName',
  },
  DHCP: {
    SERVICES: '/dhcp',
    SERVICE_DETAIL: '/dhcp/:serviceCn',
    SUBNET_DETAIL: '/dhcp/:serviceCn/subnets/:subnetCn',
    HOST_DETAIL: '/dhcp/:serviceCn/hosts/:hostCn',
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
 * Build the role detail route
 * @param cn - Role CN
 */
export function roleDetailPath(cn: string): string {
  return ROUTES.ROLE_DETAIL.replace(':cn', encodeURIComponent(cn))
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

/**
 * Build the DNS zone detail route
 * @param zoneName - Zone name
 */
export function dnsZonePath(zoneName: string): string {
  return PLUGIN_ROUTES.DNS.ZONE_DETAIL.replace(
    ':zoneName',
    encodeURIComponent(zoneName)
  )
}

/**
 * Build the DHCP service detail route
 * @param serviceCn - Service CN
 */
export function dhcpServicePath(serviceCn: string): string {
  return PLUGIN_ROUTES.DHCP.SERVICE_DETAIL.replace(
    ':serviceCn',
    encodeURIComponent(serviceCn)
  )
}

/**
 * Build the DHCP subnet detail route
 * @param serviceCn - Service CN
 * @param subnetCn - Subnet CN (network address)
 */
export function dhcpSubnetPath(serviceCn: string, subnetCn: string): string {
  return PLUGIN_ROUTES.DHCP.SUBNET_DETAIL
    .replace(':serviceCn', encodeURIComponent(serviceCn))
    .replace(':subnetCn', encodeURIComponent(subnetCn))
}

/**
 * Build the DHCP host detail route
 * @param serviceCn - Service CN
 * @param hostCn - Host CN (hostname)
 */
export function dhcpHostPath(serviceCn: string, hostCn: string): string {
  return PLUGIN_ROUTES.DHCP.HOST_DETAIL
    .replace(':serviceCn', encodeURIComponent(serviceCn))
    .replace(':hostCn', encodeURIComponent(hostCn))
}

/**
 * Build the department detail route
 * @param dn - Department DN
 */
export function departmentDetailPath(dn: string): string {
  return ROUTES.DEPARTMENT_DETAIL.replace(':dn', encodeURIComponent(dn))
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
