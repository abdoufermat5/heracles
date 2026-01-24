/**
 * Mixed Groups Table Component
 *
 * Reusable table for displaying Mixed groups (groupOfNames + posixGroup).
 */

import { Link } from 'react-router-dom'
import { Edit, Trash2, Users, Terminal } from 'lucide-react'

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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

import { mixedGroupPath } from '@/config/routes'
import type { MixedGroupListItem } from '@/types/posix'

interface MixedGroupsTableProps {
  groups: MixedGroupListItem[]
  onDelete?: (group: MixedGroupListItem) => void
  emptyMessage?: string
}

export function MixedGroupsTable({
  groups,
  onDelete,
  emptyMessage = 'No mixed groups found',
}: MixedGroupsTableProps) {
  if (groups.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        {emptyMessage}
      </div>
    )
  }

  return (
    <TooltipProvider>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Group Name (cn)</TableHead>
            <TableHead>GID</TableHead>
            <TableHead>Description</TableHead>
            <TableHead>
              <Tooltip>
                <TooltipTrigger className="flex items-center gap-1">
                  <Users className="h-3 w-3" />
                  LDAP
                </TooltipTrigger>
                <TooltipContent>
                  <p>LDAP members (groupOfNames - member DNs)</p>
                </TooltipContent>
              </Tooltip>
            </TableHead>
            <TableHead>
              <Tooltip>
                <TooltipTrigger className="flex items-center gap-1">
                  <Terminal className="h-3 w-3" />
                  POSIX
                </TooltipTrigger>
                <TooltipContent>
                  <p>POSIX members (memberUid for UNIX)</p>
                </TooltipContent>
              </Tooltip>
            </TableHead>
            <TableHead className="w-[100px]">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {groups.map((group) => (
            <TableRow key={group.cn}>
              <TableCell className="font-medium">
                <Link
                  to={mixedGroupPath(group.cn)}
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
                  {group.memberCount}
                </Badge>
              </TableCell>
              <TableCell>
                <Badge variant="secondary">
                  {group.memberUidCount}
                </Badge>
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="icon" asChild>
                    <Link to={mixedGroupPath(group.cn)}>
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
    </TooltipProvider>
  )
}
