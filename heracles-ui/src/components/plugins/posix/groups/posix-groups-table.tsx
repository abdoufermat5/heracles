/**
 * POSIX Groups Table Component
 *
 * Reusable table for displaying POSIX groups.
 */

import { Link } from 'react-router-dom'
import { Edit, Trash2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

import { posixGroupPath } from '@/config/routes'
import type { PosixGroupListItem } from '@/types/posix'

interface PosixGroupsTableProps {
  groups: PosixGroupListItem[]
  onDelete?: (group: PosixGroupListItem) => void
  emptyMessage?: string
}

export function PosixGroupsTable({
  groups,
  onDelete,
  emptyMessage = 'No POSIX groups found',
}: PosixGroupsTableProps) {
  if (groups.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        {emptyMessage}
      </div>
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Group Name (cn)</TableHead>
          <TableHead>GID</TableHead>
          <TableHead>Description</TableHead>
          <TableHead>Members</TableHead>
          <TableHead className="w-[100px]">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {groups.map((group) => (
          <TableRow key={group.cn}>
            <TableCell className="font-medium">
              <Link
                to={posixGroupPath(group.cn)}
                className="hover:underline text-primary"
              >
                {group.cn}
              </Link>
            </TableCell>
            <TableCell>
              <Badge variant="outline">{group.gidNumber}</Badge>
            </TableCell>
            <TableCell className="text-muted-foreground">
              {group.description || '-'}
            </TableCell>
            <TableCell>
              <Badge variant="secondary">
                {group.memberCount} member{group.memberCount !== 1 ? 's' : ''}
              </Badge>
            </TableCell>
            <TableCell>
              <div className="flex items-center gap-1">
                <Button variant="ghost" size="icon" asChild>
                  <Link to={posixGroupPath(group.cn)}>
                    <Edit className="h-4 w-4" />
                  </Link>
                </Button>
                {onDelete && (
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => onDelete(group)}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                )}
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
