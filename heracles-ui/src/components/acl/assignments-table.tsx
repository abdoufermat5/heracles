/**
 * Assignments Table Component
 *
 * Reusable table for displaying ACL assignments using DataTable.
 */

import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Trash2, MoreHorizontal } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'

import { DataTable, SortableHeader, type ColumnDef } from '@/components/common/data-table'
import { aclPolicyDetailPath } from '@/config/routes'
import type { AclAssignment } from '@/types/acl'

interface AssignmentsTableProps {
  assignments: AclAssignment[]
  isLoading?: boolean
  onDelete?: (assignment: AclAssignment) => void
  emptyMessage?: string
}

/** Extract the short name from a DN for display */
function shortDn(dn: string): string {
  const first = dn.split(',')[0]
  return first || dn
}

const subjectTypeLabels: Record<string, string> = {
  user: 'User',
  group: 'Group',
  role: 'Role',
}

const subjectTypeVariants: Record<string, 'default' | 'secondary' | 'outline'> = {
  user: 'default',
  group: 'secondary',
  role: 'outline',
}

export function AssignmentsTable({
  assignments,
  isLoading = false,
  onDelete,
  emptyMessage = 'No assignments found',
}: AssignmentsTableProps) {
  const columns = useMemo<ColumnDef<AclAssignment>[]>(
    () => [
      {
        accessorKey: 'policyName',
        header: ({ column }) => (
          <SortableHeader column={column}>Policy</SortableHeader>
        ),
        cell: ({ row }) => (
          <div className="flex items-center gap-2">
            <Link
              to={aclPolicyDetailPath(row.original.policyId)}
              className="font-medium text-primary hover:underline"
            >
              {row.original.policyName}
            </Link>
            {row.original.builtin && (
              <Badge variant="secondary" className="text-xs">Built-in</Badge>
            )}
          </div>
        ),
      },
      {
        accessorKey: 'subjectDn',
        header: ({ column }) => (
          <SortableHeader column={column}>Subject</SortableHeader>
        ),
        cell: ({ row }) => (
          <div className="flex items-center gap-2">
            <Badge variant={subjectTypeVariants[row.original.subjectType] || 'outline'}>
              {subjectTypeLabels[row.original.subjectType] || row.original.subjectType}
            </Badge>
            <Tooltip>
              <TooltipTrigger>
                <span className="font-mono text-sm">{shortDn(row.original.subjectDn)}</span>
              </TooltipTrigger>
              <TooltipContent className="max-w-md break-all">
                {row.original.subjectDn}
              </TooltipContent>
            </Tooltip>
          </div>
        ),
      },
      {
        accessorKey: 'scopeDn',
        header: 'Scope',
        cell: ({ row }) => (
          <div className="flex items-center gap-1.5">
            <Badge variant="outline" className="text-xs">
              {row.original.scopeType}
            </Badge>
            <span className="text-sm text-muted-foreground">
              {row.original.scopeDn || 'Global'}
            </span>
          </div>
        ),
      },
      {
        id: 'flags',
        header: 'Flags',
        cell: ({ row }) => (
          <div className="flex items-center gap-1">
            {row.original.deny && (
              <Badge variant="destructive" className="text-xs">Deny</Badge>
            )}
            {row.original.selfOnly && (
              <Badge variant="secondary" className="text-xs">Self Only</Badge>
            )}
            {!row.original.deny && !row.original.selfOnly && (
              <span className="text-muted-foreground text-sm">—</span>
            )}
          </div>
        ),
      },
      {
        accessorKey: 'priority',
        header: ({ column }) => (
          <SortableHeader column={column}>Priority</SortableHeader>
        ),
        cell: ({ row }) => (
          <span className="font-mono text-sm">{row.original.priority}</span>
        ),
      },
      {
        id: 'actions',
        header: () => <span className="sr-only">Actions</span>,
        cell: ({ row }) => {
          const isBuiltin = row.original.builtin

          if (isBuiltin || !onDelete) return null

          return (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <MoreHorizontal className="h-4 w-4" />
                  <span className="sr-only">Open menu</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  className="text-destructive focus:text-destructive"
                  onClick={() => onDelete(row.original)}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )
        },
      },
    ],
    [onDelete]
  )

  return (
    <DataTable
      columns={columns}
      data={assignments}
      isLoading={isLoading}
      emptyMessage={emptyMessage}
      enableSearch
      searchPlaceholder="Search by policy or subject..."
      searchColumn="policyName"
      getRowId={(row) => row.id}
      enablePagination
      defaultPageSize={10}
      enableSelection
      enableColumnVisibility
      enableExport
      exportFilename="acl-assignments"
    />
  )
}
