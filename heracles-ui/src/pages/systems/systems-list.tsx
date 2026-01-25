/**
 * Systems List Page
 *
 * Lists all systems with filtering by type and CRUD operations.
 */

import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Plus,
  Server,
  RefreshCw,
  Monitor,
  Printer,
  Cpu,
  Phone,
  Smartphone,
  MonitorSmartphone,
} from 'lucide-react'
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
import { Skeleton } from '@/components/ui/skeleton'

import { DeleteDialog } from '@/components/common'
import {
  SystemsTable,
  CreateSystemDialog,
  SystemTypeTabs,
} from '@/components/plugins/systems'

import { useSystems, useDeleteSystem } from '@/hooks/use-systems'
import type { SystemListItem, SystemType } from '@/types/systems'
import { SYSTEM_TYPE_LABELS } from '@/types/systems'

export function SystemsListPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [systemToDelete, setSystemToDelete] = useState<SystemListItem | null>(
    null
  )
  const [selectedType, setSelectedType] = useState<SystemType | 'all'>('all')

  // Open create dialog if ?create=true is in URL
  useEffect(() => {
    if (searchParams.get('create') === 'true') {
      setShowCreateDialog(true)
      searchParams.delete('create')
      setSearchParams(searchParams, { replace: true })
    }
    // Set type from URL if present
    const typeParam = searchParams.get('type')
    if (
      typeParam &&
      [
        'server',
        'workstation',
        'terminal',
        'printer',
        'component',
        'phone',
        'mobile',
      ].includes(typeParam)
    ) {
      setSelectedType(typeParam as SystemType)
    }
  }, [searchParams, setSearchParams])

  const {
    data: systemsResponse,
    isLoading,
    error,
    refetch,
  } = useSystems({
    system_type: selectedType === 'all' ? undefined : selectedType,
  })

  const deleteMutation = useDeleteSystem()

  const handleDelete = async () => {
    if (!systemToDelete) return

    try {
      await deleteMutation.mutateAsync({
        systemType: systemToDelete.systemType,
        cn: systemToDelete.cn,
      })
      toast.success(`System "${systemToDelete.cn}" deleted successfully`)
      setSystemToDelete(null)
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to delete system'
      )
    }
  }

  const handleTypeChange = (type: SystemType | 'all') => {
    setSelectedType(type)
    if (type === 'all') {
      searchParams.delete('type')
    } else {
      searchParams.set('type', type)
    }
    setSearchParams(searchParams, { replace: true })
  }

  // Get icon for current type
  const getTypeIcon = () => {
    const icons: Record<SystemType | 'all', React.ElementType> = {
      all: Server,
      server: Server,
      workstation: Monitor,
      terminal: MonitorSmartphone,
      printer: Printer,
      component: Cpu,
      phone: Phone,
      mobile: Smartphone,
    }
    return icons[selectedType]
  }

  const TypeIcon = getTypeIcon()

  if (isLoading) {
    return (
      <div className="container mx-auto py-6 space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-32" />
        </div>
        <Skeleton className="h-12 w-full" />
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container mx-auto py-6">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-8 text-destructive">
              <p>Failed to load systems</p>
              <Button
                variant="outline"
                size="sm"
                className="mt-4"
                onClick={() => refetch()}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <TypeIcon className="h-6 w-6" />
            {selectedType === 'all'
              ? 'Systems'
              : SYSTEM_TYPE_LABELS[selectedType]}
          </h1>
          <p className="text-muted-foreground">
            Manage servers, workstations, printers, and other systems
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Add System
        </Button>
      </div>

      {/* Type Tabs */}
      <SystemTypeTabs value={selectedType} onValueChange={handleTypeChange} />

      {/* Stats and Refresh */}
      <div className="flex items-center gap-4">
        <Badge variant="secondary">
          {systemsResponse?.systems?.length ?? 0} system
          {(systemsResponse?.systems?.length ?? 0) !== 1 ? 's' : ''}
        </Badge>
        <Button variant="outline" size="icon" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* Systems Table */}
      <Card>
        <CardHeader>
          <CardTitle>
            {selectedType === 'all'
              ? 'All Systems'
              : SYSTEM_TYPE_LABELS[selectedType]}
          </CardTitle>
          <CardDescription>
            {selectedType === 'all'
              ? 'Manage all systems in the directory'
              : `Manage ${SYSTEM_TYPE_LABELS[selectedType].toLowerCase()} systems`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <SystemsTable
            systems={systemsResponse?.systems ?? []}
            isLoading={isLoading}
            onDelete={setSystemToDelete}
            emptyMessage={
              selectedType === 'all'
                ? 'No systems found'
                : `No ${SYSTEM_TYPE_LABELS[selectedType].toLowerCase()} found`
            }
          />
        </CardContent>
      </Card>

      {/* Create Dialog */}
      <CreateSystemDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        defaultType={selectedType === 'all' ? 'server' : selectedType}
      />

      {/* Delete Confirmation */}
      <DeleteDialog
        open={!!systemToDelete}
        onOpenChange={(open) => !open && setSystemToDelete(null)}
        itemName={systemToDelete?.cn ?? ''}
        itemType="system"
        description={`Are you sure you want to delete the system "${systemToDelete?.cn}"? This will remove it from the directory. This action cannot be undone.`}
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
      />
    </div>
  )
}
