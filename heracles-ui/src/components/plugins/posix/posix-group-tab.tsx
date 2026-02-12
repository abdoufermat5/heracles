import { Users, ExternalLink } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Link } from 'react-router-dom'

interface PosixGroupTabProps {
  cn: string
}

/**
 * POSIX Group Tab (Informational)
 * 
 * In standard LDAP, posixGroup is a standalone structural objectClass,
 * not something you add to groupOfNames. This tab provides information and
 * links to the proper POSIX group management page.
 */
export function PosixGroupTab(_: PosixGroupTabProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Users className="h-5 w-5" />
          <CardTitle>POSIX Group</CardTitle>
        </div>
        <CardDescription>
          POSIX groups are managed separately from organizational groups
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="text-sm text-muted-foreground">
          <p className="mb-2">
            In UNIX/Linux systems, <strong>posixGroup</strong> and <strong>groupOfNames</strong> serve different purposes:
          </p>
          <ul className="list-disc list-inside space-y-1 ml-2">
            <li><strong>groupOfNames</strong>: Organizational groups for grouping members</li>
            <li><strong>posixGroup</strong>: UNIX groups with GID and file system permissions</li>
          </ul>
          <p className="mt-4">
            To manage POSIX groups (create, edit, add members), please use the dedicated POSIX Groups page.
          </p>
        </div>
        <Button asChild variant="outline">
          <Link to="/posix/groups">
            <Users className="h-4 w-4 mr-2" />
            Manage POSIX Groups
            <ExternalLink className="h-4 w-4 ml-2" />
          </Link>
        </Button>
      </CardContent>
    </Card>
  )
}
