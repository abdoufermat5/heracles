/**
 * Roles Table Component
 *
 * Reusable table for displaying organizational roles using DataTable.
 */

import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Edit, Trash2, Users, Shield } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
    DataTable,
    SortableHeader,
    type ColumnDef,
} from '@/components/common/data-table'

import type { Role } from '@/types'

interface RolesTableProps {
    roles: Role[]
    isLoading?: boolean
    onDelete?: (role: Role) => void
    emptyMessage?: string
}

export function RolesTable({
    roles,
    isLoading = false,
    onDelete,
    emptyMessage = 'No roles found',
}: RolesTableProps) {
    const columns = useMemo<ColumnDef<Role>[]>(
        () => [
            {
                accessorKey: 'cn',
                header: ({ column }) => (
                    <SortableHeader column={column}>Role Name</SortableHeader>
                ),
                cell: ({ row }) => (
                    <Link
                        to={`/roles/${row.original.cn}`}
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
                            <Link to={`/roles/${row.original.cn}`}>
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
            data={roles}
            isLoading={isLoading}
            getRowId={(row) => row.dn || row.cn}
            emptyMessage={emptyMessage}
            emptyDescription="Create a new role to get started"
            emptyIcon={<Shield className="h-8 w-8 text-muted-foreground" />}
            enableSearch
            searchPlaceholder="Search roles..."
            searchColumn="cn"
            enablePagination
            defaultPageSize={10}
            enableSelection
            enableColumnVisibility
            enableExport
            exportFilename="roles"
        />
    )
}
