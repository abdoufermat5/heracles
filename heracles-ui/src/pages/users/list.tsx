import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { Plus, Search, MoreHorizontal, Pencil, Trash2, Key, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader, LoadingPage, ErrorDisplay, EmptyState, ConfirmDialog } from '@/components/common'
import { useUsers, useDeleteUser } from '@/hooks'
import { ROUTES } from '@/config/constants'
import type { User } from '@/types'

export function UsersListPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [deleteUser, setDeleteUser] = useState<User | null>(null)

  const { data, isLoading, error, refetch } = useUsers({ search: search || undefined })
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
        breadcrumbs={[{ label: 'Users' }]}
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
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              All Users
              <Badge variant="secondary">{data?.total || 0}</Badge>
            </CardTitle>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search users..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-9 w-64"
                />
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {data?.users.length === 0 ? (
            <EmptyState
              icon={Users}
              title="No users found"
              description={search ? 'Try a different search term' : 'Get started by creating your first user'}
              action={
                !search
                  ? {
                      label: 'Create User',
                      onClick: () => navigate(ROUTES.USER_CREATE),
                    }
                  : undefined
              }
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Username</TableHead>
                  <TableHead>Display Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>UID</TableHead>
                  <TableHead className="w-[80px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.users.map((user) => (
                  <TableRow key={user.dn}>
                    <TableCell>
                      <Link
                        to={ROUTES.USER_DETAIL.replace(':uid', user.uid)}
                        className="font-medium text-primary hover:underline"
                      >
                        {user.uid}
                      </Link>
                    </TableCell>
                    <TableCell>{user.displayName || `${user.givenName} ${user.sn}`}</TableCell>
                    <TableCell>{user.mail || '-'}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{user.uidNumber || '-'}</Badge>
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem asChild>
                            <Link to={ROUTES.USER_DETAIL.replace(':uid', user.uid)}>
                              <Pencil className="mr-2 h-4 w-4" />
                              Edit
                            </Link>
                          </DropdownMenuItem>
                          <DropdownMenuItem>
                            <Key className="mr-2 h-4 w-4" />
                            Set Password
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-destructive focus:text-destructive"
                            onClick={() => setDeleteUser(user)}
                          >
                            <Trash2 className="mr-2 h-4 w-4" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
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
