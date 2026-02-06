import { Shield, ShieldAlert, ShieldCheck, ExternalLink } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { PermissionBadges } from '@/components/acl'
import { useAclAssignments, useAclPolicy } from '@/hooks'
import { aclPolicyDetailPath } from '@/config/constants'
import type { AclAssignment } from '@/types'

interface EntityPermissionsTabProps {
  /** Full DN of the entity (user, group, etc.) */
  subjectDn: string
  /** Display label for the entity */
  entityLabel: string
}

/** Renders a single assignment row with its resolved policy */
function AssignmentRow({ assignment }: { assignment: AclAssignment }) {
  const { data: policy, isLoading } = useAclPolicy(assignment.policyId)

  if (isLoading) {
    return (
      <div className="flex items-center gap-3 rounded-lg border p-3">
        <Skeleton className="h-5 w-5 rounded" />
        <div className="flex-1 space-y-1.5">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-3 w-60" />
        </div>
      </div>
    )
  }

  const isDeny = assignment.deny
  const isSelfOnly = assignment.selfOnly

  return (
    <div className="flex flex-col gap-2 rounded-lg border p-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {isDeny ? (
            <ShieldAlert className="h-4 w-4 text-destructive" />
          ) : (
            <ShieldCheck className="h-4 w-4 text-green-600" />
          )}
          <Link
            to={aclPolicyDetailPath(assignment.policyId)}
            className="font-medium text-sm hover:underline"
          >
            {policy?.name ?? `Policy #${assignment.policyId}`}
            <ExternalLink className="ml-1 inline h-3 w-3" />
          </Link>
          {isDeny && <Badge variant="destructive" className="text-xs">Deny</Badge>}
          {isSelfOnly && <Badge variant="outline" className="text-xs">Self Only</Badge>}
          {policy?.builtin && <Badge variant="secondary" className="text-xs">Built-in</Badge>}
        </div>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger>
              <Badge variant="outline" className="text-xs">
                Priority {assignment.priority}
              </Badge>
            </TooltipTrigger>
            <TooltipContent>
              Higher priority assignments override lower ones
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
      {policy && (
        <PermissionBadges permissions={policy.permissions} compact />
      )}
      {assignment.scopeDn && (
        <p className="text-xs text-muted-foreground font-mono">
          Scope: {assignment.scopeDn} ({assignment.scopeType})
        </p>
      )}
    </div>
  )
}

/**
 * Tab component that shows all ACL assignments for a given entity DN.
 * Displays direct assignments (subject matches DN exactly).
 * Designed to be embedded in user/group/role detail pages.
 */
export function EntityPermissionsTab({ subjectDn, entityLabel }: EntityPermissionsTabProps) {
  const { data, isLoading } = useAclAssignments({ subject_dn: subjectDn, page_size: 100 })

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="h-5 w-5" />
          ACL Assignments
          {data && (
            <Badge variant="secondary">{data.total}</Badge>
          )}
        </CardTitle>
        <CardDescription>
          Policy assignments that apply to {entityLabel}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3 rounded-lg border p-3">
                <Skeleton className="h-5 w-5 rounded" />
                <div className="flex-1 space-y-1.5">
                  <Skeleton className="h-4 w-40" />
                  <Skeleton className="h-3 w-60" />
                </div>
              </div>
            ))}
          </div>
        ) : data && data.assignments.length > 0 ? (
          <div className="space-y-3">
            {data.assignments.map((assignment) => (
              <AssignmentRow key={assignment.id} assignment={assignment} />
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground py-4 text-center">
            No ACL assignments found for this entity.
          </p>
        )}
      </CardContent>
    </Card>
  )
}
