/**
 * Mixed Groups List Page
 *
 * Lists all MixedGroups (groupOfNames + posixGroup) and provides CRUD operations.
 */

import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Plus, Layers, RefreshCw, Search } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

import { DeleteDialog, ListPageSkeleton, ErrorDisplay } from '@/components/common'
import { MixedGroupsTable, CreateMixedGroupDialog } from '@/components/plugins/posix'

import { useMixedGroups, useDeleteMixedGroup } from '@/hooks'
import type { MixedGroupListItem } from '@/types/posix'

export function MixedGroupsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [searchQuery, setSearchQuery] = useState('')
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [groupToDelete, setGroupToDelete] = useState<MixedGroupListItem | null>(null)

  // Open create dialog if ?create=true is in URL
  useEffect(() => {
    if (searchParams.get('create') === 'true') {
      setShowCreateDialog(true)
      searchParams.delete('create')
      setSearchParams(searchParams, { replace: true })
    }
  }, [searchParams, setSearchParams])

  const { data: groupsResponse, isLoading, error, refetch } = useMixedGroups()
  const deleteMutation = useDeleteMixedGroup()

  // Filter groups by search query
  const filteredGroups =
    groupsResponse?.groups?.filter(
      (group) =>
        group.cn.toLowerCase().includes(searchQuery.toLowerCase()) ||
        group.description?.toLowerCase().includes(searchQuery.toLowerCase())
    ) ?? []

  const handleCreateSuccess = () => {
    toast.success('Mixed group created successfully')
  }

  const handleDelete = async () => {
    if (!groupToDelete) return

    try {
      await deleteMutation.mutateAsync(groupToDelete.cn)
      toast.success(`Mixed group "${groupToDelete.cn}" deleted successfully`)
      setGroupToDelete(null)
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to delete mixed group'
      )
    }
  }

  if (isLoading) {
    return <ListPageSkeleton />
  }

  if (error) {
    return (
      <div className="container mx-auto py-6">
        <ErrorDisplay
          title="Failed to load mixed groups"
          message={error.message}
          onRetry={() => refetch()}
        />
      </div>
    )
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Layers className="h-6 w-6" />
            Mixed Groups
          </h1>
          <p className="text-muted-foreground">
            Groups combining LDAP membership (groupOfNames) with POSIX permissions
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Create Group
        </Button>
      </div>

      {/* Search and Stats */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search groups..."
            className="pl-9"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <Badge variant="secondary">
          {groupsResponse?.groups?.length ?? 0} group
          {(groupsResponse?.groups?.length ?? 0) !== 1 ? 's' : ''}
        </Badge>
        <Button variant="outline" size="icon" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* Groups Table */}
      <Card>
        <CardHeader>
          <CardTitle>Mixed Groups</CardTitle>
          <CardDescription>
            Mixed groups combine LDAP groupOfNames (member DNs) for application
            access with POSIX posixGroup (memberUid) for UNIX permissions
          </CardDescription>
        </CardHeader>
        <CardContent>
          <MixedGroupsTable
            groups={filteredGroups}
            onDelete={setGroupToDelete}
            emptyMessage={
              searchQuery ? 'No groups match your search' : 'No mixed groups found'
            }
          />
        </CardContent>
      </Card>

      {/* Create Dialog */}
      <CreateMixedGroupDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        onSuccess={handleCreateSuccess}
      />

      {/* Delete Confirmation */}
      <DeleteDialog
        open={!!groupToDelete}
        onOpenChange={(open) => !open && setGroupToDelete(null)}
        onConfirm={handleDelete}
        itemName={groupToDelete?.cn ?? ''}
        itemType="Mixed Group"
        isLoading={deleteMutation.isPending}
      />
    </div>
  )
}
