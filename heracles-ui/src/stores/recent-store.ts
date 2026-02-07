import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type RecentItemType =
  | 'user'
  | 'group'
  | 'role'
  | 'department'
  | 'policy'
  | 'assignment'
  | 'system'
  | 'dns'
  | 'dhcp'

export interface RecentItem {
  id: string
  label: string
  href: string
  type: RecentItemType
  description?: string
}

interface RecentStoreState {
  items: RecentItem[]
  addItem: (item: RecentItem) => void
  clear: () => void
}

const MAX_RECENT = 10

export const useRecentStore = create<RecentStoreState>()(
  persist(
    (set) => ({
      items: [],
      addItem: (item) =>
        set((state) => {
          const filtered = state.items.filter((existing) => existing.href !== item.href)
          return { items: [item, ...filtered].slice(0, MAX_RECENT) }
        }),
      clear: () => set({ items: [] }),
    }),
    {
      name: 'heracles-recent-items',
    }
  )
)
