/**
 * Mixed Groups List Page
 *
 * Lists all MixedGroups (groupOfNames + posixGroup) and provides CRUD operations.
 */

import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Plus, Layers, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
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

  const handleCreateSuccess = () => {
    toast.success('Mixed group created successfully')
  }

  const handleDelete = async () => {
    if (!groupToDelete) return

    try {
      await deleteMutation.mutateAsync({ cn: groupToDelete.cn })
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

  const totalGroups = groupsResponse?.groups?.length ?? 0

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
        <div className="flex items-center gap-2">
          <Badge variant="secondary">
            {totalGroups} group{totalGroups !== 1 ? 's' : ''}
          </Badge>
          <Button variant="outline" size="icon" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button onClick={() => setShowCreateDialog(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Create Group
          </Button>
        </div>
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
            groups={groupsResponse?.groups ?? []}
            onDelete={setGroupToDelete}
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
