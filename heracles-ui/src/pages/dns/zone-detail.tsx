/**
 * DNS Zone Detail Page
 *
 * Shows zone details, SOA record, and all records with management capabilities.
 */

import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  Globe,
  ArrowLeft,
  Plus,
  RefreshCw,
  Settings,
  Trash2,
  Clock,
  Server,
  Mail,
  Pencil,
} from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
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
import { Skeleton } from '@/components/ui/skeleton'
import { PageHeader } from '@/components/common/page-header'
import { DnsRecordsTable, CreateRecordDialog, EditSoaDialog } from '@/components/plugins/dns'
import {
  useDnsZone,
  useDnsRecords,
  useDeleteDnsZone,
  useDeleteDnsRecord,
} from '@/hooks/use-dns'
import type { DnsRecord } from '@/types/dns'
import { ZONE_TYPE_LABELS } from '@/types/dns'
import { useDepartmentStore } from '@/stores'

export function DnsZoneDetailPage() {
  const { zoneName } = useParams<{ zoneName: string }>()
  const navigate = useNavigate()

  const [createRecordOpen, setCreateRecordOpen] = useState(false)
  const [editSoaOpen, setEditSoaOpen] = useState(false)
  const [deleteZoneOpen, setDeleteZoneOpen] = useState(false)
  const [recordToDelete, setRecordToDelete] = useState<DnsRecord | null>(null)
  const { currentBase } = useDepartmentStore()

  const decodedZoneName = zoneName ? decodeURIComponent(zoneName) : ''

  const {
    data: zone,
    isLoading: zoneLoading,
    refetch: refetchZone,
  } = useDnsZone(decodedZoneName, { enabled: !!decodedZoneName })

  const {
    data: records,
    isLoading: recordsLoading,
    refetch: refetchRecords,
    isRefetching,
  } = useDnsRecords(decodedZoneName, { enabled: !!decodedZoneName })

  const deleteZoneMutation = useDeleteDnsZone()
  const deleteRecordMutation = useDeleteDnsRecord(decodedZoneName)

  const handleDeleteZone = async () => {
    try {
      await deleteZoneMutation.mutateAsync({ zoneName: decodedZoneName, baseDn: currentBase || undefined })
      toast.success(`Zone "${decodedZoneName}" deleted successfully`)
      navigate('/dns')
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to delete zone'
      )
    }
  }

  const handleDeleteRecord = async () => {
    if (!recordToDelete) return

    try {
      await deleteRecordMutation.mutateAsync({
        name: recordToDelete.name,
        recordType: recordToDelete.recordType,
        value: recordToDelete.value,
      })
      toast.success('Record deleted successfully')
      setRecordToDelete(null)
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to delete record'
      )
    }
  }

  const handleRefresh = () => {
    refetchZone()
    refetchRecords()
  }

  if (zoneLoading) {
    return (
      <div className="container py-6 space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10 rounded-lg" />
          <div className="space-y-2">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-32" />
          </div>
        </div>
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  if (!zone) {
    return (
      <div className="container py-6">
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Globe className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium">Zone not found</h3>
            <p className="text-muted-foreground mb-4">
              The zone "{decodedZoneName}" does not exist.
            </p>
            <Button asChild>
              <Link to="/dns">Back to Zones</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container py-6 space-y-6">
      <PageHeader
        title={zone.zoneName}
        description={`${ZONE_TYPE_LABELS[zone.zoneType]} DNS zone`}
        icon={<Globe className="h-8 w-8" />}
        breadcrumbs={[
          { label: 'DNS', href: '/dns' },
          { label: zone.zoneName },
        ]}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" size="icon" asChild>
              <Link to="/dns">
                <ArrowLeft className="h-4 w-4" />
                <span className="sr-only">Back to zones</span>
              </Link>
            </Button>
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
            <Button
              variant="outline"
              size="icon"
              className="text-destructive hover:text-destructive"
              onClick={() => setDeleteZoneOpen(true)}
            >
              <Trash2 className="h-4 w-4" />
              <span className="sr-only">Delete zone</span>
            </Button>
            <Button onClick={() => setCreateRecordOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Record
            </Button>
          </div>
        }
      />

      {/* Zone Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Zone Type</CardTitle>
            <Globe className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <Badge variant="outline">{ZONE_TYPE_LABELS[zone.zoneType]}</Badge>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Primary NS</CardTitle>
            <Server className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <code className="text-sm font-mono">{zone.soa.primaryNs}</code>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Admin Email</CardTitle>
            <Mail className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <code className="text-sm font-mono">{zone.soa.adminEmail}</code>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Default TTL</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <span className="text-2xl font-bold tabular-nums">
              {zone.defaultTtl}
            </span>
            <span className="text-muted-foreground ml-1">seconds</span>
          </CardContent>
        </Card>
      </div>

      {/* SOA Details */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              SOA Record
            </CardTitle>
            <CardDescription>
              Start of Authority record configuration
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setEditSoaOpen(true)}
          >
            <Pencil className="h-4 w-4 mr-2" />
            Edit SOA
          </Button>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Serial</span>
              <p className="font-mono font-medium">{zone.soa.serial}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Refresh</span>
              <p className="font-mono">{zone.soa.refresh}s</p>
            </div>
            <div>
              <span className="text-muted-foreground">Retry</span>
              <p className="font-mono">{zone.soa.retry}s</p>
            </div>
            <div>
              <span className="text-muted-foreground">Expire</span>
              <p className="font-mono">{zone.soa.expire}s</p>
            </div>
            <div>
              <span className="text-muted-foreground">Minimum</span>
              <p className="font-mono">{zone.soa.minimum}s</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Records */}
      <Card>
        <CardHeader>
          <CardTitle>Records</CardTitle>
          <CardDescription>
            {zone.recordCount} record{zone.recordCount !== 1 ? 's' : ''} in this
            zone
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DnsRecordsTable
            records={records ?? []}
            isLoading={recordsLoading}
            onDelete={setRecordToDelete}
          />
        </CardContent>
      </Card>

      {/* Create Record Dialog */}
      <CreateRecordDialog
        open={createRecordOpen}
        onOpenChange={setCreateRecordOpen}
        zoneName={decodedZoneName}
      />

      {/* Edit SOA Dialog */}
      <EditSoaDialog
        open={editSoaOpen}
        onOpenChange={setEditSoaOpen}
        zone={zone}
      />

      {/* Delete Zone Confirmation */}
      <AlertDialog open={deleteZoneOpen} onOpenChange={setDeleteZoneOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete DNS Zone</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the zone{' '}
              <code className="font-mono font-medium">{zone.zoneName}</code>?
              This will also delete all {zone.recordCount} records within the
              zone. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteZone}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteZoneMutation.isPending ? 'Deleting...' : 'Delete Zone'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete Record Confirmation */}
      <AlertDialog
        open={!!recordToDelete}
        onOpenChange={(open) => !open && setRecordToDelete(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete DNS Record</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this {recordToDelete?.recordType}{' '}
              record for{' '}
              <code className="font-mono font-medium">
                {recordToDelete?.name}
              </code>
              ?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteRecord}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteRecordMutation.isPending ? 'Deleting...' : 'Delete Record'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
