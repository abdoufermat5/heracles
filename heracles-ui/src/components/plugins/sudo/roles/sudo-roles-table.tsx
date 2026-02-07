/**
 * Sudo Roles Table
 *
 * Table component for displaying sudo roles with actions using DataTable.
 */

import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Edit, Trash2, Terminal, Users, Server, ShieldCheck } from 'lucide-react'

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
import { ArrayBadges } from '@/components/common'
import { sudoRolePath } from '@/config/routes'
import type { SudoRoleData } from '@/types/sudo'

interface SudoRolesTableProps {
  roles: SudoRoleData[]
  isLoading?: boolean
  onDelete: (role: SudoRoleData) => void
  emptyMessage?: string
}

export function SudoRolesTable({
  roles,
  isLoading = false,
  onDelete,
  emptyMessage = 'No sudo roles found',
}: SudoRolesTableProps) {
  const columns = useMemo<ColumnDef<SudoRoleData>[]>(
    () => [
      {
        accessorKey: 'cn',
        header: ({ column }) => (
          <SortableHeader column={column}>Role Name</SortableHeader>
        ),
        cell: ({ row }) => (
          <div>
            <Link
              to={sudoRolePath(row.original.cn)}
              className="font-medium hover:underline text-primary"
            >
              {row.original.cn}
            </Link>
            {row.original.description && (
              <p className="text-xs text-muted-foreground mt-1">
                {row.original.description}
              </p>
            )}
          </div>
        ),
      },
      {
        accessorKey: 'sudoUser',
        header: () => (
          <div className="flex items-center gap-1">
            <Users className="h-4 w-4" />
            Users
          </div>
        ),
        cell: ({ row }) => <ArrayBadges items={row.original.sudoUser} />,
        enableSorting: false,
      },
      {
        accessorKey: 'sudoHost',
        header: () => (
          <div className="flex items-center gap-1">
            <Server className="h-4 w-4" />
            Hosts
          </div>
        ),
        cell: ({ row }) => (
          <ArrayBadges items={row.original.sudoHost} variant="outline" />
        ),
        enableSorting: false,
      },
      {
        accessorKey: 'sudoCommand',
        header: () => (
          <div className="flex items-center gap-1">
            <Terminal className="h-4 w-4" />
            Commands
          </div>
        ),
        cell: ({ row }) => (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div>
                  <ArrayBadges
                    items={row.original.sudoCommand}
                    variant={
                      row.original.sudoCommand.includes('ALL')
                        ? 'destructive'
                        : 'default'
                    }
                  />
                </div>
              </TooltipTrigger>
              {row.original.sudoCommand.length > 3 && (
                <TooltipContent>
                  <div className="max-w-xs">
                    {row.original.sudoCommand.join(', ')}
                  </div>
                </TooltipContent>
              )}
            </Tooltip>
          </TooltipProvider>
        ),
        enableSorting: false,
      },
      {
        accessorKey: 'sudoOption',
        header: 'Options',
        cell: ({ row }) => (
          <ArrayBadges items={row.original.sudoOption} max={2} />
        ),
        enableSorting: false,
      },
      {
        accessorKey: 'sudoOrder',
        header: ({ column }) => (
          <SortableHeader column={column}>Order</SortableHeader>
        ),
        cell: ({ row }) => (
          <Badge variant="outline">{row.original.sudoOrder}</Badge>
        ),
      },
      {
        id: 'actions',
        header: () => <span className="sr-only">Actions</span>,
        cell: ({ row }) => (
          <div className="flex items-center justify-end gap-1">
            <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
              <Link to={sudoRolePath(row.original.cn)}>
                <Edit className="h-4 w-4" />
                <span className="sr-only">Edit {row.original.cn}</span>
              </Link>
            </Button>
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
      data={roles}
      isLoading={isLoading}
      getRowId={(row) => row.cn}
      emptyMessage={emptyMessage}
      emptyDescription="Create a new sudo role to get started"
      emptyIcon={<ShieldCheck className="h-8 w-8 text-muted-foreground" />}
      enableSearch
      searchPlaceholder="Search roles..."
      searchColumn="cn"
      enablePagination
      defaultPageSize={10}
      enableSelection
      enableColumnVisibility
      enableExport
      exportFilename="sudo-roles"
    />
  )
}
