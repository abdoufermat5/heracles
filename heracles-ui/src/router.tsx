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
import { PosixGroupsPage, PosixGroupDetailPage, MixedGroupsPage } from '@/pages/posix'
import { SudoRolesPage, SudoRoleDetailPage } from '@/pages/sudo'
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
        
        {/* POSIX Groups (standalone posixGroup entries) */}
        <Route path={PLUGIN_ROUTES.POSIX.GROUPS} element={<PosixGroupsPage />} />
        <Route path={PLUGIN_ROUTES.POSIX.GROUP_DETAIL} element={<PosixGroupDetailPage />} />

        {/* Mixed Groups (groupOfNames + posixGroup) */}
        <Route path={PLUGIN_ROUTES.POSIX.MIXED_GROUPS} element={<MixedGroupsPage />} />

        {/* Sudo Roles */}
        <Route path={PLUGIN_ROUTES.SUDO.ROLES} element={<SudoRolesPage />} />
        <Route path={PLUGIN_ROUTES.SUDO.ROLE_DETAIL} element={<SudoRoleDetailPage />} />
        
        {/* Systems */}
        <Route path={PLUGIN_ROUTES.SYSTEMS.LIST} element={<SystemsListPage />} />
        <Route path={PLUGIN_ROUTES.SYSTEMS.DETAIL} element={<SystemDetailPage />} />
        
        {/* Settings */}
        <Route path={ROUTES.SETTINGS} element={<SettingsPage />} />
      </Route>

      {/* Redirects */}
      <Route path={ROUTES.HOME} element={<Navigate to={ROUTES.DASHBOARD} replace />} />
      <Route path="*" element={<Navigate to={ROUTES.DASHBOARD} replace />} />
    </Routes>
  )
}
