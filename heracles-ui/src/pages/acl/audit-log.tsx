import { useState, useMemo } from 'react'
import { ScrollText, CheckCircle, XCircle, Filter } from 'lucide-react'
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
import { useAuditLogs } from '@/hooks'
import type { AuditLogEntry, AuditLogListParams } from '@/types/acl'

export function AclAuditLogPage() {
  const [filters, setFilters] = useState<AuditLogListParams>({
    page: 1,
    page_size: 50,
  })
  const [showFilters, setShowFilters] = useState(false)
  const [userDnSearch, setUserDnSearch] = useState('')
  const [targetDnSearch, setTargetDnSearch] = useState('')
  const [actionFilter, setActionFilter] = useState<string>('')
  const [resultFilter, setResultFilter] = useState<string>('')

  const currentFilters: AuditLogListParams = {
    ...filters,
    user_dn: userDnSearch || undefined,
    target_dn: targetDnSearch || undefined,
    action: actionFilter || undefined,
    result: resultFilter === 'true' ? true : resultFilter === 'false' ? false : undefined,
  }

  const { data, isLoading, error, refetch } = useAuditLogs(currentFilters)

  const applyFilters = () => {
    setFilters((prev) => ({
      ...prev,
      page: 1,
      user_dn: userDnSearch || undefined,
      target_dn: targetDnSearch || undefined,
      action: actionFilter || undefined,
      result: resultFilter === 'true' ? true : resultFilter === 'false' ? false : undefined,
    }))
  }

  const clearFilters = () => {
    setUserDnSearch('')
    setTargetDnSearch('')
    setActionFilter('')
    setResultFilter('')
    setFilters({ page: 1, page_size: 50 })
  }

  /** Extract short name from DN */
  const shortDn = (dn: string | null) => {
    if (!dn) return '—'
    const first = dn.split(',')[0]
    return first || dn
  }

  const columns = useMemo<ColumnDef<AuditLogEntry>[]>(
    () => [
      {
        accessorKey: 'ts',
        header: ({ column }) => (
          <SortableHeader column={column}>Timestamp</SortableHeader>
        ),
        cell: ({ row }) => (
          <span className="text-sm font-mono whitespace-nowrap">
            {new Date(row.original.ts).toLocaleString()}
          </span>
        ),
      },
      {
        accessorKey: 'userDn',
        header: 'User',
        cell: ({ row }) => (
          <Tooltip>
            <TooltipTrigger>
              <span className="font-mono text-sm">{shortDn(row.original.userDn)}</span>
            </TooltipTrigger>
            <TooltipContent className="max-w-md break-all">
              {row.original.userDn}
            </TooltipContent>
          </Tooltip>
        ),
      },
      {
        accessorKey: 'action',
        header: 'Action',
        cell: ({ row }) => (
          <Badge variant="outline">{row.original.action}</Badge>
        ),
      },
      {
        accessorKey: 'targetDn',
        header: 'Target',
        cell: ({ row }) => (
          <Tooltip>
            <TooltipTrigger>
              <span className="text-sm text-muted-foreground">
                {shortDn(row.original.targetDn)}
              </span>
            </TooltipTrigger>
            <TooltipContent className="max-w-md break-all">
              {row.original.targetDn || 'N/A'}
            </TooltipContent>
          </Tooltip>
        ),
      },
      {
        accessorKey: 'permission',
        header: 'Permission',
        cell: ({ row }) =>
          row.original.permission ? (
            <Badge variant="secondary" className="font-mono text-xs">
              {row.original.permission}
            </Badge>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
      },
      {
        accessorKey: 'result',
        header: 'Result',
        cell: ({ row }) => {
          if (row.original.result === null) {
            return <span className="text-muted-foreground">—</span>
          }
          return row.original.result ? (
            <div className="flex items-center gap-1 text-green-600">
              <CheckCircle className="h-4 w-4" />
              <span className="text-xs font-medium">Allowed</span>
            </div>
          ) : (
            <div className="flex items-center gap-1 text-red-600">
              <XCircle className="h-4 w-4" />
              <span className="text-xs font-medium">Denied</span>
            </div>
          )
        },
      },
      {
        accessorKey: 'details',
        header: 'Details',
        cell: ({ row }) =>
          row.original.details ? (
            <Tooltip>
              <TooltipTrigger>
                <Badge variant="outline" className="text-xs cursor-pointer">
                  JSON
                </Badge>
              </TooltipTrigger>
              <TooltipContent className="max-w-lg">
                <pre className="text-xs whitespace-pre-wrap">
                  {JSON.stringify(row.original.details, null, 2)}
                </pre>
              </TooltipContent>
            </Tooltip>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
      },
    ],
    []
  )

  if (error) {
    return <ErrorDisplay message={error.message} onRetry={() => refetch()} />
  }

  return (
    <div>
      <PageHeader
        title="Audit Log"
        description="Track all access control checks and administrative actions"
      />

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <ScrollText className="h-5 w-5" />
              Audit Entries
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
            <div className="pt-4">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <div className="space-y-1">
                  <label className="text-xs font-medium">User DN</label>
                  <Input
                    placeholder="Search user DN..."
                    value={userDnSearch}
                    onChange={(e) => setUserDnSearch(e.target.value)}
                    className="h-8"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium">Target DN</label>
                  <Input
                    placeholder="Search target DN..."
                    value={targetDnSearch}
                    onChange={(e) => setTargetDnSearch(e.target.value)}
                    className="h-8"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium">Action</label>
                  <Input
                    placeholder="e.g., check, policy_create"
                    value={actionFilter}
                    onChange={(e) => setActionFilter(e.target.value)}
                    className="h-8"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium">Result</label>
                  <Select value={resultFilter} onValueChange={setResultFilter}>
                    <SelectTrigger className="h-8">
                      <SelectValue placeholder="Any" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Any</SelectItem>
                      <SelectItem value="true">Allowed</SelectItem>
                      <SelectItem value="false">Denied</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="flex justify-end gap-2 mt-3">
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
        </CardContent>
      </Card>
    </div>
  )
}
