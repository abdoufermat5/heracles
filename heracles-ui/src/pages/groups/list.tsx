import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Plus, UsersRound, Terminal, Layers, Shield } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { PageHeader, ErrorDisplay, ConfirmDialog, ListPageSkeleton } from '@/components/common'
import { DepartmentBreadcrumbs } from '@/components/departments'
import { LdapGroupsTable } from '@/components/groups'
import { RolesTable } from '@/components/roles'
import { PosixGroupsTable, MixedGroupsTable } from '@/components/plugins/posix/groups'
import { useGroups, useDeleteGroup, useDeleteConfirmation } from '@/hooks'
import { usePosixGroups, useDeletePosixGroup, useMixedGroups, useDeleteMixedGroup } from '@/hooks/use-posix'
import { useRoles, useDeleteRole } from '@/hooks/use-roles'
import { useDepartmentStore } from '@/stores'
import { ROUTES } from '@/config/constants'
import type { Group, Role } from '@/types'
import type { PosixGroupListItem, MixedGroupListItem } from '@/types/posix'

type GroupType = 'ldap' | 'posix' | 'mixed' | 'roles'

export function GroupsListPage() {
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

  // Delete confirmation hooks - replaces 4x useState + handleDelete patterns
  const ldapDelete = useDeleteConfirmation<Group>({
    onDelete: async (group) => { await deleteLdapMutation.mutateAsync(group.cn) },
    getItemName: (group) => group.cn,
    entityType: 'LDAP Group',
  })

  const posixDelete = useDeleteConfirmation<PosixGroupListItem>({
    onDelete: async (group) => {
      await deletePosixMutation.mutateAsync({
        cn: group.cn,
        baseDn: currentBase || undefined,
      })
    },
    getItemName: (group) => group.cn,
    entityType: 'POSIX Group',
  })

  const mixedDelete = useDeleteConfirmation<MixedGroupListItem>({
    onDelete: async (group) => {
      await deleteMixedMutation.mutateAsync({
        cn: group.cn,
        baseDn: currentBase || undefined,
      })
    },
    getItemName: (group) => group.cn,
    entityType: 'Mixed Group',
  })

  const roleDelete = useDeleteConfirmation<Role>({
    onDelete: async (role) => { await deleteRoleMutation.mutateAsync(role.cn) },
    getItemName: (role) => role.cn,
    entityType: 'Role',
  })

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
    return <ListPageSkeleton />
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
          <LdapGroupsTable
            groups={ldapData?.groups ?? []}
            onDelete={ldapDelete.requestDelete}
            emptyMessage="No LDAP groups found"
          />
        </TabsContent>

        {/* POSIX Groups Tab */}
        <TabsContent value="posix">
          <PosixGroupsTable
            groups={posixData?.groups ?? []}
            onDelete={posixDelete.requestDelete}
            emptyMessage="No POSIX groups found"
          />
        </TabsContent>

        {/* Mixed Groups Tab */}
        <TabsContent value="mixed">
          <MixedGroupsTable
            groups={mixedData?.groups ?? []}
            onDelete={mixedDelete.requestDelete}
            emptyMessage="No mixed groups found"
          />
        </TabsContent>

        {/* Roles Tab */}
        <TabsContent value="roles">
          <RolesTable
            roles={rolesData?.roles ?? []}
            onDelete={roleDelete.requestDelete}
            emptyMessage="No roles found"
          />
        </TabsContent>
      </Tabs>

      {/* Delete dialogs - using hook dialogProps */}
      <ConfirmDialog {...ldapDelete.dialogProps} />
      <ConfirmDialog {...posixDelete.dialogProps} />
      <ConfirmDialog {...mixedDelete.dialogProps} />
      <ConfirmDialog {...roleDelete.dialogProps} />
    </div>
  )
}
