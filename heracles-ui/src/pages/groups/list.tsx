import { useState, useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import { Plus, UsersRound, Terminal, Layers, Shield, MoreHorizontal, Trash2, Eye } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { PageHeader, LoadingPage, ErrorDisplay, ConfirmDialog, EmptyState } from '@/components/common'
import { DepartmentBreadcrumbs } from '@/components/departments'
import { LdapGroupsTable } from '@/components/groups'
import { PosixGroupsTable, MixedGroupsTable } from '@/components/plugins/posix/groups'
import { useGroups, useDeleteGroup } from '@/hooks'
import { usePosixGroups, useDeletePosixGroup, useMixedGroups, useDeleteMixedGroup } from '@/hooks/use-posix'
import { useRoles, useDeleteRole } from '@/hooks/use-roles'
import { useDepartmentStore } from '@/stores'
import { AppError } from '@/lib/errors'
import { ROUTES } from '@/config/constants'
import type { Group, Role } from '@/types'
import type { PosixGroupListItem, MixedGroupListItem } from '@/types/posix'

type GroupType = 'ldap' | 'posix' | 'mixed' | 'roles'

export function GroupsListPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  // Get active tab from URL or default to 'ldap'
  const initialTab = (searchParams.get('tab') as GroupType) || 'ldap'
  const [activeTab, setActiveTab] = useState<GroupType>(initialTab)

  // Update URL when tab changes
  const handleTabChange = (value: string) => {
    const newTab = value as GroupType
    setActiveTab(newTab)
    setSearchParams(prev => {
      prev.set('tab', newTab)
      return prev
    }, { replace: true })
  }

  // Sync state if URL changes externally
  useEffect(() => {
    const tabFromUrl = (searchParams.get('tab') as GroupType) || 'ldap'
    if (tabFromUrl !== activeTab) {
      setActiveTab(tabFromUrl)
    }
  }, [searchParams])

  const [deleteGroup, setDeleteGroup] = useState<Group | null>(null)
  const [deletePosixGroup, setDeletePosixGroup] = useState<PosixGroupListItem | null>(null)
  const [deleteMixedGroup, setDeleteMixedGroup] = useState<MixedGroupListItem | null>(null)
  const [deleteRole, setDeleteRoleItem] = useState<Role | null>(null)
  const { currentBase, currentPath } = useDepartmentStore()

  // LDAP Groups (groupOfNames) - filtered by department context
  const { data: ldapData, isLoading: ldapLoading, error: ldapError, refetch: refetchLdap } = useGroups(
    currentBase ? { base: currentBase } : undefined
  )
  const deleteLdapMutation = useDeleteGroup()

  // POSIX Groups (posixGroup)
  const { data: posixData, isLoading: posixLoading, error: posixError, refetch: refetchPosix } = usePosixGroups(
    currentBase ? { base: currentBase } : undefined
  )
  const deletePosixMutation = useDeletePosixGroup()

  // Mixed Groups (groupOfNames + posixGroup)
  const { data: mixedData, isLoading: mixedLoading, error: mixedError, refetch: refetchMixed } = useMixedGroups(
    currentBase ? { base: currentBase } : undefined
  )
  const deleteMixedMutation = useDeleteMixedGroup()

  // Roles (organizationalRole)
  const { data: rolesData, isLoading: rolesLoading, error: rolesError, refetch: refetchRoles } = useRoles(
    currentBase ? { base: currentBase } : undefined
  )
  const deleteRoleMutation = useDeleteRole()

  const handleDeleteLdap = async () => {
    if (!deleteGroup) return
    try {
      await deleteLdapMutation.mutateAsync(deleteGroup.cn)
      toast.success(`Group "${deleteGroup.cn}" deleted successfully`)
      setDeleteGroup(null)
    } catch (error) {
      AppError.toastError(error, 'Failed to delete group')
    }
  }

  const handleDeletePosix = async () => {
    if (!deletePosixGroup) return
    try {
      await deletePosixMutation.mutateAsync({
        cn: deletePosixGroup.cn,
        baseDn: currentBase || undefined
      })
      toast.success(`POSIX group "${deletePosixGroup.cn}" deleted successfully`)
      setDeletePosixGroup(null)
    } catch (error) {
      AppError.toastError(error, 'Failed to delete POSIX group')
    }
  }

  const handleDeleteMixed = async () => {
    if (!deleteMixedGroup) return
    try {
      await deleteMixedMutation.mutateAsync({
        cn: deleteMixedGroup.cn,
        baseDn: currentBase || undefined
      })
      toast.success(`Mixed group "${deleteMixedGroup.cn}" deleted successfully`)
      setDeleteMixedGroup(null)
    } catch (error) {
      AppError.toastError(error, 'Failed to delete mixed group')
    }
  }

  const handleDeleteRole = async () => {
    if (!deleteRole) return
    try {
      await deleteRoleMutation.mutateAsync(deleteRole.cn)
      toast.success(`Role "${deleteRole.cn}" deleted successfully`)
      setDeleteRoleItem(null)
    } catch (error) {
      AppError.toastError(error, 'Failed to delete role')
    }
  }

  const isLoading =
    activeTab === 'ldap' ? ldapLoading :
      activeTab === 'posix' ? posixLoading :
        activeTab === 'mixed' ? mixedLoading :
          rolesLoading
  const error =
    activeTab === 'ldap' ? ldapError :
      activeTab === 'posix' ? posixError :
        activeTab === 'mixed' ? mixedError :
          rolesError
  const refetch =
    activeTab === 'ldap' ? refetchLdap :
      activeTab === 'posix' ? refetchPosix :
        activeTab === 'mixed' ? refetchMixed :
          refetchRoles

  if (isLoading) {
    return <LoadingPage message="Loading groups..." />
  }

  if (error) {
    return <ErrorDisplay message={error.message} onRetry={() => refetch()} />
  }

  return (
    <div>
      <PageHeader
        title="Groups & Roles"
        description={
          currentBase
            ? `Manage groups and roles in ${currentPath}`
            : 'Manage groups and roles in the directory'
        }
        actions={
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                New
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
              <DropdownMenuItem asChild>
                <Link to="/roles/create">
                  <Shield className="mr-2 h-4 w-4" />
                  Role
                </Link>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        }
      />

      {currentBase && (
        <div className="mb-4">
          <DepartmentBreadcrumbs />
        </div>
      )}

      <Tabs value={activeTab} onValueChange={handleTabChange} className="space-y-4">
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
          <TabsTrigger value="roles" className="gap-2">
            <Shield className="h-4 w-4" />
            Roles
            <Badge variant="secondary" className="ml-1">{rolesData?.total || 0}</Badge>
          </TabsTrigger>
        </TabsList>

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
              <LdapGroupsTable
                groups={ldapData?.groups ?? []}
                onDelete={setDeleteGroup}
                emptyMessage="No LDAP groups found"
              />
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
              <PosixGroupsTable
                groups={posixData?.groups ?? []}
                onDelete={setDeletePosixGroup}
                emptyMessage="No POSIX groups found"
              />
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
              <MixedGroupsTable
                groups={mixedData?.groups ?? []}
                onDelete={setDeleteMixedGroup}
                emptyMessage="No mixed groups found"
              />
            </CardContent>
          </Card>
        </TabsContent>

        {/* Roles Tab */}
        <TabsContent value="roles">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Organizational Roles (organizationalRole)
              </CardTitle>
            </CardHeader>
            <CardContent>
              {rolesData?.roles && rolesData.roles.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead>Members</TableHead>
                      <TableHead className="w-[100px]">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rolesData.roles.map((role) => (
                      <TableRow key={role.dn}>
                        <TableCell className="font-medium">{role.cn}</TableCell>
                        <TableCell className="text-muted-foreground">
                          {role.description || '-'}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{role.memberCount} members</Badge>
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
                                <Link to={`/roles/${role.cn}`}>
                                  <Eye className="mr-2 h-4 w-4" />
                                  View
                                </Link>
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onClick={() => setDeleteRoleItem(role)}
                                className="text-destructive"
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
              ) : (
                <EmptyState
                  icon={Shield}
                  title="No roles found"
                  description="Create a role to assign users to organizational responsibilities."
                  action={{
                    label: 'Create Role',
                    onClick: () => navigate('/roles/create'),
                  }}
                />
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

      <ConfirmDialog
        open={!!deleteRole}
        onOpenChange={(open) => !open && setDeleteRoleItem(null)}
        title="Delete Role"
        description={`Are you sure you want to delete role "${deleteRole?.cn}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={handleDeleteRole}
        isLoading={deleteRoleMutation.isPending}
      />
    </div>
  )
}

