/**
 * DHCP Hosts Table Component
 *
 * Displays DHCP hosts in a sortable, filterable table.
 */

import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  Monitor,
  Edit,
  Trash2,
  Network,
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
import type { DhcpHostListItem } from '@/types/dhcp'

interface DhcpHostsTableProps {
  serviceCn: string
  hosts: DhcpHostListItem[]
  isLoading?: boolean
  onDelete?: (host: DhcpHostListItem) => void
  emptyMessage?: string
}

/**
 * Extract MAC address from dhcpHWAddress format (e.g., "ethernet 00:11:22:33:44:55")
 */
function formatMacAddress(hwAddress?: string): string | null {
  if (!hwAddress) return null
  const parts = hwAddress.split(' ')
  return parts.length > 1 ? parts[1] : hwAddress
}

/**
 * Extract IP from fixed-address statement
 */
function extractFixedAddress(statements?: string[]): string | null {
  if (!statements) return null
  for (const stmt of statements) {
    const match = stmt.match(/fixed-address\s+([0-9.]+)/)
    if (match) return match[1]
  }
  return null
}

export function DhcpHostsTable({
  serviceCn,
  hosts,
  isLoading = false,
  onDelete,
  emptyMessage = 'No hosts found',
}: DhcpHostsTableProps) {
  const columns = useMemo<ColumnDef<DhcpHostListItem>[]>(
    () => [
      {
        accessorKey: 'icon',
        header: '',
        cell: () => (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <span>
                  <Monitor className="h-5 w-5 text-muted-foreground" />
                </span>
              </TooltipTrigger>
              <TooltipContent>DHCP Host</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        ),
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
              to={`/dhcp/${serviceCn}/hosts/${row.original.cn}?dn=${encodeURIComponent(row.original.dn)}`}
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
        accessorKey: 'dhcpHWAddress',
        header: 'MAC Address',
        cell: ({ row }) => {
          const mac = formatMacAddress(row.original.dhcpHWAddress ?? undefined)
          if (!mac) {
            return <span className="text-muted-foreground">-</span>
          }
          return (
            <code className="text-sm font-mono">{mac}</code>
          )
        },
        enableSorting: false,
      },
      {
        accessorKey: 'fixedAddress',
        header: () => (
          <div className="flex items-center gap-1">
            <Network className="h-4 w-4" />
            Fixed IP
          </div>
        ),
        cell: ({ row }) => {
          const ip = row.original.fixedAddress
          if (!ip) {
            return <span className="text-muted-foreground">Dynamic</span>
          }
          return (
            <code className="text-sm font-mono">{ip}</code>
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
              <Link to={`/dhcp/${serviceCn}/hosts/${row.original.cn}?dn=${encodeURIComponent(row.original.dn)}`}>
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
      data={hosts}
      isLoading={isLoading}
      emptyMessage={emptyMessage}
      searchPlaceholder="Search hosts..."
      searchColumn="cn"
    />
  )
}
