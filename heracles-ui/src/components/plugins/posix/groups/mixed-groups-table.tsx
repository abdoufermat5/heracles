/**
 * Mixed Groups Table Component
 *
 * Reusable table for displaying Mixed groups (groupOfNames + posixGroup).
 */

import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Edit, Trash2, Users, Terminal, Layers } from 'lucide-react'

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

import { mixedGroupPath } from '@/config/routes'
import type { MixedGroupListItem } from '@/types/posix'

interface MixedGroupsTableProps {
  groups: MixedGroupListItem[]
  isLoading?: boolean
  onDelete?: (group: MixedGroupListItem) => void
  emptyMessage?: string
}

export function MixedGroupsTable({
  groups,
  isLoading = false,
  onDelete,
  emptyMessage = 'No mixed groups found',
}: MixedGroupsTableProps) {
  const columns = useMemo<ColumnDef<MixedGroupListItem>[]>(
    () => [
      {
        accessorKey: 'cn',
        header: ({ column }) => (
          <SortableHeader column={column}>Group Name</SortableHeader>
        ),
        cell: ({ row }) => (
          <Link
            to={mixedGroupPath(row.original.cn)}
            className="font-medium text-primary hover:underline"
          >
            {row.original.cn}
          </Link>
        ),
      },
      {
        accessorKey: 'gidNumber',
        header: ({ column }) => (
          <SortableHeader column={column}>GID</SortableHeader>
        ),
        cell: ({ row }) => (
          <Badge variant="outline" className="font-mono">
            {row.original.gidNumber}
          </Badge>
        ),
      },
      {
        accessorKey: 'description',
        header: 'Description',
        cell: ({ row }) => (
          <span className="text-muted-foreground max-w-[250px] truncate block">
            {row.original.description || '—'}
          </span>
        ),
      },
      {
        accessorKey: 'memberCount',
        header: () => (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger className="flex items-center gap-1.5">
                <Users className="h-3.5 w-3.5" />
                LDAP
              </TooltipTrigger>
              <TooltipContent>
                <p>LDAP members (groupOfNames)</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        ),
        cell: ({ row }) => (
          <Badge variant="secondary">
            <Users className="h-3 w-3 mr-1" />
            {row.original.memberCount}
          </Badge>
        ),
      },
      {
        accessorKey: 'memberUidCount',
        header: () => (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger className="flex items-center gap-1.5">
                <Terminal className="h-3.5 w-3.5" />
                POSIX
              </TooltipTrigger>
              <TooltipContent>
                <p>POSIX members (memberUid)</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        ),
        cell: ({ row }) => (
          <Badge variant="outline">
            <Terminal className="h-3 w-3 mr-1" />
            {row.original.memberUidCount}
          </Badge>
        ),
      },
      {
        id: 'actions',
        header: () => <span className="sr-only">Actions</span>,
        cell: ({ row }) => (
          <div className="flex items-center justify-end gap-1">
            <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
              <Link to={mixedGroupPath(row.original.cn)}>
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
      data={groups}
      isLoading={isLoading}
      getRowId={(row) => row.cn}
      emptyMessage={emptyMessage}
      emptyDescription="Create a mixed group to combine LDAP and POSIX membership"
      emptyIcon={<Layers className="h-8 w-8 text-muted-foreground" />}
      enableSearch
      searchPlaceholder="Search groups..."
      searchColumn="cn"
      enablePagination
      defaultPageSize={10}
      enableSelection
      enableColumnVisibility
      enableExport
      exportFilename="mixed-groups"
    />
  )
}
