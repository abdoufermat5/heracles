/**
 * DHCP Subnets Table Component
 *
 * Displays DHCP subnets in a sortable, filterable table.
 */

import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  Blocks,
  Edit,
  Trash2,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
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
import type { DhcpSubnetListItem } from '@/types/dhcp'

interface DhcpSubnetsTableProps {
  serviceCn: string
  subnets: DhcpSubnetListItem[]
  isLoading?: boolean
  onDelete?: (subnet: DhcpSubnetListItem) => void
  emptyMessage?: string
}

export function DhcpSubnetsTable({
  serviceCn,
  subnets,
  isLoading = false,
  onDelete,
  emptyMessage = 'No subnets found',
}: DhcpSubnetsTableProps) {
  const columns = useMemo<ColumnDef<DhcpSubnetListItem>[]>(
    () => [
      {
        accessorKey: 'icon',
        header: '',
        cell: () => (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <span>
                  <Blocks className="h-5 w-5 text-muted-foreground" />
                </span>
              </TooltipTrigger>
              <TooltipContent>Subnet</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        ),
        enableSorting: false,
        size: 60,
      },
      {
        accessorKey: 'cn',
        header: ({ column }) => (
          <SortableHeader column={column}>Network Address</SortableHeader>
        ),
        cell: ({ row }) => (
          <div>
            <Link
              to={`/dhcp/${serviceCn}/subnets/${row.original.cn}?dn=${encodeURIComponent(row.original.dn)}`}
              className="font-medium hover:underline text-primary font-mono"
            >
              {row.original.cn}/{row.original.dhcpNetMask}
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
        accessorKey: 'dhcpRange',
        header: 'IP Range',
        cell: ({ row }) => {
          const ranges = row.original.dhcpRange
          if (!ranges || ranges.length === 0) {
            return <span className="text-muted-foreground">-</span>
          }
          return (
            <code className="text-sm">{ranges.join(', ')}</code>
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
              <Link to={`/dhcp/${serviceCn}/subnets/${row.original.cn}?dn=${encodeURIComponent(row.original.dn)}`}>
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
        size: 100,
      },
    ],
    [serviceCn, onDelete]
  )

  return (
    <DataTable
      columns={columns}
      data={subnets}
      isLoading={isLoading}
      emptyMessage={emptyMessage}
      searchPlaceholder="Search subnets..."
      searchColumn="cn"
    />
  )
}
