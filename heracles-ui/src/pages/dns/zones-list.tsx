/**
 * DNS Zones List Page
 *
 * Lists all DNS zones with create, edit, and delete capabilities.
 */

import { useState } from 'react'
import { Plus, Globe, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { PageHeader } from '@/components/common/page-header'
import { DnsZonesTable, CreateZoneDialog } from '@/components/plugins/dns'
import { useDnsZones, useDeleteDnsZone } from '@/hooks/use-dns'
import type { DnsZoneListItem } from '@/types/dns'

export function DnsZonesListPage() {
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [zoneToDelete, setZoneToDelete] = useState<DnsZoneListItem | null>(null)

  const { data, isLoading, refetch, isRefetching } = useDnsZones()
  const deleteMutation = useDeleteDnsZone()

  const handleDelete = async () => {
    if (!zoneToDelete) return

    try {
      await deleteMutation.mutateAsync(zoneToDelete.zoneName)
      toast.success(`Zone "${zoneToDelete.zoneName}" deleted successfully`)
      setZoneToDelete(null)
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to delete zone'
      )
    }
  }

  return (
    <div className="container py-6 space-y-6">
      <PageHeader
        title="DNS Zones"
        description="Manage DNS zones and records"
        icon={<Globe className="h-8 w-8" />}
        actions={
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="icon"
              onClick={() => refetch()}
              disabled={isRefetching}
            >
              <RefreshCw
                className={`h-4 w-4 ${isRefetching ? 'animate-spin' : ''}`}
              />
              <span className="sr-only">Refresh</span>
            </Button>
            <Button onClick={() => setCreateDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Zone
            </Button>
          </div>
        }
      />

      <DnsZonesTable
        zones={data?.zones ?? []}
        isLoading={isLoading}
        onDelete={setZoneToDelete}
      />

      <CreateZoneDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
      />

      <AlertDialog
        open={!!zoneToDelete}
        onOpenChange={(open) => !open && setZoneToDelete(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete DNS Zone</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the zone{' '}
              <code className="font-mono font-medium">
                {zoneToDelete?.zoneName}
              </code>
              ? This will also delete all records within the zone. This action
              cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete Zone'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
