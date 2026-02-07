/**
 * DHCP Services Table Component
 *
 * Displays DHCP services in a sortable, filterable table using DataTable.
 */

import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  Server,
  Edit,
  Trash2,
  Network,
  Monitor,
  TreePine,
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
import type { DhcpServiceListItem } from '@/types/dhcp'

interface DhcpServicesTableProps {
  services: DhcpServiceListItem[]
  isLoading?: boolean
  onDelete?: (service: DhcpServiceListItem) => void
  onViewTree?: (serviceCn: string) => void
  emptyMessage?: string
}

export function DhcpServicesTable({
  services,
  isLoading = false,
  onDelete,
  onViewTree,
  emptyMessage = 'No DHCP services found',
}: DhcpServicesTableProps) {
  const columns = useMemo<ColumnDef<DhcpServiceListItem>[]>(
    () => [
      {
        accessorKey: 'icon',
        header: '',
        cell: () => (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <span>
                  <Server className="h-5 w-5 text-muted-foreground" />
                </span>
              </TooltipTrigger>
              <TooltipContent>DHCP Service</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        ),
        enableSorting: false,
        size: 60,
      },
      {
        accessorKey: 'cn',
        header: ({ column }) => (
          <SortableHeader column={column}>Service Name</SortableHeader>
        ),
        cell: ({ row }) => (
          <div>
            <Link
              to={`/dhcp/${row.original.cn}`}
              className="font-medium hover:underline text-primary"
            >
              {row.original.cn}
            </Link>
            {row.original.dhcpComments && (
              <p className="text-xs text-muted-foreground mt-1 truncate max-w-xs">
                {row.original.dhcpComments}
              </p>
            )}
          </div>
        ),
      },
      {
        accessorKey: 'subnetCount',
        header: () => (
          <div className="flex items-center gap-1">
            <Network className="h-4 w-4" />
            Subnets
          </div>
        ),
        cell: ({ row }) => {
          const count = row.original.subnetCount ?? 0
          return (
            <Badge variant="outline" className="text-xs">
              {count}
            </Badge>
          )
        },
        enableSorting: false,
      },
      {
        accessorKey: 'hostCount',
        header: () => (
          <div className="flex items-center gap-1">
            <Monitor className="h-4 w-4" />
            Hosts
          </div>
        ),
        cell: ({ row }) => {
          const count = row.original.hostCount ?? 0
          return (
            <Badge variant="outline" className="text-xs">
              {count}
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
            {onViewTree && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => onViewTree(row.original.cn)}
                    >
                      <TreePine className="h-4 w-4" />
                      <span className="sr-only">View tree for {row.original.cn}</span>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>View hierarchy</TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
            <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
              <Link to={`/dhcp/${row.original.cn}`}>
                <Edit className="h-4 w-4" />
                <span className="sr-only">Edit {row.original.cn}</span>
              </Link>
            </Button>
            {onDelete && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-destructive hover:text-destructive"
                onClick={() => onDelete(row.original)}
              >
                <Trash2 className="h-4 w-4" />
                <span className="sr-only">Delete {row.original.cn}</span>
              </Button>
            )}
          </div>
        ),
        enableSorting: false,
        size: 120,
      },
    ],
    [onDelete, onViewTree]
  )

  return (
    <DataTable
      columns={columns}
      data={services}
      isLoading={isLoading}
      emptyMessage={emptyMessage}
      enableSearch
      searchPlaceholder="Search services..."
      searchColumn="cn"
      enablePagination
      defaultPageSize={10}
      enableSelection
      enableColumnVisibility
      enableExport
      exportFilename="dhcp-services"
    />
  )
}
