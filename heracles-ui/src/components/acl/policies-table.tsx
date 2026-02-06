/**
 * Policies Table Component
 *
 * Reusable table for displaying ACL policies using DataTable.
 */

import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Edit, Trash2, MoreHorizontal, Lock } from 'lucide-react'

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
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'

import { DataTable, SortableHeader, type ColumnDef } from '@/components/common/data-table'
import { aclPolicyDetailPath } from '@/config/routes'
import type { AclPolicy } from '@/types/acl'

interface PoliciesTableProps {
  policies: AclPolicy[]
  isLoading?: boolean
  onDelete?: (policy: AclPolicy) => void
  emptyMessage?: string
}

export function PoliciesTable({
  policies,
  isLoading = false,
  onDelete,
  emptyMessage = 'No policies found',
}: PoliciesTableProps) {
  const columns = useMemo<ColumnDef<AclPolicy>[]>(
    () => [
      {
        accessorKey: 'name',
        header: ({ column }) => (
          <SortableHeader column={column}>Name</SortableHeader>
        ),
        cell: ({ row }) => (
          <div className="flex items-center gap-2">
            <Link
              to={aclPolicyDetailPath(row.original.id)}
              className="font-medium text-primary hover:underline"
            >
              {row.original.name}
            </Link>
            {row.original.builtin && (
              <Tooltip>
                <TooltipTrigger>
                  <Badge variant="secondary" className="gap-1">
                    <Lock className="h-3 w-3" />
                    Built-in
                  </Badge>
                </TooltipTrigger>
                <TooltipContent>Built-in policies cannot be modified or deleted</TooltipContent>
              </Tooltip>
            )}
          </div>
        ),
      },
      {
        accessorKey: 'description',
        header: 'Description',
        cell: ({ row }) => (
          <span className="text-muted-foreground line-clamp-1">
            {row.original.description || '—'}
          </span>
        ),
      },
      {
        accessorKey: 'permissions',
        header: ({ column }) => (
          <SortableHeader column={column}>Permissions</SortableHeader>
        ),
        cell: ({ row }) => (
          <Badge variant="outline">
            {row.original.permissions.length} permission{row.original.permissions.length !== 1 ? 's' : ''}
          </Badge>
        ),
        sortingFn: (rowA, rowB) =>
          rowA.original.permissions.length - rowB.original.permissions.length,
      },
      {
        accessorKey: 'updatedAt',
        header: ({ column }) => (
          <SortableHeader column={column}>Updated</SortableHeader>
        ),
        cell: ({ row }) => (
          <span className="text-muted-foreground text-sm">
            {new Date(row.original.updatedAt).toLocaleDateString()}
          </span>
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
                <span className="sr-only">Open menu</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem asChild>
                <Link to={aclPolicyDetailPath(row.original.id)}>
                  <Edit className="mr-2 h-4 w-4" />
                  {row.original.builtin ? 'View' : 'Edit'}
                </Link>
              </DropdownMenuItem>
              {!row.original.builtin && onDelete && (
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
      },
    ],
    [onDelete]
  )

  return (
    <DataTable
      columns={columns}
      data={policies}
      isLoading={isLoading}
      emptyMessage={emptyMessage}
      enableSearch
      searchPlaceholder="Search policies..."
      searchColumn="name"
      getRowId={(row) => row.id}
    />
  )
}
