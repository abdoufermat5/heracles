import { useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { Plus, Shield } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader, LoadingPage, ErrorDisplay, ConfirmDialog } from '@/components/common'
import { PoliciesTable } from '@/components/acl'
import { useAclPolicies, useDeletePolicy } from '@/hooks'
import { AppError } from '@/lib/errors'
import { ROUTES } from '@/config/constants'
import type { AclPolicy } from '@/types/acl'

export function AclPoliciesListPage() {
  const [deletePolicy, setDeletePolicy] = useState<AclPolicy | null>(null)

  const { data, isLoading, error, refetch } = useAclPolicies()
  const deleteMutation = useDeletePolicy()

  const handleDelete = async () => {
    if (!deletePolicy) return
    try {
      await deleteMutation.mutateAsync(deletePolicy.id)
      toast.success(`Policy "${deletePolicy.name}" deleted successfully`)
      setDeletePolicy(null)
    } catch (error) {
      AppError.toastError(error, 'Failed to delete policy')
    }
  }

  if (isLoading) {
    return <LoadingPage message="Loading policies..." />
  }

  if (error) {
    return <ErrorDisplay message={error.message} onRetry={() => refetch()} />
  }

  return (
    <div>
      <PageHeader
        title="ACL Policies"
        description="Manage access control policies that define permission sets"
        actions={
          <Button asChild>
            <Link to={ROUTES.ACL_POLICY_CREATE}>
              <Plus className="mr-2 h-4 w-4" />
              New Policy
            </Link>
          </Button>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Policies
            <Badge variant="secondary">{data?.total || 0}</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <PoliciesTable
            policies={data?.policies ?? []}
            onDelete={setDeletePolicy}
            emptyMessage="No policies found"
          />
        </CardContent>
      </Card>

      <ConfirmDialog
        open={!!deletePolicy}
        onOpenChange={(open) => !open && setDeletePolicy(null)}
        title="Delete Policy"
        description={`Are you sure you want to delete policy "${deletePolicy?.name}"? All assignments using this policy will also be deleted. This action cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
      />
    </div>
  )
}
