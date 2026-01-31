/**
 * Departments Table Component
 *
 * Reusable table for displaying departments using DataTable.
 */

import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Edit, Trash2, Building2, MoreHorizontal, FolderOpen } from 'lucide-react'

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
import { departmentDetailPath } from '@/config/routes'
import type { Department } from '@/types'

interface DepartmentsTableProps {
  departments: Department[]
  isLoading?: boolean
  onDelete?: (department: Department) => void
  onSelect?: (department: Department) => void
  emptyMessage?: string
}

export function DepartmentsTable({
  departments,
  isLoading = false,
  onDelete,
  onSelect,
  emptyMessage = 'No departments found',
}: DepartmentsTableProps) {
  const columns = useMemo<ColumnDef<Department>[]>(
    () => [
      {
        accessorKey: 'ou',
        header: ({ column }) => (
          <SortableHeader column={column}>Name</SortableHeader>
        ),
        cell: ({ row }) => (
          <Link
            to={departmentDetailPath(row.original.dn)}
            className="flex items-center gap-2 font-medium text-primary hover:underline"
          >
            <Building2 className="h-4 w-4" />
            {row.original.ou}
          </Link>
        ),
      },
      {
        accessorKey: 'description',
        header: ({ column }) => (
          <SortableHeader column={column}>Description</SortableHeader>
        ),
        cell: ({ row }) => (
          <span className="text-muted-foreground">
            {row.original.description || '—'}
          </span>
        ),
      },
      {
        accessorKey: 'path',
        header: ({ column }) => (
          <SortableHeader column={column}>Path</SortableHeader>
        ),
        cell: ({ row }) => (
          <span className="font-mono text-sm text-muted-foreground">
            {row.original.path}
          </span>
        ),
      },
      {
        accessorKey: 'childrenCount',
        header: ({ column }) => (
          <SortableHeader column={column}>Children</SortableHeader>
        ),
        cell: ({ row }) =>
          row.original.childrenCount > 0 ? (
            <Badge variant="secondary">{row.original.childrenCount}</Badge>
          ) : (
            <span className="text-muted-foreground">0</span>
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
                <span className="sr-only">Actions for {row.original.ou}</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {onSelect && (
                <DropdownMenuItem onClick={() => onSelect(row.original)}>
                  <FolderOpen className="mr-2 h-4 w-4" />
                  Select
                </DropdownMenuItem>
              )}
              <DropdownMenuItem asChild>
                <Link to={departmentDetailPath(row.original.dn)}>
                  <Edit className="mr-2 h-4 w-4" />
                  Edit
                </Link>
              </DropdownMenuItem>
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
    [onDelete, onSelect]
  )

  return (
    <DataTable
      columns={columns}
      data={departments}
      isLoading={isLoading}
      getRowId={(row) => row.dn}
      emptyMessage={emptyMessage}
      emptyDescription="Create a new department to organize your users and groups"
      emptyIcon={<Building2 className="h-8 w-8 text-muted-foreground" />}
      enableSearch
      searchPlaceholder="Search departments..."
      searchColumn="ou"
      enablePagination
      defaultPageSize={10}
    />
  )
}
