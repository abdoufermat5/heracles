/**
 * ACL Attribute Groups Browser Page
 *
 * Lists all registered attribute groups organized by object type,
 * showing which attributes each group contains and its source (core/plugin).
 */

import { useMemo, useState } from 'react'
import { Layers, Search, Tag, Plug } from 'lucide-react'
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { PageHeader, ListPageSkeleton, ErrorDisplay } from '@/components/common'
import { useAclAttributeGroups } from '@/hooks'

const OBJECT_TYPE_LABELS: Record<string, string> = {
  user: 'User',
  group: 'Group',
  role: 'Role',
  department: 'Department',
  system: 'System',
  'dns-zone': 'DNS Zone',
  'dns-record': 'DNS Record',
  'dhcp-service': 'DHCP Service',
  'dhcp-subnet': 'DHCP Subnet',
  'dhcp-host': 'DHCP Host',
  'sudo-role': 'Sudo Role',
  'posix-group': 'POSIX Group',
  'mail-account': 'Mail Account',
}

export function AclAttrGroupsListPage() {
  const [search, setSearch] = useState('')
  const [objectTypeFilter, setObjectTypeFilter] = useState<string>('all')

  const { data: groups, isLoading, error, refetch } = useAclAttributeGroups()

  // Unique object types for filter dropdown
  const objectTypes = useMemo(() => {
    if (!groups) return []
    const types = new Set(groups.map((g) => g.objectType))
    return Array.from(types).sort()
  }, [groups])

  const filtered = useMemo(() => {
    if (!groups) return []
    return groups.filter((g) => {
      // Object type filter
      if (objectTypeFilter !== 'all' && g.objectType !== objectTypeFilter) return false
      // Text search
      if (!search) return true
      const q = search.toLowerCase()
      return (
        g.groupName.toLowerCase().includes(q) ||
        g.label.toLowerCase().includes(q) ||
        g.objectType.toLowerCase().includes(q) ||
        (g.plugin ?? '').toLowerCase().includes(q) ||
        g.attributes.some((a) => a.toLowerCase().includes(q))
      )
    })
  }, [groups, search, objectTypeFilter])

  // Group by object type for display
  const grouped = useMemo(() => {
    const map: Record<string, typeof filtered> = {}
    for (const g of filtered) {
      if (!map[g.objectType]) map[g.objectType] = []
      map[g.objectType].push(g)
    }
    for (const ot of Object.keys(map)) {
      map[ot].sort((a, b) => a.groupName.localeCompare(b.groupName))
    }
    return map
  }, [filtered])

  const objectTypeOrder = Object.keys(grouped).sort()

  if (isLoading) return <ListPageSkeleton />
  if (error) return <ErrorDisplay message={error.message} onRetry={() => refetch()} />

  return (
    <div>
      <PageHeader
        title="ACL Attribute Groups"
        description="Browse attribute groups that define fine-grained field-level access control"
      />

      <div className="mb-6 flex items-center gap-3">
        <div className="relative max-w-sm flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search groups or attributes..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={objectTypeFilter} onValueChange={setObjectTypeFilter}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="All Object Types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Object Types</SelectItem>
            {objectTypes.map((ot) => (
              <SelectItem key={ot} value={ot}>
                {OBJECT_TYPE_LABELS[ot] ?? ot}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Badge variant="secondary">{filtered.length} groups</Badge>
      </div>

      <div className="space-y-6">
        {objectTypeOrder.map((objectType) => (
          <Card key={objectType}>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Layers className="h-4 w-4" />
                {OBJECT_TYPE_LABELS[objectType] ?? objectType}
                <Badge variant="outline">{grouped[objectType].length} groups</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">ID</TableHead>
                    <TableHead className="w-40">Group Name</TableHead>
                    <TableHead className="w-48">Label</TableHead>
                    <TableHead>Attributes</TableHead>
                    <TableHead className="w-24">Source</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {grouped[objectType].map((group) => (
                    <TableRow key={group.id}>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {group.id}
                      </TableCell>
                      <TableCell className="font-medium font-mono text-sm">
                        {group.groupName}
                      </TableCell>
                      <TableCell>{group.label}</TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {group.attributes.map((attr) => (
                            <Badge key={attr} variant="outline" className="text-xs font-mono">
                              <Tag className="mr-1 h-2.5 w-2.5" />
                              {attr}
                            </Badge>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={group.plugin ? 'secondary' : 'outline'}
                          className="text-xs"
                        >
                          {group.plugin ? (
                            <>
                              <Plug className="mr-1 h-3 w-3" />
                              {group.plugin}
                            </>
                          ) : (
                            'core'
                          )}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        ))}

        {objectTypeOrder.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            No attribute groups match your search
          </div>
        )}
      </div>
    </div>
  )
}
