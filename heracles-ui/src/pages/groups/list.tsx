import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { Plus, Search, MoreHorizontal, Pencil, Trash2, UsersRound, Users, Terminal, Layers } from 'lucide-react'
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { PageHeader, LoadingPage, ErrorDisplay, EmptyState, ConfirmDialog } from '@/components/common'
import { useGroups, useDeleteGroup } from '@/hooks'
import { usePosixGroups, useDeletePosixGroup, useMixedGroups, useDeleteMixedGroup } from '@/hooks/use-posix'
import { ROUTES } from '@/config/constants'
import type { Group } from '@/types'
import type { PosixGroupListItem, MixedGroupListItem } from '@/types/posix'

type GroupType = 'ldap' | 'posix' | 'mixed'

export function GroupsListPage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<GroupType>('ldap')
  const [search, setSearch] = useState('')
  const [deleteGroup, setDeleteGroup] = useState<Group | null>(null)
  const [deletePosixGroup, setDeletePosixGroup] = useState<PosixGroupListItem | null>(null)
  const [deleteMixedGroup, setDeleteMixedGroup] = useState<MixedGroupListItem | null>(null)

  // LDAP Groups (groupOfNames)
  const { data: ldapData, isLoading: ldapLoading, error: ldapError, refetch: refetchLdap } = useGroups({ search: search || undefined })
  const deleteLdapMutation = useDeleteGroup()

  // POSIX Groups (posixGroup)
  const { data: posixData, isLoading: posixLoading, error: posixError, refetch: refetchPosix } = usePosixGroups()
  const deletePosixMutation = useDeletePosixGroup()

  // Mixed Groups (groupOfNames + posixGroup)
  const { data: mixedData, isLoading: mixedLoading, error: mixedError, refetch: refetchMixed } = useMixedGroups()
  const deleteMixedMutation = useDeleteMixedGroup()

  // Filter POSIX groups by search
  const filteredPosixGroups = posixData?.groups?.filter((group) =>
    group.cn.toLowerCase().includes(search.toLowerCase()) ||
    (group.description?.toLowerCase().includes(search.toLowerCase()))
  ) ?? []

  // Filter Mixed groups by search
  const filteredMixedGroups = mixedData?.groups?.filter((group) =>
    group.cn.toLowerCase().includes(search.toLowerCase()) ||
    (group.description?.toLowerCase().includes(search.toLowerCase()))
  ) ?? []

  const handleDeleteLdap = async () => {
    if (!deleteGroup) return
    try {
      await deleteLdapMutation.mutateAsync(deleteGroup.cn)
      toast.success(`Group "${deleteGroup.cn}" deleted successfully`)
      setDeleteGroup(null)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to delete group')
    }
  }

  const handleDeletePosix = async () => {
    if (!deletePosixGroup) return
    try {
      await deletePosixMutation.mutateAsync(deletePosixGroup.cn)
      toast.success(`POSIX group "${deletePosixGroup.cn}" deleted successfully`)
      setDeletePosixGroup(null)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to delete POSIX group')
    }
  }

  const handleDeleteMixed = async () => {
    if (!deleteMixedGroup) return
    try {
      await deleteMixedMutation.mutateAsync(deleteMixedGroup.cn)
      toast.success(`Mixed group "${deleteMixedGroup.cn}" deleted successfully`)
      setDeleteMixedGroup(null)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to delete mixed group')
    }
  }

  const isLoading = activeTab === 'ldap' ? ldapLoading : activeTab === 'posix' ? posixLoading : mixedLoading
  const error = activeTab === 'ldap' ? ldapError : activeTab === 'posix' ? posixError : mixedError
  const refetch = activeTab === 'ldap' ? refetchLdap : activeTab === 'posix' ? refetchPosix : refetchMixed

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
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                New Group
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem asChild>
                <Link to={ROUTES.GROUP_CREATE}>
                  <UsersRound className="mr-2 h-4 w-4" />
                  LDAP Group
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link to="/posix/groups?create=true">
                  <Terminal className="mr-2 h-4 w-4" />
                  POSIX Group
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link to="/posix/mixed-groups?create=true">
                  <Layers className="mr-2 h-4 w-4" />
                  Mixed Group
                </Link>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        }
      />

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as GroupType)} className="space-y-4">
        <div className="flex items-center justify-between">
          <TabsList>
            <TabsTrigger value="ldap" className="gap-2">
              <UsersRound className="h-4 w-4" />
              LDAP Groups
              <Badge variant="secondary" className="ml-1">{ldapData?.total || 0}</Badge>
            </TabsTrigger>
            <TabsTrigger value="posix" className="gap-2">
              <Terminal className="h-4 w-4" />
              POSIX Groups
              <Badge variant="secondary" className="ml-1">{posixData?.groups?.length || 0}</Badge>
            </TabsTrigger>
            <TabsTrigger value="mixed" className="gap-2">
              <Layers className="h-4 w-4" />
              Mixed Groups
              <Badge variant="secondary" className="ml-1">{mixedData?.groups?.length || 0}</Badge>
            </TabsTrigger>
          </TabsList>
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

        {/* LDAP Groups Tab */}
        <TabsContent value="ldap">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <UsersRound className="h-5 w-5" />
                LDAP Groups (groupOfNames)
              </CardTitle>
            </CardHeader>
            <CardContent>
              {ldapData?.groups.length === 0 ? (
                <EmptyState
                  icon={UsersRound}
                  title="No LDAP groups found"
                  description={search ? 'Try a different search term' : 'Get started by creating your first LDAP group'}
                  action={
                    !search
                      ? {
                          label: 'Create LDAP Group',
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
                    {ldapData?.groups.map((group) => (
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
        </TabsContent>

        {/* POSIX Groups Tab */}
        <TabsContent value="posix">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Terminal className="h-5 w-5" />
                POSIX Groups (posixGroup)
              </CardTitle>
            </CardHeader>
            <CardContent>
              {filteredPosixGroups.length === 0 ? (
                <EmptyState
                  icon={Terminal}
                  title="No POSIX groups found"
                  description={search ? 'Try a different search term' : 'Get started by creating your first POSIX group'}
                  action={
                    !search
                      ? {
                          label: 'Create POSIX Group',
                          onClick: () => navigate('/posix/groups?create=true'),
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
                    {filteredPosixGroups.map((group) => (
                      <TableRow key={group.cn}>
                        <TableCell>
                          <Link
                            to={`/posix/groups/${group.cn}`}
                            className="font-medium text-primary hover:underline"
                          >
                            {group.cn}
                          </Link>
                        </TableCell>
                        <TableCell>{group.description || '-'}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{group.gidNumber}</Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">
                            <Users className="mr-1 h-3 w-3" />
                            {group.memberCount}
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
                                <Link to={`/posix/groups/${group.cn}`}>
                                  <Pencil className="mr-2 h-4 w-4" />
                                  Edit
                                </Link>
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                className="text-destructive focus:text-destructive"
                                onClick={() => setDeletePosixGroup(group)}
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
        </TabsContent>

        {/* Mixed Groups Tab */}
        <TabsContent value="mixed">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Layers className="h-5 w-5" />
                Mixed Groups (groupOfNames + posixGroup)
              </CardTitle>
            </CardHeader>
            <CardContent>
              {filteredMixedGroups.length === 0 ? (
                <EmptyState
                  icon={Layers}
                  title="No mixed groups found"
                  description={search ? 'Try a different search term' : 'Mixed groups combine LDAP and POSIX group features'}
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Group Name</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead>GID</TableHead>
                      <TableHead>LDAP Members</TableHead>
                      <TableHead>POSIX Members</TableHead>
                      <TableHead className="w-[80px]"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredMixedGroups.map((group) => (
                      <TableRow key={group.cn}>
                        <TableCell>
                          <span className="font-medium">{group.cn}</span>
                        </TableCell>
                        <TableCell>{group.description || '-'}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{group.gidNumber}</Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">
                            <Users className="mr-1 h-3 w-3" />
                            {group.memberCount}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">
                            <Terminal className="mr-1 h-3 w-3" />
                            {group.memberUidCount}
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
                              <DropdownMenuItem
                                className="text-destructive focus:text-destructive"
                                onClick={() => setDeleteMixedGroup(group)}
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
        </TabsContent>
      </Tabs>

      {/* Delete dialogs */}
      <ConfirmDialog
        open={!!deleteGroup}
        onOpenChange={(open) => !open && setDeleteGroup(null)}
        title="Delete LDAP Group"
        description={`Are you sure you want to delete group "${deleteGroup?.cn}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={handleDeleteLdap}
        isLoading={deleteLdapMutation.isPending}
      />

      <ConfirmDialog
        open={!!deletePosixGroup}
        onOpenChange={(open) => !open && setDeletePosixGroup(null)}
        title="Delete POSIX Group"
        description={`Are you sure you want to delete POSIX group "${deletePosixGroup?.cn}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={handleDeletePosix}
        isLoading={deletePosixMutation.isPending}
      />

      <ConfirmDialog
        open={!!deleteMixedGroup}
        onOpenChange={(open) => !open && setDeleteMixedGroup(null)}
        title="Delete Mixed Group"
        description={`Are you sure you want to delete mixed group "${deleteMixedGroup?.cn}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={handleDeleteMixed}
        isLoading={deleteMixedMutation.isPending}
      />
    </div>
  )
}
