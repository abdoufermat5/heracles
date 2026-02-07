import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type TableDensity = 'comfortable' | 'compact'

interface TablePreferencesState {
  density: TableDensity
  setDensity: (density: TableDensity) => void
  toggleDensity: () => void
}

export const useTablePreferencesStore = create<TablePreferencesState>()(
  persist(
    (set) => ({
      density: 'comfortable',
      setDensity: (density) => set({ density }),
      toggleDensity: () =>
        set((state) => ({
          density: state.density === 'compact' ? 'comfortable' : 'compact',
        })),
    }),
    {
      name: 'heracles-table-preferences',
    }
  )
)
