import { create } from 'zustand'
import { persist } from 'zustand/middleware'

import type { DepartmentTreeNode } from '@/types'

interface DepartmentState {
  // Current department context
  currentBase: string | null
  currentPath: string

  // Cached department tree
  tree: DepartmentTreeNode[]
  flatList: DepartmentTreeNode[]
  lastFetched: number | null

  // Actions
  setCurrentBase: (dn: string | null, path?: string) => void
  clearContext: () => void
  setTree: (tree: DepartmentTreeNode[]) => void
  getBreadcrumbs: () => { dn: string | null; label: string }[]
  getDepartmentByDn: (dn: string) => DepartmentTreeNode | null
}

// Flatten tree into list for easier lookup
function flattenTree(nodes: DepartmentTreeNode[]): DepartmentTreeNode[] {
  const result: DepartmentTreeNode[] = []
  for (const node of nodes) {
    result.push(node)
    if (node.children && node.children.length > 0) {
      result.push(...flattenTree(node.children))
    }
  }
  return result
}

// Build breadcrumbs from path
function buildBreadcrumbs(path: string): { dn: string | null; label: string }[] {
  if (!path || path === '/') {
    return [{ dn: null, label: 'All Departments' }]
  }

  const breadcrumbs: { dn: string | null; label: string }[] = [
    { dn: null, label: 'All Departments' },
  ]

  // Path is like /Engineering/DevOps
  // We need to build intermediate breadcrumbs
  const parts = path.split('/').filter((p) => p)
  for (let i = 0; i < parts.length; i++) {
    breadcrumbs.push({
      dn: parts.slice(0, i + 1).join('/'), // Placeholder, actual DN lookup needed
      label: parts[i],
    })
  }

  return breadcrumbs
}

export const useDepartmentStore = create<DepartmentState>()(
  persist(
    (set, get) => ({
      currentBase: null,
      currentPath: '/',
      tree: [],
      flatList: [],
      lastFetched: null,

      setCurrentBase: (dn: string | null, path?: string) => {
        if (dn === null) {
          set({ currentBase: null, currentPath: '/' })
          return
        }

        // If path provided, use it; otherwise try to find it from tree
        let resolvedPath = path
        if (!resolvedPath) {
          const dept = get().getDepartmentByDn(dn)
          resolvedPath = dept?.path ?? '/'
        }

        set({ currentBase: dn, currentPath: resolvedPath })
      },

      clearContext: () => {
        set({ currentBase: null, currentPath: '/' })
      },

      setTree: (tree: DepartmentTreeNode[]) => {
        set({
          tree,
          flatList: flattenTree(tree),
          lastFetched: Date.now(),
        })
      },

      getBreadcrumbs: () => {
        const { currentPath } = get()
        return buildBreadcrumbs(currentPath)
      },

      getDepartmentByDn: (dn: string) => {
        const { flatList } = get()
        return flatList.find((d) => d.dn === dn) ?? null
      },
    }),
    {
      name: 'heracles-department-store',
      partialize: (state) => ({
        currentBase: state.currentBase,
        currentPath: state.currentPath,
      }),
    }
  )
)
