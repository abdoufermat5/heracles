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
import { PosixGroupsPage, PosixGroupDetailPage, MixedGroupsPage, MixedGroupDetailPage } from '@/pages/posix'
import { SudoRolesPage, SudoRoleDetailPage } from '@/pages/sudo'
import { DnsZonesListPage, DnsZoneDetailPage } from '@/pages/dns'
import { DhcpServicesListPage, DhcpServiceDetailPage, DhcpSubnetDetailPage, DhcpHostDetailPage } from '@/pages/dhcp'
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
        
        {/* Groups (organizational - groupOfNames) */}
        <Route path={ROUTES.GROUPS} element={<GroupsListPage />} />
        <Route path={ROUTES.GROUP_CREATE} element={<GroupCreatePage />} />
        <Route path={ROUTES.GROUP_DETAIL} element={<GroupDetailPage />} />

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

        {/* Settings */}
        <Route path={ROUTES.SETTINGS} element={<SettingsPage />} />
      </Route>

      {/* Redirects */}
      <Route path={ROUTES.HOME} element={<Navigate to={ROUTES.DASHBOARD} replace />} />
      <Route path="*" element={<Navigate to={ROUTES.DASHBOARD} replace />} />
    </Routes>
  )
}
