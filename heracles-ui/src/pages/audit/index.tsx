import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ScrollText,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Filter,
  Download,
  Search,
  RefreshCw,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { DataTable, SortableHeader, type ColumnDef } from '@/components/common/data-table'
import { PageHeader, ErrorDisplay } from '@/components/common'
import { auditApi } from '@/lib/api/audit'
import { exportToCsv } from '@/lib/export'
import type { GeneralAuditEntry, GeneralAuditFilters } from '@/types/audit'

const ENTITY_TYPES = [
  { value: 'user', label: 'Users' },
  { value: 'group', label: 'Groups' },
  { value: 'role', label: 'Roles' },
  { value: 'department', label: 'Departments' },
  { value: 'system', label: 'Systems' },
  { value: 'dns_zone', label: 'DNS Zones' },
  { value: 'dhcp_service', label: 'DHCP' },
  { value: 'sudo_role', label: 'Sudo Roles' },
  { value: 'template', label: 'Templates' },
  { value: 'config', label: 'Config' },
  { value: 'acl_policy', label: 'ACL Policies' },
  { value: 'session', label: 'Sessions' },
]

const ACTIONS = [
  { value: 'create', label: 'Create' },
  { value: 'update', label: 'Update' },
  { value: 'delete', label: 'Delete' },
  { value: 'login', label: 'Login' },
  { value: 'logout', label: 'Logout' },
  { value: 'export', label: 'Export' },
  { value: 'import', label: 'Import' },
  { value: 'password_change', label: 'Password Change' },
]

const ACTION_COLORS: Record<string, string> = {
  create: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  update: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  delete: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  login: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  logout: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
  export: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
  import: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
  password_change: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
}

export function AuditPage() {
  const [filters, setFilters] = useState<GeneralAuditFilters>({
    page: 1,
    page_size: 50,
  })
  const [showFilters, setShowFilters] = useState(false)
  const [searchInput, setSearchInput] = useState('')
  const [actorInput, setActorInput] = useState('')
  const [entityTypeFilter, setEntityTypeFilter] = useState<string>('')
  const [actionFilter, setActionFilter] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('')

  const activeFilters: GeneralAuditFilters = {
    ...filters,
    search: searchInput || undefined,
    actor_dn: actorInput || undefined,
    entity_type: entityTypeFilter || undefined,
    action: actionFilter || undefined,
    status: statusFilter || undefined,
  }

  const { data, isLoading, isFetching, error, refetch } = useQuery({
    queryKey: ['audit-logs', activeFilters],
    queryFn: () => auditApi.listLogs(activeFilters),
  })

  const applyFilters = () => {
    setFilters((prev) => ({
      ...prev,
      page: 1,
      search: searchInput || undefined,
      actor_dn: actorInput || undefined,
      entity_type: entityTypeFilter || undefined,
      action: actionFilter || undefined,
      status: statusFilter || undefined,
    }))
  }

  const clearFilters = () => {
    setSearchInput('')
    setActorInput('')
    setEntityTypeFilter('')
    setActionFilter('')
    setStatusFilter('')
    setFilters({ page: 1, page_size: 50 })
  }

  const handleExport = () => {
    if (!data?.entries.length) return
    exportToCsv({
      data: data.entries.map((e) => ({
        timestamp: e.timestamp,
        actor: e.actor_dn,
        action: e.action,
        entityType: e.entity_type,
        entityName: e.entity_name || '',
        entityId: e.entity_id || '',
        status: e.status,
      })),
      filename: `heracles-audit-${new Date().toISOString().slice(0, 10)}.csv`,
    })
  }

  const shortDn = (dn: string | null | undefined) => {
    if (!dn) return '—'
    const first = dn.split(',')[0]
    return first || dn
  }

  const columns: ColumnDef<GeneralAuditEntry>[] = [
    {
      accessorKey: 'timestamp',
      header: ({ column }) => (
        <SortableHeader column={column}>Timestamp</SortableHeader>
      ),
      cell: ({ row }) => (
        <span className="text-sm font-mono whitespace-nowrap">
          {new Date(row.original.timestamp).toLocaleString()}
        </span>
      ),
    },
    {
      accessorKey: 'actor_dn',
      header: 'Actor',
      cell: ({ row }) => (
        <Tooltip>
          <TooltipTrigger>
            <span className="font-mono text-sm">{shortDn(row.original.actor_dn)}</span>
          </TooltipTrigger>
          <TooltipContent className="max-w-md break-all">
            {row.original.actor_dn}
          </TooltipContent>
        </Tooltip>
      ),
    },
    {
      accessorKey: 'action',
      header: 'Action',
      cell: ({ row }) => {
        const color = ACTION_COLORS[row.original.action] || 'bg-gray-100 text-gray-800'
        return (
          <Badge className={color} variant="outline">
            {row.original.action}
          </Badge>
        )
      },
    },
    {
      accessorKey: 'entity_type',
      header: 'Type',
      cell: ({ row }) => (
        <Badge variant="secondary">{row.original.entity_type}</Badge>
      ),
    },
    {
      accessorKey: 'entity_name',
      header: 'Entity',
      cell: ({ row }) => (
        <Tooltip>
          <TooltipTrigger>
            <span className="text-sm font-medium">
              {row.original.entity_name || shortDn(row.original.entity_id)}
            </span>
          </TooltipTrigger>
          <TooltipContent className="max-w-md break-all">
            {row.original.entity_id || 'N/A'}
          </TooltipContent>
        </Tooltip>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => {
        const s = row.original.status
        if (s === 'success') {
          return (
            <div className="flex items-center gap-1 text-green-600">
              <CheckCircle className="h-4 w-4" />
              <span className="text-xs font-medium">Success</span>
            </div>
          )
        }
        if (s === 'failure') {
          return (
            <Tooltip>
              <TooltipTrigger>
                <div className="flex items-center gap-1 text-red-600">
                  <XCircle className="h-4 w-4" />
                  <span className="text-xs font-medium">Failed</span>
                </div>
              </TooltipTrigger>
              <TooltipContent>{row.original.error_message}</TooltipContent>
            </Tooltip>
          )
        }
        return (
          <div className="flex items-center gap-1 text-amber-600">
            <AlertTriangle className="h-4 w-4" />
            <span className="text-xs font-medium">{s}</span>
          </div>
        )
      },
    },
    {
      accessorKey: 'changes',
      header: 'Details',
      cell: ({ row }) =>
        row.original.changes ? (
          <Tooltip>
            <TooltipTrigger>
              <Badge variant="outline" className="text-xs cursor-pointer">
                Changes
              </Badge>
            </TooltipTrigger>
            <TooltipContent className="max-w-lg">
              <pre className="text-xs whitespace-pre-wrap max-h-64 overflow-auto">
                {JSON.stringify(row.original.changes, null, 2)}
              </pre>
            </TooltipContent>
          </Tooltip>
        ) : (
          <span className="text-muted-foreground">—</span>
        ),
    },
  ]

  if (error) {
    return <ErrorDisplay message={(error as Error).message} onRetry={() => refetch()} />
  }

  return (
    <div>
      <PageHeader
        title="Audit Log"
        description="Complete audit trail of all operations across the system"
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
              <RefreshCw className={`mr-2 h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button variant="outline" size="sm" onClick={handleExport} disabled={!data?.entries.length}>
              <Download className="mr-2 h-4 w-4" />
              Export CSV
            </Button>
          </div>
        }
      />

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <ScrollText className="h-5 w-5" />
              Activity Timeline
              <Badge variant="secondary">{data?.total || 0}</Badge>
            </CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
            >
              <Filter className="mr-2 h-3 w-3" />
              Filters
            </Button>
          </div>

          {showFilters && (
            <div className="pt-4 space-y-3">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                <div className="space-y-1">
                  <label className="text-xs font-medium">Search</label>
                  <div className="relative">
                    <Search className="absolute left-2 top-2 h-3 w-3 text-muted-foreground" />
                    <Input
                      placeholder="Entity name or actor..."
                      value={searchInput}
                      onChange={(e) => setSearchInput(e.target.value)}
                      className="h-8 pl-7"
                    />
                  </div>
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium">Actor DN</label>
                  <Input
                    placeholder="Filter by actor..."
                    value={actorInput}
                    onChange={(e) => setActorInput(e.target.value)}
                    className="h-8"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium">Entity Type</label>
                  <Select value={entityTypeFilter} onValueChange={setEntityTypeFilter}>
                    <SelectTrigger className="h-8">
                      <SelectValue placeholder="All types" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All types</SelectItem>
                      {ENTITY_TYPES.map((t) => (
                        <SelectItem key={t.value} value={t.value}>
                          {t.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium">Action</label>
                  <Select value={actionFilter} onValueChange={setActionFilter}>
                    <SelectTrigger className="h-8">
                      <SelectValue placeholder="All actions" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All actions</SelectItem>
                      {ACTIONS.map((a) => (
                        <SelectItem key={a.value} value={a.value}>
                          {a.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium">Status</label>
                  <Select value={statusFilter} onValueChange={setStatusFilter}>
                    <SelectTrigger className="h-8">
                      <SelectValue placeholder="Any" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Any</SelectItem>
                      <SelectItem value="success">Success</SelectItem>
                      <SelectItem value="failure">Failed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="ghost" size="sm" onClick={clearFilters}>
                  Clear
                </Button>
                <Button size="sm" onClick={applyFilters}>
                  Apply Filters
                </Button>
              </div>
            </div>
          )}
        </CardHeader>
        <CardContent>
          <DataTable
            columns={columns}
            data={data?.entries ?? []}
            isLoading={isLoading}
            emptyMessage="No audit log entries found"
            getRowId={(row) => String(row.id)}
          />
          {data && data.has_more && (
            <div className="flex justify-center pt-4">
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  setFilters((prev) => ({ ...prev, page: (prev.page || 1) + 1 }))
                }
              >
                Load more
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
