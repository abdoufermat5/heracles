/**
 * Department Breadcrumbs Component
 *
 * Shows the current department path as clickable breadcrumbs.
 */

import { ChevronRight } from 'lucide-react'
import { useDepartmentStore } from '@/stores'
import { useDepartmentTree } from '@/hooks'

export function DepartmentBreadcrumbs() {
  const { currentBase, currentPath, setCurrentBase, flatList } = useDepartmentStore()
  // Ensure tree is loaded for DN lookups
  useDepartmentTree()

  if (!currentBase) {
    return null
  }

  // Parse path into segments
  const pathParts = currentPath.split('/').filter((p) => p)

  // Build breadcrumb items with DNs
  // We reconstruct DNs by looking up departments in flatList by their ou name
  const breadcrumbs: { label: string; dn: string | null; path: string }[] = [
    { label: '/', dn: null, path: '' },
  ]

  // Build cumulative paths and find matching DNs by ou name
  let cumulativePath = ''
  for (const part of pathParts) {
    cumulativePath = cumulativePath ? `${cumulativePath}/${part}` : part

    // Find department with this ou in flatList
    // The ou should match the part name
    const dept = flatList.find(d => d.ou === part && d.path === cumulativePath)

    if (dept) {
      breadcrumbs.push({
        label: part,
        dn: dept.dn,
        path: cumulativePath,
      })
    } else {
      // Fallback: try to find just by ou name
      const deptByOu = flatList.find(d => d.ou === part)
      breadcrumbs.push({
        label: part,
        dn: deptByOu?.dn ?? null,
        path: cumulativePath,
      })
    }
  }

  return (
    <nav className="flex items-center space-x-1 text-sm text-muted-foreground">
      {breadcrumbs.map((crumb, index) => (
        <div key={crumb.path || 'root'} className="flex items-center">
          {index > 0 && <ChevronRight className="h-4 w-4 mx-1" />}
          {index === breadcrumbs.length - 1 ? (
            // Current/last item - not clickable
            <span className="font-medium text-foreground">{crumb.label}</span>
          ) : crumb.dn === null ? (
            // Root item
            <button
              type="button"
              onClick={() => setCurrentBase(null)}
              className="hover:text-foreground transition-colors font-mono"
            >
              {crumb.label}
            </button>
          ) : (
            // Clickable parent item with valid DN
            <button
              type="button"
              onClick={() => setCurrentBase(crumb.dn, crumb.path)}
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
