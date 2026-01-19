import { Routes, Route, Navigate } from 'react-router-dom'
import { AppLayout } from '@/components/layout'
import { ProtectedRoute } from '@/components/auth'
import {
  LoginPage,
  DashboardPage,
  UsersListPage,
  UserCreatePage,
  UserDetailPage,
  GroupsListPage,
  GroupCreatePage,
  GroupDetailPage,
  SystemsPage,
  SettingsPage,
} from '@/pages'
import { PosixGroupsPage, PosixGroupDetailPage } from '@/pages/posix'
import { ROUTES } from '@/config/constants'

export function AppRouter() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path={ROUTES.LOGIN} element={<LoginPage />} />

      {/* Protected routes */}
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
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
        <Route path="/posix/groups" element={<PosixGroupsPage />} />
        <Route path="/posix/groups/:cn" element={<PosixGroupDetailPage />} />
        
        {/* Systems */}
        <Route path={ROUTES.SYSTEMS} element={<SystemsPage />} />
        
        {/* Settings */}
        <Route path={ROUTES.SETTINGS} element={<SettingsPage />} />
      </Route>

      {/* Redirects */}
      <Route path={ROUTES.HOME} element={<Navigate to={ROUTES.DASHBOARD} replace />} />
      <Route path="*" element={<Navigate to={ROUTES.DASHBOARD} replace />} />
    </Routes>
  )
}
