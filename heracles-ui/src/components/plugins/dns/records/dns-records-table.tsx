/**
 * DNS Records Table Component
 *
 * Displays DNS records in a sortable, filterable table.
 */

import { useMemo } from 'react'
import { Edit, Trash2, Globe } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

import {
  DataTable,
  SortableHeader,
  type ColumnDef,
} from '@/components/common/data-table'
import type { DnsRecord, RecordType } from '@/types/dns'
import { recordRequiresPriority } from '@/types/dns'

// Record type badge variants
const recordTypeBadgeVariant: Record<
  RecordType,
  'default' | 'secondary' | 'outline' | 'destructive'
> = {
  A: 'default',
  AAAA: 'default',
  MX: 'secondary',
  NS: 'secondary',
  CNAME: 'outline',
  PTR: 'outline',
  TXT: 'outline',
  SRV: 'secondary',
}

interface DnsRecordsTableProps {
  records: DnsRecord[]
  isLoading?: boolean
  onEdit?: (record: DnsRecord) => void
  onDelete?: (record: DnsRecord) => void
  emptyMessage?: string
}

export function DnsRecordsTable({
  records,
  isLoading = false,
  onEdit,
  onDelete,
  emptyMessage = 'No records found',
}: DnsRecordsTableProps) {
  const columns = useMemo<ColumnDef<DnsRecord>[]>(
    () => [
      {
        accessorKey: 'name',
        header: ({ column }) => (
          <SortableHeader column={column}>Name</SortableHeader>
        ),
        cell: ({ row }) => (
          <code className="font-mono text-sm">
            {row.original.name === '@' ? (
              <span className="text-muted-foreground">(zone apex)</span>
            ) : (
              row.original.name
            )}
          </code>
        ),
      },
      {
        accessorKey: 'recordType',
        header: 'Type',
        cell: ({ row }) => (
          <Badge variant={recordTypeBadgeVariant[row.original.recordType]}>
            {row.original.recordType}
          </Badge>
        ),
        size: 80,
      },
      {
        accessorKey: 'value',
        header: 'Value',
        cell: ({ row }) => (
          <code className="font-mono text-sm break-all max-w-md">
            {row.original.value}
          </code>
        ),
      },
      {
        accessorKey: 'priority',
        header: 'Priority',
        cell: ({ row }) => {
          if (!recordRequiresPriority(row.original.recordType)) {
            return <span className="text-muted-foreground">-</span>
          }
          return (
            <span className="tabular-nums">
              {row.original.priority ?? '-'}
            </span>
          )
        },
        size: 80,
      },
      {
        accessorKey: 'ttl',
        header: 'TTL',
        cell: ({ row }) => (
          <span className="tabular-nums text-muted-foreground">
            {row.original.ttl ?? 'default'}
          </span>
        ),
        size: 80,
      },
      {
        id: 'actions',
        header: () => <span className="sr-only">Actions</span>,
        cell: ({ row }) => (
          <div className="flex items-center justify-end gap-1">
            {onEdit && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={(e) => {
                  e.stopPropagation()
                  onEdit(row.original)
                }}
              >
                <Edit className="h-4 w-4" />
                <span className="sr-only">Edit record</span>
              </Button>
            )}
            {onDelete && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-destructive hover:text-destructive"
                onClick={(e) => {
                  e.stopPropagation()
                  onDelete(row.original)
                }}
              >
                <Trash2 className="h-4 w-4" />
                <span className="sr-only">Delete record</span>
              </Button>
            )}
          </div>
        ),
        enableSorting: false,
        size: 100,
      },
    ],
    [onEdit, onDelete]
  )

  return (
    <DataTable
      columns={columns}
      data={records}
      isLoading={isLoading}
      getRowId={(row) => `${row.name}-${row.recordType}-${row.value}`}
      emptyMessage={emptyMessage}
      emptyDescription="Add a record to get started"
      emptyIcon={<Globe className="h-8 w-8 text-muted-foreground" />}
      enableSearch
      searchPlaceholder="Search records..."
      searchColumn="name"
      enablePagination
      defaultPageSize={15}
    />
  )
}
