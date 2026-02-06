/**
 * Permission Badges Component
 *
 * Renders a list of permissions as grouped badges.
 * Used in user/group detail pages and the profile page.
 */

import { useMemo } from 'react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ShieldCheck, ShieldX } from 'lucide-react'

interface PermissionBadgesProps {
  permissions: string[]
  compact?: boolean
}

const scopeColors: Record<string, string> = {
  user: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  group: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  role: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  department: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  config: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  acl: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  audit: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
}

export function PermissionBadges({ permissions, compact = false }: PermissionBadgesProps) {
  const grouped = useMemo(() => {
    const map = new Map<string, string[]>()
    for (const perm of permissions) {
      const [scope, action] = perm.split(':')
      const existing = map.get(scope) || []
      existing.push(action)
      map.set(scope, existing)
    }
    return map
  }, [permissions])

  if (permissions.length === 0) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <ShieldX className="h-4 w-4" />
        <span className="text-sm">No permissions</span>
      </div>
    )
  }

  if (compact) {
    return (
      <div className="flex flex-wrap gap-1">
        {permissions.map((perm) => (
          <Badge key={perm} variant="outline" className="text-xs font-mono">
            {perm}
          </Badge>
        ))}
      </div>
    )
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from(grouped.entries()).map(([scope, actions]) => (
        <Card key={scope} className="overflow-hidden">
          <CardHeader className="pb-2 pt-3 px-3">
            <CardTitle className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider">
              <ShieldCheck className="h-3.5 w-3.5" />
              {scope}
            </CardTitle>
          </CardHeader>
          <CardContent className="pb-3 px-3">
            <div className="flex flex-wrap gap-1">
              {actions.map((action) => (
                <Badge
                  key={`${scope}:${action}`}
                  className={scopeColors[scope] || 'bg-slate-100 text-slate-800 dark:bg-slate-900 dark:text-slate-200'}
                >
                  {action}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
