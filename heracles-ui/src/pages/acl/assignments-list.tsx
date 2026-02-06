import { useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { Plus, UserCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader, LoadingPage, ErrorDisplay, ConfirmDialog } from '@/components/common'
import { AssignmentsTable } from '@/components/acl'
import { useAclAssignments, useDeleteAssignment } from '@/hooks'
import { AppError } from '@/lib/errors'
import { ROUTES } from '@/config/constants'
import type { AclAssignment } from '@/types/acl'

export function AclAssignmentsListPage() {
  const [deleteAssignment, setDeleteAssignment] = useState<AclAssignment | null>(null)

  const { data, isLoading, error, refetch } = useAclAssignments()
  const deleteMutation = useDeleteAssignment()

  const handleDelete = async () => {
    if (!deleteAssignment) return
    try {
      await deleteMutation.mutateAsync(deleteAssignment.id)
      toast.success('Assignment deleted successfully')
      setDeleteAssignment(null)
    } catch (error) {
      AppError.toastError(error, 'Failed to delete assignment')
    }
  }

  if (isLoading) {
    return <LoadingPage message="Loading assignments..." />
  }

  if (error) {
    return <ErrorDisplay message={error.message} onRetry={() => refetch()} />
  }

  return (
    <div>
      <PageHeader
        title="ACL Assignments"
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

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <UserCheck className="h-5 w-5" />
            Assignments
            <Badge variant="secondary">{data?.total || 0}</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <AssignmentsTable
            assignments={data?.assignments ?? []}
            onDelete={setDeleteAssignment}
            emptyMessage="No assignments found"
          />
        </CardContent>
      </Card>

      <ConfirmDialog
        open={!!deleteAssignment}
        onOpenChange={(open) => !open && setDeleteAssignment(null)}
        title="Delete Assignment"
        description={`Are you sure you want to remove the "${deleteAssignment?.policyName}" policy assignment? The subject will lose the permissions granted by this assignment.`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
      />
    </div>
  )
}
