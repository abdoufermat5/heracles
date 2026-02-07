import { Link } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { PageHeader, ErrorDisplay, ConfirmDialog, ListPageSkeleton } from '@/components/common'
import { DepartmentBreadcrumbs } from '@/components/departments'
import { UsersTable } from '@/components/users'
import { useUsers, useDeleteUser, useDeleteConfirmation } from '@/hooks'
import { useDepartmentStore } from '@/stores'
import { ROUTES } from '@/config/constants'
import type { User } from '@/types'

export function UsersListPage() {
  const { currentBase, currentPath } = useDepartmentStore()

  // Filter users by department context
  const { data, isLoading, error, refetch } = useUsers(
    currentBase ? { base: currentBase } : undefined
  )
  const deleteMutation = useDeleteUser()
  const deleteConfirmation = useDeleteConfirmation<User>({
    onDelete: async (user) => { await deleteMutation.mutateAsync(user.uid) },
    getItemName: (user) => user.uid,
    entityType: 'User',
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
            Users
            <Badge variant="secondary">{data?.total || 0}</Badge>
          </span>
        }
        description={
          currentBase
            ? `Manage user accounts in ${currentPath}`
            : 'Manage user accounts in the directory'
        }
        actions={
          <Button asChild>
            <Link to={ROUTES.USER_CREATE}>
              <Plus className="mr-2 h-4 w-4" />
              New User
            </Link>
          </Button>
        }
      />

      {currentBase && (
        <div className="mb-4">
          <DepartmentBreadcrumbs />
        </div>
      )}

      <UsersTable
        users={data?.users ?? []}
        onDelete={deleteConfirmation.requestDelete}
        emptyMessage="No users found"
      />

      <ConfirmDialog {...deleteConfirmation.dialogProps} />
    </div>
  )
}
