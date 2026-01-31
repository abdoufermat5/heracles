import { useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { Plus, UsersRound, Terminal, Layers } from 'lucide-react'
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
import { PageHeader, LoadingPage, ErrorDisplay, ConfirmDialog } from '@/components/common'
import { DepartmentBreadcrumbs } from '@/components/departments'
import { LdapGroupsTable } from '@/components/groups'
import { PosixGroupsTable, MixedGroupsTable } from '@/components/plugins/posix/groups'
import { useGroups, useDeleteGroup } from '@/hooks'
import { usePosixGroups, useDeletePosixGroup, useMixedGroups, useDeleteMixedGroup } from '@/hooks/use-posix'
import { useDepartmentStore } from '@/stores'
import { ROUTES } from '@/config/constants'
import type { Group } from '@/types'
import type { PosixGroupListItem, MixedGroupListItem } from '@/types/posix'

type GroupType = 'ldap' | 'posix' | 'mixed'

export function GroupsListPage() {
  const [activeTab, setActiveTab] = useState<GroupType>('ldap')
  const [deleteGroup, setDeleteGroup] = useState<Group | null>(null)
  const [deletePosixGroup, setDeletePosixGroup] = useState<PosixGroupListItem | null>(null)
  const [deleteMixedGroup, setDeleteMixedGroup] = useState<MixedGroupListItem | null>(null)
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
      await deletePosixMutation.mutateAsync({
        cn: deletePosixGroup.cn,
        baseDn: currentBase || undefined
      })
      toast.success(`POSIX group "${deletePosixGroup.cn}" deleted successfully`)
      setDeletePosixGroup(null)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to delete POSIX group')
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
        description={
          currentBase
            ? `Manage groups in ${currentPath}`
            : 'Manage groups in the directory'
        }
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

      {currentBase && (
        <div className="mb-4">
          <DepartmentBreadcrumbs />
        </div>
      )}

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as GroupType)} className="space-y-4">
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
