import { useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { Plus, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader, LoadingPage, ErrorDisplay, ConfirmDialog } from '@/components/common'
import { UsersTable } from '@/components/users'
import { useUsers, useDeleteUser } from '@/hooks'
import { ROUTES } from '@/config/constants'
import type { User } from '@/types'

export function UsersListPage() {
  const [deleteUser, setDeleteUser] = useState<User | null>(null)

  const { data, isLoading, error, refetch } = useUsers()
  const deleteMutation = useDeleteUser()

  const handleDelete = async () => {
    if (!deleteUser) return
    try {
      await deleteMutation.mutateAsync(deleteUser.uid)
      toast.success(`User "${deleteUser.uid}" deleted successfully`)
      setDeleteUser(null)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to delete user')
    }
  }

  if (isLoading) {
    return <LoadingPage message="Loading users..." />
  }

  if (error) {
    return <ErrorDisplay message={error.message} onRetry={() => refetch()} />
  }

  return (
    <div>
      <PageHeader
        title="Users"
        description="Manage user accounts in the directory"
        actions={
          <Button asChild>
            <Link to={ROUTES.USER_CREATE}>
              <Plus className="mr-2 h-4 w-4" />
              New User
            </Link>
          </Button>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            All Users
            <Badge variant="secondary">{data?.total || 0}</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <UsersTable
            users={data?.users ?? []}
            onDelete={setDeleteUser}
            emptyMessage="No users found"
          />
        </CardContent>
      </Card>

      <ConfirmDialog
        open={!!deleteUser}
        onOpenChange={(open) => !open && setDeleteUser(null)}
        title="Delete User"
        description={`Are you sure you want to delete user "${deleteUser?.uid}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
      />
    </div>
  )
}
