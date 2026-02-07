/**
 * Systems Table Component
 *
 * Displays systems in a sortable, filterable table using DataTable.
 */

import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  Server,
  Monitor,
  MonitorSmartphone,
  Printer,
  Cpu,
  Phone,
  Smartphone,
  Edit,
  Trash2,
  MapPin,
  Network,
} from 'lucide-react'

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
import { systemDetailPath } from '@/config/routes'
import type { SystemListItem, SystemType, LockMode } from '@/types/systems'
import { SYSTEM_TYPE_LABELS, LOCK_MODE_LABELS } from '@/types/systems'

// Icon mapping
const SystemTypeIcon: Record<SystemType, React.ElementType> = {
  server: Server,
  workstation: Monitor,
  terminal: MonitorSmartphone,
  printer: Printer,
  component: Cpu,
  phone: Phone,
  mobile: Smartphone,
}

// Mode badge variants
const modeBadgeVariant: Record<
  LockMode,
  'default' | 'secondary' | 'destructive' | 'outline'
> = {
  unlocked: 'default',
  locked: 'destructive',
}

interface SystemsTableProps {
  systems: SystemListItem[]
  isLoading?: boolean
  onDelete?: (system: SystemListItem) => void
  emptyMessage?: string
}

export function SystemsTable({
  systems,
  isLoading = false,
  onDelete,
  emptyMessage = 'No systems found',
}: SystemsTableProps) {
  const columns = useMemo<ColumnDef<SystemListItem>[]>(
    () => [
      {
        accessorKey: 'systemType',
        header: 'Type',
        cell: ({ row }) => {
          const Icon = SystemTypeIcon[row.original.systemType]
          return (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span>
                    <Icon className="h-5 w-5 text-muted-foreground" />
                  </span>
                </TooltipTrigger>
                <TooltipContent>
                  {SYSTEM_TYPE_LABELS[row.original.systemType]}
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )
        },
        enableSorting: false,
        size: 60,
      },
      {
        accessorKey: 'cn',
        header: ({ column }) => (
          <SortableHeader column={column}>Hostname</SortableHeader>
        ),
        cell: ({ row }) => (
          <div>
            <Link
              to={systemDetailPath(row.original.systemType, row.original.cn)}
              className="font-medium hover:underline text-primary"
            >
              {row.original.cn}
            </Link>
            {row.original.description && (
              <p className="text-xs text-muted-foreground mt-1 truncate max-w-xs">
                {row.original.description}
              </p>
            )}
          </div>
        ),
      },
      {
        accessorKey: 'ipHostNumber',
        header: () => (
          <div className="flex items-center gap-1">
            <Network className="h-4 w-4" />
            IP Address
          </div>
        ),
        cell: ({ row }) => {
          const ips = row.original.ipHostNumber
          const primaryIp = ips?.[0]
          const additionalIps = (ips?.length ?? 0) - 1

          if (!primaryIp) {
            return <span className="text-muted-foreground">-</span>
          }

          return (
            <div className="flex items-center gap-1">
              <code className="text-sm">{primaryIp}</code>
              {additionalIps > 0 && (
                <Badge variant="outline" className="text-xs">
                  +{additionalIps}
                </Badge>
              )}
            </div>
          )
        },
        enableSorting: false,
      },
      {
        accessorKey: 'l',
        header: () => (
          <div className="flex items-center gap-1">
            <MapPin className="h-4 w-4" />
            Location
          </div>
        ),
        cell: ({ row }) => {
          const location = row.original.l
          if (!location) {
            return <span className="text-muted-foreground">-</span>
          }
          return (
            <span className="truncate max-w-32 text-muted-foreground">
              {location}
            </span>
          )
        },
        enableSorting: false,
      },
      {
        accessorKey: 'hrcMode',
        header: 'Status',
        cell: ({ row }) => {
          const mode = row.original.hrcMode
          if (!mode) return null
          return (
            <Badge variant={modeBadgeVariant[mode]}>
              {LOCK_MODE_LABELS[mode]}
            </Badge>
          )
        },
        enableSorting: false,
      },
      {
        id: 'actions',
        header: () => <span className="sr-only">Actions</span>,
        cell: ({ row }) => (
          <div className="flex items-center justify-end gap-1">
            <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
              <Link
                to={systemDetailPath(row.original.systemType, row.original.cn)}
              >
                <Edit className="h-4 w-4" />
                <span className="sr-only">Edit {row.original.cn}</span>
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
                <span className="sr-only">Delete {row.original.cn}</span>
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
      data={systems}
      isLoading={isLoading}
      getRowId={(row) => `${row.systemType}-${row.cn}`}
      emptyMessage={emptyMessage}
      emptyDescription="Create a new system to get started"
      emptyIcon={<Server className="h-8 w-8 text-muted-foreground" />}
      enableSearch
      searchPlaceholder="Search systems..."
      searchColumn="cn"
      enablePagination
      defaultPageSize={10}
      enableSelection
      enableColumnVisibility
      enableExport
      exportFilename="systems"
    />
  )
}
