/**
 * ACL Permissions Browser Page
 *
 * Displays all registered permissions grouped by scope (object type),
 * showing which plugin defines each permission.
 */

import { useMemo, useState } from 'react'
import { Key, Search, Plug } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { PageHeader, LoadingPage, ErrorDisplay } from '@/components/common'
import { useAclPermissions } from '@/hooks'
import type { AclPermission } from '@/types/acl'

/** Group permissions by scope. */
function groupByScope(permissions: AclPermission[]) {
  const groups: Record<string, AclPermission[]> = {}
  for (const perm of permissions) {
    if (!groups[perm.scope]) groups[perm.scope] = []
    groups[perm.scope].push(perm)
  }
  // Sort each group by action
  for (const scope of Object.keys(groups)) {
    groups[scope].sort((a, b) => a.action.localeCompare(b.action))
  }
  return groups
}

const SCOPE_LABELS: Record<string, string> = {
  user: 'Users',
  group: 'Groups',
  role: 'Roles',
  department: 'Departments',
  config: 'Configuration',
  acl: 'Access Control',
  audit: 'Audit',
  posix: 'POSIX',
  sudo: 'Sudo',
  ssh: 'SSH',
  systems: 'Systems',
  dns: 'DNS',
  dhcp: 'DHCP',
  mail: 'Mail',
}

export function AclPermissionsListPage() {
  const [search, setSearch] = useState('')
  const { data: permissions, isLoading, error, refetch } = useAclPermissions()

  const filtered = useMemo(() => {
    if (!permissions) return []
    if (!search) return permissions
    const q = search.toLowerCase()
    return permissions.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.description.toLowerCase().includes(q) ||
        p.scope.toLowerCase().includes(q) ||
        (p.plugin ?? '').toLowerCase().includes(q)
    )
  }, [permissions, search])

  const grouped = useMemo(() => groupByScope(filtered), [filtered])
  const scopeOrder = Object.keys(grouped).sort((a, b) => {
    // Core scopes first, then plugins alphabetically
    const coreScopes = ['user', 'group', 'role', 'department', 'config', 'acl', 'audit']
    const aIdx = coreScopes.indexOf(a)
    const bIdx = coreScopes.indexOf(b)
    if (aIdx !== -1 && bIdx !== -1) return aIdx - bIdx
    if (aIdx !== -1) return -1
    if (bIdx !== -1) return 1
    return a.localeCompare(b)
  })

  if (isLoading) return <LoadingPage message="Loading permissions..." />
  if (error) return <ErrorDisplay message={error.message} onRetry={() => refetch()} />

  return (
    <div>
      <PageHeader
        title="ACL Permissions"
        description="Browse all registered permissions from core and plugins"
      />

      <div className="mb-6 flex items-center gap-3">
        <div className="relative max-w-sm flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search permissions..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Badge variant="secondary">{filtered.length} permissions</Badge>
      </div>

      <div className="space-y-6">
        {scopeOrder.map((scope) => (
          <Card key={scope}>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Key className="h-4 w-4" />
                {SCOPE_LABELS[scope] ?? scope}
                <Badge variant="outline">{grouped[scope].length}</Badge>
                {grouped[scope][0]?.plugin && (
                  <Badge variant="secondary" className="ml-1 text-xs">
                    <Plug className="mr-1 h-3 w-3" />
                    {grouped[scope][0].plugin}
                  </Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">Bit</TableHead>
                    <TableHead className="w-48">Permission</TableHead>
                    <TableHead className="w-24">Action</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead className="w-24">Source</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {grouped[scope].map((perm) => (
                    <TableRow key={perm.bitPosition}>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {perm.bitPosition}
                      </TableCell>
                      <TableCell className="font-medium font-mono text-sm">
                        {perm.name}
                      </TableCell>
                      <TableCell>
                        <Badge variant={actionVariant(perm.action)}>
                          {perm.action}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {perm.description}
                      </TableCell>
                      <TableCell>
                        <Badge variant={perm.plugin ? 'secondary' : 'outline'} className="text-xs">
                          {perm.plugin ?? 'core'}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        ))}

        {scopeOrder.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            No permissions match your search
          </div>
        )}
      </div>
    </div>
  )
}

function actionVariant(action: string) {
  switch (action) {
    case 'read': return 'default' as const
    case 'write': return 'secondary' as const
    case 'create': return 'secondary' as const
    case 'delete': return 'destructive' as const
    case 'manage': return 'outline' as const
    default: return 'outline' as const
  }
}
