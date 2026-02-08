import { create } from 'zustand'

import type { UserInfo } from '@/types'
import { authApi } from '@/lib/api'
import { useDepartmentStore } from '@/stores/department-store'
import { configApi } from '@/lib/api/config'

let cachedUsersRdn: string | null = null
let usersRdnPromise: Promise<string | null> | null = null

async function getUsersRdnFromConfig(): Promise<string | null> {
  if (cachedUsersRdn) {
    return cachedUsersRdn
  }

  if (!usersRdnPromise) {
    usersRdnPromise = configApi
      .getCategory('ldap')
      .then((category) => {
        const setting =
          category.settings.find((item) => item.key === 'users_rdn') ??
          category.settings.find((item) => item.key === 'user_rdn') ??
          category.settings.find((item) => item.key === 'userRdn')
        const value = setting?.value ?? setting?.defaultValue
        if (typeof value !== 'string' || value.trim().length === 0) {
          return null
        }
        return value.trim()
      })
      .catch(() => null)
      .finally(() => {
        usersRdnPromise = null
      })
  }

  const result = await usersRdnPromise
  if (result) {
    cachedUsersRdn = result
  }
  return result
}

function normalizeRdn(rdn: string | null): string | null {
  if (!rdn) return null
  const trimmed = rdn.trim()
  if (trimmed.length === 0) return null
  return trimmed.includes('=') ? trimmed.toLowerCase() : `ou=${trimmed.toLowerCase()}`
}

function getDepartmentContextFromDn(
  userDn: string,
  usersRdn: string | null
): { departmentDn: string | null; path: string } {
  const parts = userDn.split(',').map((part) => part.trim()).filter(Boolean)
  if (parts.length < 2) {
    return { departmentDn: null, path: '/' }
  }

  // Strip uid=... from the front.
  let rest = parts.slice(1)

  // Strip configured users container RDN if present.
  const normalizedUsersRdn = normalizeRdn(usersRdn)
  if (rest.length > 0 && normalizedUsersRdn && rest[0].toLowerCase() === normalizedUsersRdn) {
    rest = rest.slice(1)
  }

  if (rest.length === 0 || !rest[0].toLowerCase().startsWith('ou=')) {
    return { departmentDn: null, path: '/' }
  }

  const departmentDn = rest.join(',')
  const ouParts = rest
    .filter((part) => part.toLowerCase().startsWith('ou='))
    .map((part) => part.slice(3))
    .reverse()
  const path = ouParts.length > 0 ? `/${ouParts.join('/')}` : '/'

  return { departmentDn, path }
}

async function syncDepartmentContext(userDn: string) {
  const usersRdn = await getUsersRdnFromConfig()
  const { departmentDn, path } = getDepartmentContextFromDn(userDn, usersRdn)
  const departmentStore = useDepartmentStore.getState()
  if (departmentDn) {
    departmentStore.setCurrentBase(departmentDn, path)
    return
  }
  departmentStore.clearContext()
}

interface AuthState {
  user: UserInfo | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null

  // Actions
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  fetchUser: () => Promise<void>
  clearError: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true, // Start loading by default to check session
  error: null,

  login: async (username: string, password: string) => {
    set({ isLoading: true, error: null })
    try {
      await authApi.login({ username, password })
      const user = await authApi.getCurrentUser()
      await syncDepartmentContext(user.dn)
      set({ user, isAuthenticated: true, isLoading: false })
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Login failed',
        isLoading: false,
      })
      throw error
    }
  },

  logout: async () => {
    set({ isLoading: true })
    try {
      await authApi.logout()
    } catch {
      // Ignore logout errors
    } finally {
      useDepartmentStore.getState().clearContext()
      set({ user: null, isAuthenticated: false, isLoading: false })
    }
  },

  fetchUser: async () => {
    set({ isLoading: true })
    try {
      const user = await authApi.getCurrentUser()
      await syncDepartmentContext(user.dn)
      set({ user, isAuthenticated: true, isLoading: false })
    } catch {
      set({ user: null, isAuthenticated: false, isLoading: false })
    }
  },

  clearError: () => set({ error: null }),
}))
