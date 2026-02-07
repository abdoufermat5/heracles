import { Link } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { PageHeader, ListPageSkeleton, ErrorDisplay, ConfirmDialog } from '@/components/common'
import { AssignmentsTable } from '@/components/acl'
import { useAclAssignments, useDeleteAssignment, useDeleteConfirmation } from '@/hooks'
import { ROUTES } from '@/config/constants'
import type { AclAssignment } from '@/types/acl'

export function AclAssignmentsListPage() {
  const { data, isLoading, error, refetch } = useAclAssignments()
  const deleteMutation = useDeleteAssignment()
  const deleteConfirmation = useDeleteConfirmation<AclAssignment>({
    onDelete: async (assignment) => { await deleteMutation.mutateAsync(assignment.id) },
    getItemName: (assignment) => assignment.policyName,
    entityType: 'Assignment',
    successMessage: () => 'Assignment deleted successfully',
    getDescription: (assignment) =>
      `Are you sure you want to remove the "${assignment.policyName}" policy assignment? The subject will lose the permissions granted by this assignment.`,
  })

  if (isLoading) {
    return <ListPageSkeleton />
  }

  if (error) {
    return <ErrorDisplay message={error.message} onRetry={() => refetch()} />
  }

  return (
    <div>
      <PageHeader
        title={
          <span className="flex items-center gap-2">
            ACL Assignments
            <Badge variant="secondary">{data?.total || 0}</Badge>
          </span>
        }
        description="Map policies to users, groups, or roles with scope and priority controls"
        actions={
          <Button asChild>
            <Link to={ROUTES.ACL_ASSIGNMENT_CREATE}>
              <Plus className="mr-2 h-4 w-4" />
              New Assignment
            </Link>
          </Button>
        }
      />

      <AssignmentsTable
        assignments={data?.assignments ?? []}
        onDelete={deleteConfirmation.requestDelete}
        emptyMessage="No assignments found"
      />

      <ConfirmDialog {...deleteConfirmation.dialogProps} />
    </div>
  )
}
