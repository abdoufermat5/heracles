import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { Plus, Search, MoreHorizontal, Pencil, Trash2, UsersRound, Users } from 'lucide-react'
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
import { useGroups, useDeleteGroup } from '@/hooks'
import { ROUTES } from '@/config/constants'
import type { Group } from '@/types'

export function GroupsListPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [deleteGroup, setDeleteGroup] = useState<Group | null>(null)

  const { data, isLoading, error, refetch } = useGroups({ search: search || undefined })
  const deleteMutation = useDeleteGroup()

  const handleDelete = async () => {
    if (!deleteGroup) return
    try {
      await deleteMutation.mutateAsync(deleteGroup.cn)
      toast.success(`Group "${deleteGroup.cn}" deleted successfully`)
      setDeleteGroup(null)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to delete group')
    }
  }

  if (isLoading) {
    return <LoadingPage message="Loading groups..." />
  }

  if (error) {
    return <ErrorDisplay message={error.message} onRetry={() => refetch()} />
  }

  return (
    <div>
      <PageHeader
        title="Groups"
        description="Manage groups in the directory"
        breadcrumbs={[{ label: 'Groups' }]}
        actions={
          <Button asChild>
            <Link to={ROUTES.GROUP_CREATE}>
              <Plus className="mr-2 h-4 w-4" />
              New Group
            </Link>
          </Button>
        }
      />

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <UsersRound className="h-5 w-5" />
              All Groups
              <Badge variant="secondary">{data?.total || 0}</Badge>
            </CardTitle>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search groups..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-9 w-64"
                />
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {data?.groups.length === 0 ? (
            <EmptyState
              icon={UsersRound}
              title="No groups found"
              description={search ? 'Try a different search term' : 'Get started by creating your first group'}
              action={
                !search
                  ? {
                      label: 'Create Group',
                      onClick: () => navigate(ROUTES.GROUP_CREATE),
                    }
                  : undefined
              }
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Group Name</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>GID</TableHead>
                  <TableHead>Members</TableHead>
                  <TableHead className="w-[80px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.groups.map((group) => (
                  <TableRow key={group.dn}>
                    <TableCell>
                      <Link
                        to={ROUTES.GROUP_DETAIL.replace(':cn', group.cn)}
                        className="font-medium text-primary hover:underline"
                      >
                        {group.cn}
                      </Link>
                    </TableCell>
                    <TableCell>{group.description || '-'}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{group.gidNumber || '-'}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">
                        <Users className="mr-1 h-3 w-3" />
                        {group.memberUid?.length || group.member?.length || 0}
                      </Badge>
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
                            <Link to={ROUTES.GROUP_DETAIL.replace(':cn', group.cn)}>
                              <Pencil className="mr-2 h-4 w-4" />
                              Edit
                            </Link>
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-destructive focus:text-destructive"
                            onClick={() => setDeleteGroup(group)}
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
        open={!!deleteGroup}
        onOpenChange={(open) => !open && setDeleteGroup(null)}
        title="Delete Group"
        description={`Are you sure you want to delete group "${deleteGroup?.cn}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
      />
    </div>
  )
}
