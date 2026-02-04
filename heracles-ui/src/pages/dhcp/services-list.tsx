/**
 * DHCP Services List Page
 *
 * Lists all DHCP services with create, edit, and delete capabilities.
 */

import { useState } from 'react'
import { Plus, Network, RefreshCw } from 'lucide-react'
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
import { DhcpServicesTable, CreateDhcpServiceDialog } from '@/components/plugins/dhcp'
import { useDhcpServices, useCreateDhcpService, useDeleteDhcpService } from '@/hooks/use-dhcp'
import type { DhcpServiceListItem } from '@/types/dhcp'
import { useDepartmentStore } from '@/stores'

export function DhcpServicesListPage() {
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [serviceToDelete, setServiceToDelete] = useState<DhcpServiceListItem | null>(null)
  const { currentBase } = useDepartmentStore()

  // Use actual hooks for API calls
  const { data, isLoading, refetch, isRefetching } = useDhcpServices({
    base: currentBase ?? undefined
  })
  const createMutation = useCreateDhcpService()
  const deleteMutation = useDeleteDhcpService()

  const handleRefresh = async () => {
    await refetch()
  }

  const handleDelete = async () => {
    if (!serviceToDelete) return

    try {
      await deleteMutation.mutateAsync({
        serviceCn: serviceToDelete.cn,
        recursive: true,
        baseDn: currentBase || undefined
      })
      toast.success(`Service "${serviceToDelete.cn}" deleted successfully`)
      setServiceToDelete(null)
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to delete service'
      )
    }
  }

  const handleCreateService = async (formData: {
    cn: string
    description?: string
    statements?: string[]
    options?: string[]
  }) => {
    try {
      await createMutation.mutateAsync({
        data: {
          cn: formData.cn,
          comments: formData.description,
          dhcpStatements: formData.statements,
          dhcpOptions: formData.options,
        },
        baseDn: currentBase || undefined,
      })
      toast.success(`Service "${formData.cn}" created successfully`)
      setCreateDialogOpen(false)
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to create service'
      )
    }
  }

  const services = data?.items ?? []

  return (
    <div className="container py-6 space-y-6">
      <PageHeader
        title="DHCP Services"
        description="Manage DHCP server configurations, subnets, and host reservations"
        actions={
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="icon"
              onClick={handleRefresh}
              disabled={isRefetching}
            >
              <RefreshCw
                className={`h-4 w-4 ${isRefetching ? 'animate-spin' : ''}`}
              />
              <span className="sr-only">Refresh</span>
            </Button>
            <Button onClick={() => setCreateDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Service
            </Button>
          </div>
        }
      />

      <DhcpServicesTable
        services={services}
        isLoading={isLoading}
        onDelete={setServiceToDelete}
        emptyMessage="No DHCP services configured. Create your first service to get started."
      />

      <CreateDhcpServiceDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onSubmit={handleCreateService}
      />

      <AlertDialog
        open={!!serviceToDelete}
        onOpenChange={(open) => !open && setServiceToDelete(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete DHCP Service</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the service{' '}
              <code className="font-mono font-medium">
                {serviceToDelete?.cn}
              </code>
              ? This will also delete all subnets, pools, and hosts within the
              service. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete Service
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
