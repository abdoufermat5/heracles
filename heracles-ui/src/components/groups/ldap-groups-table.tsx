/**
 * LDAP Groups Table Component
 *
 * Reusable table for displaying LDAP groups (groupOfNames) using DataTable.
 */

import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Edit, Trash2, Users, UsersRound } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  DataTable,
  SortableHeader,
  type ColumnDef,
} from '@/components/common/data-table'

import { ROUTES } from '@/config/constants'
import type { Group } from '@/types'

interface LdapGroupsTableProps {
  groups: Group[]
  isLoading?: boolean
  onDelete?: (group: Group) => void
  emptyMessage?: string
}

export function LdapGroupsTable({
  groups,
  isLoading = false,
  onDelete,
  emptyMessage = 'No LDAP groups found',
}: LdapGroupsTableProps) {
  const columns = useMemo<ColumnDef<Group>[]>(
    () => [
      {
        accessorKey: 'cn',
        header: ({ column }) => (
          <SortableHeader column={column}>Group Name</SortableHeader>
        ),
        cell: ({ row }) => (
          <Link
            to={ROUTES.GROUP_DETAIL.replace(':cn', row.original.cn)}
            className="font-medium text-primary hover:underline"
          >
            {row.original.cn}
          </Link>
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
        accessorKey: 'gidNumber',
        header: ({ column }) => (
          <SortableHeader column={column}>GID</SortableHeader>
        ),
        cell: ({ row }) =>
          row.original.gidNumber ? (
            <Badge variant="outline" className="font-mono">
              {row.original.gidNumber}
            </Badge>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
      },
      {
        id: 'memberCount',
        header: ({ column }) => (
          <SortableHeader column={column}>Members</SortableHeader>
        ),
        accessorFn: (row) => row.members?.length || row.memberUid?.length || row.member?.length || 0,
        cell: ({ row }) => (
          <Badge variant="secondary">
            <Users className="h-3 w-3 mr-1" />
            {row.original.members?.length || row.original.memberUid?.length || row.original.member?.length || 0}
          </Badge>
        ),
      },
      {
        id: 'actions',
        header: () => <span className="sr-only">Actions</span>,
        cell: ({ row }) => (
          <div className="flex items-center justify-end gap-1">
            <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
              <Link to={ROUTES.GROUP_DETAIL.replace(':cn', row.original.cn)}>
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
      getRowId={(row) => row.dn || row.cn}
      emptyMessage={emptyMessage}
      emptyDescription="Create a new group to get started"
      emptyIcon={<UsersRound className="h-8 w-8 text-muted-foreground" />}
      enableSearch
      searchPlaceholder="Search groups..."
      searchColumn="cn"
      enablePagination
      defaultPageSize={10}
    />
  )
}
