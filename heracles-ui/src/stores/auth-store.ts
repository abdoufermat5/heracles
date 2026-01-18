import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { UserInfo } from '@/types'
import { authApi } from '@/lib/api'

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

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (username: string, password: string) => {
        set({ isLoading: true, error: null })
        try {
          await authApi.login({ username, password })
          const user = await authApi.getCurrentUser()
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
          set({ user: null, isAuthenticated: false, isLoading: false })
        }
      },

      fetchUser: async () => {
        if (!get().isAuthenticated) return
        
        set({ isLoading: true })
        try {
          const user = await authApi.getCurrentUser()
          set({ user, isLoading: false })
        } catch {
          set({ user: null, isAuthenticated: false, isLoading: false })
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'heracles-auth',
      partialize: (state) => ({
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
