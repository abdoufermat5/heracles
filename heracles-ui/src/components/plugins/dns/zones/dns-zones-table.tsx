/**
 * DNS Zones Table Component
 *
 * Displays DNS zones in a sortable, filterable table.
 */

import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Globe, ArrowRightLeft, Edit, Trash2, FileText } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

import {
  DataTable,
  SortableHeader,
  type ColumnDef,
} from '@/components/common/data-table'
import type { DnsZoneListItem, ZoneType } from '@/types/dns'
import { ZONE_TYPE_LABELS } from '@/types/dns'

// Zone type badge variants
const zoneTypeBadgeVariant: Record<
  ZoneType,
  'default' | 'secondary' | 'outline'
> = {
  forward: 'default',
  'reverse-ipv4': 'secondary',
  'reverse-ipv6': 'outline',
}

interface DnsZonesTableProps {
  zones: DnsZoneListItem[]
  isLoading?: boolean
  onDelete?: (zone: DnsZoneListItem) => void
  emptyMessage?: string
}

export function DnsZonesTable({
  zones,
  isLoading = false,
  onDelete,
  emptyMessage = 'No DNS zones found',
}: DnsZonesTableProps) {
  const columns = useMemo<ColumnDef<DnsZoneListItem>[]>(
    () => [
      {
        accessorKey: 'zoneType',
        header: 'Type',
        cell: ({ row }) => {
          const zoneType = row.original.zoneType
          const isReverse = zoneType.startsWith('reverse')
          const Icon = isReverse ? ArrowRightLeft : Globe
          return (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span>
                    <Icon className="h-5 w-5 text-muted-foreground" />
                  </span>
                </TooltipTrigger>
                <TooltipContent>{ZONE_TYPE_LABELS[zoneType]}</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )
        },
        enableSorting: false,
        size: 60,
      },
      {
        accessorKey: 'zoneName',
        header: ({ column }) => (
          <SortableHeader column={column}>Zone Name</SortableHeader>
        ),
        cell: ({ row }) => (
          <div>
            <Link
              to={`/dns/${encodeURIComponent(row.original.zoneName)}`}
              className="font-medium hover:underline text-primary font-mono"
            >
              {row.original.zoneName}
            </Link>
          </div>
        ),
      },
      {
        accessorKey: 'zoneType',
        id: 'zoneTypeLabel',
        header: 'Zone Type',
        cell: ({ row }) => (
          <Badge variant={zoneTypeBadgeVariant[row.original.zoneType]}>
            {ZONE_TYPE_LABELS[row.original.zoneType]}
          </Badge>
        ),
        enableSorting: false,
      },
      {
        accessorKey: 'recordCount',
        header: () => (
          <div className="flex items-center gap-1">
            <FileText className="h-4 w-4" />
            Records
          </div>
        ),
        cell: ({ row }) => (
          <span className="tabular-nums">{row.original.recordCount}</span>
        ),
        enableSorting: false,
      },
      {
        id: 'actions',
        header: () => <span className="sr-only">Actions</span>,
        cell: ({ row }) => (
          <div className="flex items-center justify-end gap-1">
            <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
              <Link to={`/dns/${encodeURIComponent(row.original.zoneName)}`}>
                <Edit className="h-4 w-4" />
                <span className="sr-only">Edit {row.original.zoneName}</span>
              </Link>
            </Button>
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
                <span className="sr-only">Delete {row.original.zoneName}</span>
              </Button>
            )}
          </div>
        ),
        enableSorting: false,
        size: 100,
      },
    ],
    [onDelete]
  )

  return (
    <DataTable
      columns={columns}
      data={zones}
      isLoading={isLoading}
      getRowId={(row) => row.zoneName}
      emptyMessage={emptyMessage}
      emptyDescription="Create a DNS zone to get started"
      emptyIcon={<Globe className="h-8 w-8 text-muted-foreground" />}
      enableSearch
      searchPlaceholder="Search zones..."
      searchColumn="zoneName"
      enablePagination
      defaultPageSize={10}
      enableSelection
      enableColumnVisibility
      enableExport
      exportFilename="dns-zones"
    />
  )
}
