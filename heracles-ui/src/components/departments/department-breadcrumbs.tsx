/**
 * Department Breadcrumbs Component
 *
 * Shows the current department path as clickable breadcrumbs.
 */

import { ChevronRight, Home } from 'lucide-react'
import { useDepartmentStore } from '@/stores'
import { useDepartmentTree } from '@/hooks'
import { cn } from '@/lib/utils'

export function DepartmentBreadcrumbs() {
  const { currentBase, currentPath, setCurrentBase, getDepartmentByDn } = useDepartmentStore()
  // Ensure tree is loaded for DN lookups
  useDepartmentTree()

  if (!currentBase) {
    return null
  }

  // Parse path into segments
  const pathParts = currentPath.split('/').filter((p) => p)

  // Build breadcrumb items with DNs
  // We need to reconstruct DNs from the path
  // This is a simplification - in reality we'd need to build proper DNs
  const breadcrumbs: { label: string; dn: string | null }[] = [
    { label: 'Root', dn: null },
  ]

  // Add intermediate parts if there are multiple levels
  let cumulativePath = ''
  for (const part of pathParts) {
    cumulativePath = cumulativePath ? `${cumulativePath}/${part}` : part
    // Try to find the department with this path
    const dept = getDepartmentByDn(currentBase) // We'd need better lookup logic
    breadcrumbs.push({
      label: part,
      dn: currentBase, // This should ideally be the actual DN for this level
    })
  }

  return (
    <nav className="flex items-center space-x-1 text-sm text-muted-foreground">
      {breadcrumbs.map((crumb, index) => (
        <div key={crumb.dn ?? 'root'} className="flex items-center">
          {index > 0 && <ChevronRight className="h-4 w-4 mx-1" />}
          {index === 0 ? (
            <button
              type="button"
              onClick={() => setCurrentBase(null)}
              className="flex items-center gap-1 hover:text-foreground transition-colors"
            >
              <Home className="h-3.5 w-3.5" />
              <span>Root</span>
            </button>
          ) : index === breadcrumbs.length - 1 ? (
            <span className="font-medium text-foreground">{crumb.label}</span>
          ) : (
            <button
              type="button"
              onClick={() => setCurrentBase(crumb.dn, cumulativePath)}
              className="hover:text-foreground transition-colors"
            >
              {crumb.label}
            </button>
          )}
        </div>
      ))}
    </nav>
  )
}
