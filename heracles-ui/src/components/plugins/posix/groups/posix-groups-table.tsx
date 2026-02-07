/**
 * POSIX Groups Table Component
 *
 * Reusable table for displaying POSIX groups using DataTable.
 */

import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Edit, Trash2, Users } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  DataTable,
  SortableHeader,
  type ColumnDef,
} from '@/components/common/data-table'

import { posixGroupPath } from '@/config/routes'
import type { PosixGroupListItem } from '@/types/posix'

interface PosixGroupsTableProps {
  groups: PosixGroupListItem[]
  isLoading?: boolean
  onDelete?: (group: PosixGroupListItem) => void
  emptyMessage?: string
}

export function PosixGroupsTable({
  groups,
  isLoading = false,
  onDelete,
  emptyMessage = 'No POSIX groups found',
}: PosixGroupsTableProps) {
  const columns = useMemo<ColumnDef<PosixGroupListItem>[]>(
    () => [
      {
        accessorKey: 'cn',
        header: ({ column }) => (
          <SortableHeader column={column}>Group Name</SortableHeader>
        ),
        cell: ({ row }) => (
          <Link
            to={posixGroupPath(row.original.cn)}
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
          <span className="text-muted-foreground max-w-[300px] truncate block">
            {row.original.description || '—'}
          </span>
        ),
      },
      {
        accessorKey: 'memberCount',
        header: ({ column }) => (
          <SortableHeader column={column}>Members</SortableHeader>
        ),
        cell: ({ row }) => (
          <Badge variant="secondary">
            <Users className="h-3 w-3 mr-1" />
            {row.original.memberCount}
          </Badge>
        ),
      },
      {
        id: 'actions',
        header: () => <span className="sr-only">Actions</span>,
        cell: ({ row }) => (
          <div className="flex items-center justify-end gap-1">
            <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
              <Link to={posixGroupPath(row.original.cn)}>
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
      emptyDescription="Create a new POSIX group to get started"
      emptyIcon={<Users className="h-8 w-8 text-muted-foreground" />}
      enableSearch
      searchPlaceholder="Search groups..."
      searchColumn="cn"
      enablePagination
      defaultPageSize={10}
      enableSelection
      enableColumnVisibility
      enableExport
      exportFilename="posix-groups"
    />
  )
}
