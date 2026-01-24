/**
 * Sudo Roles Table
 *
 * Table component for displaying sudo roles with actions.
 */

import { Link } from 'react-router-dom'
import { Edit, Trash2, Terminal, Users, Server } from 'lucide-react'

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

import { ArrayBadges } from '@/components/common'
import { sudoRolePath } from '@/config/routes'
import type { SudoRoleData } from '@/types/sudo'

interface SudoRolesTableProps {
  roles: SudoRoleData[]
  onDelete: (role: SudoRoleData) => void
}

export function SudoRolesTable({ roles, onDelete }: SudoRolesTableProps) {
  if (roles.length === 0) {
    return null
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Role Name</TableHead>
          <TableHead>
            <div className="flex items-center gap-1">
              <Users className="h-4 w-4" />
              Users
            </div>
          </TableHead>
          <TableHead>
            <div className="flex items-center gap-1">
              <Server className="h-4 w-4" />
              Hosts
            </div>
          </TableHead>
          <TableHead>
            <div className="flex items-center gap-1">
              <Terminal className="h-4 w-4" />
              Commands
            </div>
          </TableHead>
          <TableHead>Options</TableHead>
          <TableHead>Order</TableHead>
          <TableHead className="w-[100px]">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {roles.map((role) => (
          <TableRow key={role.cn}>
            <TableCell className="font-medium">
              <Link
                to={sudoRolePath(role.cn)}
                className="hover:underline text-primary"
              >
                {role.cn}
              </Link>
              {role.description && (
                <p className="text-xs text-muted-foreground mt-1">
                  {role.description}
                </p>
              )}
            </TableCell>
            <TableCell>
              <ArrayBadges items={role.sudoUser} />
            </TableCell>
            <TableCell>
              <ArrayBadges items={role.sudoHost} variant="outline" />
            </TableCell>
            <TableCell>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div>
                      <ArrayBadges
                        items={role.sudoCommand}
                        variant={
                          role.sudoCommand.includes('ALL')
                            ? 'destructive'
                            : 'default'
                        }
                      />
                    </div>
                  </TooltipTrigger>
                  {role.sudoCommand.length > 3 && (
                    <TooltipContent>
                      <div className="max-w-xs">
                        {role.sudoCommand.join(', ')}
                      </div>
                    </TooltipContent>
                  )}
                </Tooltip>
              </TooltipProvider>
            </TableCell>
            <TableCell>
              <ArrayBadges items={role.sudoOption} max={2} />
            </TableCell>
            <TableCell>
              <Badge variant="outline">{role.sudoOrder}</Badge>
            </TableCell>
            <TableCell>
              <div className="flex items-center gap-1">
                <Button variant="ghost" size="icon" asChild>
                  <Link to={sudoRolePath(role.cn)}>
                    <Edit className="h-4 w-4" />
                  </Link>
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => onDelete(role)}
                >
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
