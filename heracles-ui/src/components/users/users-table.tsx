/**
 * Users Table Component
 *
 * Reusable table for displaying users using DataTable.
 */

import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Edit, Trash2, Key, Users, MoreHorizontal } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

import {
  DataTable,
  SortableHeader,
  type ColumnDef,
} from '@/components/common/data-table'
import { ROUTES } from '@/config/constants'
import type { User } from '@/types'

interface UsersTableProps {
  users: User[]
  isLoading?: boolean
  onDelete?: (user: User) => void
  onSetPassword?: (user: User) => void
  emptyMessage?: string
}

export function UsersTable({
  users,
  isLoading = false,
  onDelete,
  onSetPassword,
  emptyMessage = 'No users found',
}: UsersTableProps) {
  const columns = useMemo<ColumnDef<User>[]>(
    () => [
      {
        accessorKey: 'uid',
        header: ({ column }) => (
          <SortableHeader column={column}>Username</SortableHeader>
        ),
        cell: ({ row }) => (
          <Link
            to={ROUTES.USER_DETAIL.replace(':uid', row.original.uid)}
            className="font-medium text-primary hover:underline"
          >
            {row.original.uid}
          </Link>
        ),
      },
      {
        accessorKey: 'displayName',
        header: ({ column }) => (
          <SortableHeader column={column}>Display Name</SortableHeader>
        ),
        cell: ({ row }) =>
          row.original.displayName ||
          `${row.original.givenName || ''} ${row.original.sn || ''}`.trim() ||
          '—',
      },
      {
        accessorKey: 'mail',
        header: ({ column }) => (
          <SortableHeader column={column}>Email</SortableHeader>
        ),
        cell: ({ row }) => (
          <span className="text-muted-foreground">
            {row.original.mail || '—'}
          </span>
        ),
      },
      {
        accessorKey: 'uidNumber',
        header: ({ column }) => (
          <SortableHeader column={column}>UID</SortableHeader>
        ),
        cell: ({ row }) =>
          row.original.uidNumber ? (
            <Badge variant="outline" className="font-mono">
              {row.original.uidNumber}
            </Badge>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
      },
      {
        id: 'actions',
        header: () => <span className="sr-only">Actions</span>,
        cell: ({ row }) => (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreHorizontal className="h-4 w-4" />
                <span className="sr-only">Actions for {row.original.uid}</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem asChild>
                <Link to={ROUTES.USER_DETAIL.replace(':uid', row.original.uid)}>
                  <Edit className="mr-2 h-4 w-4" />
                  Edit
                </Link>
              </DropdownMenuItem>
              {onSetPassword && (
                <DropdownMenuItem onClick={() => onSetPassword(row.original)}>
                  <Key className="mr-2 h-4 w-4" />
                  Set Password
                </DropdownMenuItem>
              )}
              {onDelete && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    className="text-destructive focus:text-destructive"
                    onClick={() => onDelete(row.original)}
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        ),
        enableSorting: false,
        size: 80,
      },
    ],
    [onDelete, onSetPassword]
  )

  return (
    <DataTable
      columns={columns}
      data={users}
      isLoading={isLoading}
      getRowId={(row) => row.dn || row.uid}
      emptyMessage={emptyMessage}
      emptyDescription="Create a new user to get started"
      emptyIcon={<Users className="h-8 w-8 text-muted-foreground" />}
      enableSearch
      searchPlaceholder="Search users..."
      searchColumn="uid"
      enablePagination
      defaultPageSize={10}
    />
  )
}
