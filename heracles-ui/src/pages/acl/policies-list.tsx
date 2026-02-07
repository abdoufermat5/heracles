import { Link } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { PageHeader, ListPageSkeleton, ErrorDisplay, ConfirmDialog } from '@/components/common'
import { PoliciesTable } from '@/components/acl'
import { useAclPolicies, useDeletePolicy, useDeleteConfirmation } from '@/hooks'
import { ROUTES } from '@/config/constants'
import type { AclPolicy } from '@/types/acl'

export function AclPoliciesListPage() {
  const { data, isLoading, error, refetch } = useAclPolicies()
  const deleteMutation = useDeletePolicy()
  const deleteConfirmation = useDeleteConfirmation<AclPolicy>({
    onDelete: async (policy) => { await deleteMutation.mutateAsync(policy.id) },
    getItemName: (policy) => policy.name,
    entityType: 'Policy',
    successMessage: (policy) => `Policy "${policy.name}" deleted successfully`,
    getDescription: (policy) =>
      `Are you sure you want to delete policy "${policy.name}"? All assignments using this policy will also be deleted. This action cannot be undone.`,
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
            ACL Policies
            <Badge variant="secondary">{data?.total || 0}</Badge>
          </span>
        }
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

      <PoliciesTable
        policies={data?.policies ?? []}
        onDelete={deleteConfirmation.requestDelete}
        emptyMessage="No policies found"
      />

      <ConfirmDialog {...deleteConfirmation.dialogProps} />
    </div>
  )
}
