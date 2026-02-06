import { Routes, Route, Navigate } from 'react-router-dom'
import { AppLayout } from '@/components/layout'
import { ProtectedRoute } from '@/components/auth'
import { ErrorBoundary } from '@/components/common/error-boundary'
import {
  LoginPage,
  DashboardPage,
  UsersListPage,
  UserCreatePage,
  UserDetailPage,
  GroupsListPage,
  GroupCreatePage,
  GroupDetailPage,
  SystemsListPage,
  SystemDetailPage,
  SettingsPage,
} from '@/pages'
import {
  DepartmentsListPage,
  DepartmentCreatePage,
  DepartmentDetailPage,
} from '@/pages/departments'
import { RoleCreatePage, RoleDetailPage } from '@/pages/roles'
import { PosixGroupsPage, PosixGroupDetailPage, MixedGroupsPage, MixedGroupDetailPage } from '@/pages/posix'
import { SudoRolesPage, SudoRoleDetailPage } from '@/pages/sudo'
import { DnsZonesListPage, DnsZoneDetailPage } from '@/pages/dns'
import { DhcpServicesListPage, DhcpServiceDetailPage, DhcpSubnetDetailPage, DhcpHostDetailPage } from '@/pages/dhcp'
import {
  AclPoliciesListPage,
  AclPolicyCreatePage,
  AclPolicyDetailPage,
  AclAssignmentsListPage,
  AclAssignmentCreatePage,
  AclPermissionsListPage,
  AclAttrGroupsListPage,
  AclAccessMatrixPage,
  AclAuditLogPage,
} from '@/pages/acl'
import { ProfilePage } from '@/pages/profile'
import { ROUTES, PLUGIN_ROUTES } from '@/config/constants'

export function AppRouter() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path={ROUTES.LOGIN} element={<LoginPage />} />

      {/* Protected routes */}
      <Route
        element={
          <ProtectedRoute>
            <ErrorBoundary>
              <AppLayout />
            </ErrorBoundary>
          </ProtectedRoute>
        }
      >
        <Route path={ROUTES.DASHBOARD} element={<DashboardPage />} />

        {/* Users */}
        <Route path={ROUTES.USERS} element={<UsersListPage />} />
        <Route path={ROUTES.USER_CREATE} element={<UserCreatePage />} />
        <Route path={ROUTES.USER_DETAIL} element={<UserDetailPage />} />

        {/* Groups (organizational - groupOfNames) - also contains Roles tab */}
        <Route path={ROUTES.GROUPS} element={<GroupsListPage />} />
        <Route path={ROUTES.GROUP_CREATE} element={<GroupCreatePage />} />
        <Route path={ROUTES.GROUP_DETAIL} element={<GroupDetailPage />} />

        {/* Roles (organizationalRole) */}
        <Route path={ROUTES.ROLES} element={<Navigate to={`${ROUTES.GROUPS}?tab=roles`} replace />} />
        <Route path={ROUTES.ROLE_CREATE} element={<RoleCreatePage />} />
        <Route path={ROUTES.ROLE_DETAIL} element={<RoleDetailPage />} />

        {/* Departments */}
        <Route path={ROUTES.DEPARTMENTS} element={<DepartmentsListPage />} />
        <Route path={ROUTES.DEPARTMENT_CREATE} element={<DepartmentCreatePage />} />
        <Route path={ROUTES.DEPARTMENT_DETAIL} element={<DepartmentDetailPage />} />

        {/* POSIX Groups (standalone posixGroup entries) */}
        <Route path={PLUGIN_ROUTES.POSIX.GROUPS} element={<PosixGroupsPage />} />
        <Route path={PLUGIN_ROUTES.POSIX.GROUP_DETAIL} element={<PosixGroupDetailPage />} />

        {/* Mixed Groups (groupOfNames + posixGroup) */}
        <Route path={PLUGIN_ROUTES.POSIX.MIXED_GROUPS} element={<MixedGroupsPage />} />
        <Route path={PLUGIN_ROUTES.POSIX.MIXED_GROUP_DETAIL} element={<MixedGroupDetailPage />} />

        {/* Sudo Roles */}
        <Route path={PLUGIN_ROUTES.SUDO.ROLES} element={<SudoRolesPage />} />
        <Route path={PLUGIN_ROUTES.SUDO.ROLE_DETAIL} element={<SudoRoleDetailPage />} />

        {/* Systems */}
        <Route path={PLUGIN_ROUTES.SYSTEMS.LIST} element={<SystemsListPage />} />
        <Route path={PLUGIN_ROUTES.SYSTEMS.DETAIL} element={<SystemDetailPage />} />

        {/* DNS */}
        <Route path={PLUGIN_ROUTES.DNS.ZONES} element={<DnsZonesListPage />} />
        <Route path={PLUGIN_ROUTES.DNS.ZONE_DETAIL} element={<DnsZoneDetailPage />} />

        {/* DHCP */}
        <Route path={PLUGIN_ROUTES.DHCP.SERVICES} element={<DhcpServicesListPage />} />
        <Route path={PLUGIN_ROUTES.DHCP.SERVICE_DETAIL} element={<DhcpServiceDetailPage />} />
        <Route path={PLUGIN_ROUTES.DHCP.SUBNET_DETAIL} element={<DhcpSubnetDetailPage />} />
        <Route path={PLUGIN_ROUTES.DHCP.HOST_DETAIL} element={<DhcpHostDetailPage />} />

        {/* ACL Management */}
        <Route path={ROUTES.ACL_POLICIES} element={<AclPoliciesListPage />} />
        <Route path={ROUTES.ACL_POLICY_CREATE} element={<AclPolicyCreatePage />} />
        <Route path={ROUTES.ACL_POLICY_DETAIL} element={<AclPolicyDetailPage />} />
        <Route path={ROUTES.ACL_ASSIGNMENTS} element={<AclAssignmentsListPage />} />
        <Route path={ROUTES.ACL_ASSIGNMENT_CREATE} element={<AclAssignmentCreatePage />} />
        <Route path={ROUTES.ACL_PERMISSIONS} element={<AclPermissionsListPage />} />
        <Route path={ROUTES.ACL_ATTR_GROUPS} element={<AclAttrGroupsListPage />} />
        <Route path={ROUTES.ACL_MATRIX} element={<AclAccessMatrixPage />} />
        <Route path={ROUTES.ACL_AUDIT} element={<AclAuditLogPage />} />

        {/* Profile */}
        <Route path={ROUTES.PROFILE} element={<ProfilePage />} />

        {/* Settings */}
        <Route path={ROUTES.SETTINGS} element={<SettingsPage />} />
      </Route>

      {/* Redirects */}
      <Route path={ROUTES.HOME} element={<Navigate to={ROUTES.DASHBOARD} replace />} />
      <Route path="*" element={<Navigate to={ROUTES.DASHBOARD} replace />} />
    </Routes>
  )
}
