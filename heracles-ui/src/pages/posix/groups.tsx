/**
 * POSIX Groups List Page
 *
 * Lists all standalone POSIX groups and provides CRUD operations.
 */

import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Plus, Users, RefreshCw } from 'lucide-react'
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
import { PosixGroupsTable, CreatePosixGroupDialog } from '@/components/plugins/posix'

import { usePosixGroups, useDeletePosixGroup } from '@/hooks'
import type { PosixGroupListItem } from '@/types/posix'

export function PosixGroupsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [groupToDelete, setGroupToDelete] = useState<PosixGroupListItem | null>(null)

  // Open create dialog if ?create=true is in URL
  useEffect(() => {
    if (searchParams.get('create') === 'true') {
      setShowCreateDialog(true)
      searchParams.delete('create')
      setSearchParams(searchParams, { replace: true })
    }
  }, [searchParams, setSearchParams])

  const { data: groupsResponse, isLoading, error, refetch } = usePosixGroups()
  const deleteMutation = useDeletePosixGroup()

  const handleCreateSuccess = () => {
    toast.success('POSIX group created successfully')
  }

  const handleDelete = async () => {
    if (!groupToDelete) return

    try {
      await deleteMutation.mutateAsync(groupToDelete.cn)
      toast.success(`POSIX group "${groupToDelete.cn}" deleted successfully`)
      setGroupToDelete(null)
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to delete POSIX group'
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
          title="Failed to load POSIX groups"
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
            <Users className="h-6 w-6" />
            POSIX Groups
          </h1>
          <p className="text-muted-foreground">
            Manage standalone POSIX groups for UNIX/Linux systems
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary">
            {groupsResponse?.total ?? 0} group
            {(groupsResponse?.total ?? 0) !== 1 ? 's' : ''}
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
          <CardTitle>POSIX Groups</CardTitle>
          <CardDescription>
            These are standalone POSIX groups (posixGroup objectClass) used for
            UNIX/Linux permissions
          </CardDescription>
        </CardHeader>
        <CardContent>
          <PosixGroupsTable
            groups={groupsResponse?.groups ?? []}
            onDelete={setGroupToDelete}
          />
        </CardContent>
      </Card>

      {/* Create Dialog */}
      <CreatePosixGroupDialog
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
        itemType="POSIX Group"
        isLoading={deleteMutation.isPending}
      />
    </div>
  )
}
