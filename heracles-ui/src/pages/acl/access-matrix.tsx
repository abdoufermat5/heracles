/**
 * ACL Access Matrix Page
 *
 * Visualises "who can access what" — a cross-cutting view of all
 * active assignments. Rows are subjects (users/groups/roles),
 * columns are permission scopes, cells show allow / deny per scope.
 */

import { useMemo, useState } from 'react'
import { Grid3X3, Search, ShieldCheck, ShieldX, Minus, Info } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { PageHeader, TableSkeleton, ErrorDisplay } from '@/components/common'
import { DataTable, SortableHeader, type ColumnDef } from '@/components/common/data-table'
import { useAclAssignments, useAclPermissions, useAclPolicies } from '@/hooks'
import type { AclAssignment, AclPermission, AclPolicy } from '@/types/acl'

// ============================================================================
// Types
// ============================================================================

interface MatrixCell {
  hasAllow: boolean
  hasDeny: boolean
  details: CellDetail[]
}

interface CellDetail {
  policyName: string
  permissions: string[]
  deny: boolean
  selfOnly: boolean
  priority: number
  scopeDn: string
}

// ============================================================================
// Helpers
// ============================================================================

/** Extract a short subject label from a full DN. */
function subjectLabel(dn: string): string {
  const match = dn.match(/^(?:uid|cn)=([^,]+)/i)
  return match ? match[1] : dn
}

/** Unique scopes from the permissions list. */
function extractScopes(permissions: AclPermission[]): string[] {
  const scopes = new Set(permissions.map((p) => p.scope))
  const coreOrder = ['user', 'group', 'role', 'department', 'config', 'acl', 'audit']
  return Array.from(scopes).sort((a, b) => {
    const ai = coreOrder.indexOf(a)
    const bi = coreOrder.indexOf(b)
    if (ai !== -1 && bi !== -1) return ai - bi
    if (ai !== -1) return -1
    if (bi !== -1) return 1
    return a.localeCompare(b)
  })
}

/** Build a map from policy ID → policy name / permissions */
function buildPolicyMap(policies: AclPolicy[]) {
  const map: Record<string, AclPolicy> = {}
  for (const p of policies) map[p.id] = p
  return map
}

/** Build a map from permission name → scope */
function buildPermScopeMap(permissions: AclPermission[]) {
  const map: Record<string, string> = {}
  for (const p of permissions) map[p.name] = p.scope
  return map
}

// ============================================================================
// Matrix builder
// ============================================================================

interface MatrixRow {
  subjectDn: string
  subjectType: AclAssignment['subjectType']
  cells: Record<string, MatrixCell>
}

function buildMatrix(
  assignments: AclAssignment[],
  policyMap: Record<string, AclPolicy>,
  permScopeMap: Record<string, string>,
  scopes: string[],
): MatrixRow[] {
  // Group by subject DN
  const subjectMap: Record<string, AclAssignment[]> = {}
  for (const a of assignments) {
    if (!subjectMap[a.subjectDn]) subjectMap[a.subjectDn] = []
    subjectMap[a.subjectDn].push(a)
  }

  const rows: MatrixRow[] = []

  for (const [subjectDn, subjectAssignments] of Object.entries(subjectMap)) {
    const cells: Record<string, MatrixCell> = {}
    for (const scope of scopes) {
      cells[scope] = { hasAllow: false, hasDeny: false, details: [] }
    }

    for (const assignment of subjectAssignments) {
      const policy = policyMap[assignment.policyId]
      if (!policy) continue

      // Map this policy's permissions → scopes
      const scopePerms: Record<string, string[]> = {}
      for (const permName of policy.permissions) {
        const scope = permScopeMap[permName]
        if (!scope) continue
        if (!scopePerms[scope]) scopePerms[scope] = []
        scopePerms[scope].push(permName)
      }

      for (const [scope, perms] of Object.entries(scopePerms)) {
        if (!cells[scope]) continue
        const detail: CellDetail = {
          policyName: policy.name,
          permissions: perms,
          deny: assignment.deny,
          selfOnly: assignment.selfOnly,
          priority: assignment.priority,
          scopeDn: assignment.scopeDn,
        }
        cells[scope].details.push(detail)
        if (assignment.deny) {
          cells[scope].hasDeny = true
        } else {
          cells[scope].hasAllow = true
        }
      }
    }

    rows.push({
      subjectDn,
      subjectType: subjectAssignments[0].subjectType,
      cells,
    })
  }

  // Sort rows: users first, then groups, then roles
  const typeOrder = { user: 0, group: 1, role: 2 }
  rows.sort((a, b) => {
    const ta = typeOrder[a.subjectType] ?? 9
    const tb = typeOrder[b.subjectType] ?? 9
    if (ta !== tb) return ta - tb
    return subjectLabel(a.subjectDn).localeCompare(subjectLabel(b.subjectDn))
  })

  return rows
}

// ============================================================================
// Cell Component
// ============================================================================

function MatrixCellBadge({ cell }: { cell: MatrixCell }) {
  if (cell.details.length === 0) {
    return <Minus className="h-4 w-4 text-muted-foreground/30" />
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="flex items-center gap-1 cursor-help">
            {cell.hasAllow && (
              <ShieldCheck className="h-4 w-4 text-emerald-500" />
            )}
            {cell.hasDeny && (
              <ShieldX className="h-4 w-4 text-destructive" />
            )}
            <span className="text-xs text-muted-foreground">
              {cell.details.length}
            </span>
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="max-w-xs">
          <div className="space-y-1.5 text-xs">
            {cell.details.map((d, i) => (
              <div key={i} className="flex flex-col gap-0.5">
                <span className="font-medium">
                  {d.deny ? '⛔ Deny' : '✅ Allow'} — {d.policyName}
                </span>
                <span className="text-muted-foreground">
                  {d.permissions.join(', ')}
                </span>
                {d.selfOnly && (
                  <span className="text-amber-400">self-only</span>
                )}
              </div>
            ))}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

// ============================================================================
// Page Component
// ============================================================================

export function AclAccessMatrixPage() {
  const [search, setSearch] = useState('')
  const [subjectTypeFilter, setSubjectTypeFilter] = useState<string>('all')

  const {
    data: assignmentData,
    isLoading: assignmentsLoading,
    error: assignmentsError,
  } = useAclAssignments({ page_size: 200 })
  const {
    data: permissions,
    isLoading: permsLoading,
    error: permsError,
  } = useAclPermissions()
  const {
    data: policyData,
    isLoading: policiesLoading,
    error: policiesError,
  } = useAclPolicies({ page_size: 200 })

  const isLoading = assignmentsLoading || permsLoading || policiesLoading
  const error = assignmentsError || permsError || policiesError

  const scopes = useMemo(() => (permissions ? extractScopes(permissions) : []), [permissions])
  const policyMap = useMemo(() => (policyData ? buildPolicyMap(policyData.policies) : {}), [policyData])
  const permScopeMap = useMemo(() => (permissions ? buildPermScopeMap(permissions) : {}), [permissions])

  const allRows = useMemo(() => {
    if (!assignmentData?.assignments) return []
    return buildMatrix(assignmentData.assignments, policyMap, permScopeMap, scopes)
  }, [assignmentData, policyMap, permScopeMap, scopes])

  const filteredRows = useMemo(() => {
    return allRows.filter((row) => {
      if (subjectTypeFilter !== 'all' && row.subjectType !== subjectTypeFilter) return false
      if (!search) return true
      const q = search.toLowerCase()
      return (
        row.subjectDn.toLowerCase().includes(q) ||
        subjectLabel(row.subjectDn).toLowerCase().includes(q)
      )
    })
  }, [allRows, search, subjectTypeFilter])

  // Build columns dynamically: Subject (sortable) + Type + one column per scope
  const columns = useMemo<ColumnDef<MatrixRow>[]>(() => {
    const cols: ColumnDef<MatrixRow>[] = [
      {
        accessorKey: 'subjectDn',
        header: ({ column }) => (
          <SortableHeader column={column}>Subject</SortableHeader>
        ),
        cell: ({ row }) => (
          <span className="font-medium font-mono text-sm">
            {subjectLabel(row.original.subjectDn)}
          </span>
        ),
        sortingFn: (rowA, rowB) =>
          subjectLabel(rowA.original.subjectDn).localeCompare(
            subjectLabel(rowB.original.subjectDn),
          ),
      },
      {
        accessorKey: 'subjectType',
        header: 'Type',
        enableSorting: false,
        cell: ({ row }) => (
          <Badge variant="outline" className="text-xs">
            {row.original.subjectType}
          </Badge>
        ),
        size: 80,
      },
    ]

    for (const scope of scopes) {
      cols.push({
        id: `scope_${scope}`,
        header: () => <span className="text-center block">{scope}</span>,
        enableSorting: false,
        cell: ({ row }) => (
          <div className="flex justify-center">
            <MatrixCellBadge cell={row.original.cells[scope]} />
          </div>
        ),
        size: 80,
      })
    }

    return cols
  }, [scopes])

  if (isLoading) {
    return (
      <div className="space-y-4">
        <PageHeader
          title="Access Matrix"
          description="Visualize who can access what across the directory"
        />
        <TableSkeleton rows={8} columns={6} />
      </div>
    )
  }
  if (error) return <ErrorDisplay message={error.message} />

  return (
    <div>
      <PageHeader
        title="Access Matrix"
        description="Cross-cutting view of who can access what across all permission scopes"
      />

      <div className="mb-6 flex items-center gap-3">
        <div className="relative max-w-sm flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search subjects..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={subjectTypeFilter} onValueChange={setSubjectTypeFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="All Types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="user">Users</SelectItem>
            <SelectItem value="group">Groups</SelectItem>
            <SelectItem value="role">Roles</SelectItem>
          </SelectContent>
        </Select>
        <Badge variant="secondary">{filteredRows.length} subjects</Badge>
      </div>

      {/* Legend */}
      <Card className="mb-6">
        <CardContent className="flex items-center gap-6 py-3">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Info className="h-4 w-4" />
            Legend:
          </div>
          <div className="flex items-center gap-1.5 text-sm">
            <ShieldCheck className="h-4 w-4 text-emerald-500" />
            Allow
          </div>
          <div className="flex items-center gap-1.5 text-sm">
            <ShieldX className="h-4 w-4 text-destructive" />
            Deny
          </div>
          <div className="flex items-center gap-1.5 text-sm">
            <Minus className="h-4 w-4 text-muted-foreground/30" />
            No assignment
          </div>
          <span className="text-xs text-muted-foreground">
            Hover a cell for details
          </span>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Grid3X3 className="h-5 w-5" />
            Permission Matrix
            <Badge variant="outline">{scopes.length} scopes</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={columns}
            data={filteredRows}
            isLoading={isLoading}
            emptyMessage="No assignments to display"
            enablePagination={false}
            getRowId={(row: MatrixRow) => row.subjectDn}
            dense
          />
        </CardContent>
      </Card>
    </div>
  )
}
