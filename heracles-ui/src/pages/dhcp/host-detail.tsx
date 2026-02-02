/**
 * DHCP Host Detail Page
 *
 * Displays detailed information about a specific DHCP host reservation,
 * including MAC address, fixed IP, and configuration options.
 */

import { useState, useEffect } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import {
  ArrowLeft,
  Save,
  Trash2,
  Loader2,
  Network,
} from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { PageHeader } from '@/components/common/page-header'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import {
  useDhcpHost,
  useUpdateDhcpHost,
  useDeleteDhcpHost,
} from '@/hooks/use-dhcp'
import { AppError } from '@/lib/errors'
import { dhcpServicePath } from '@/config/routes'

/**
 * Format MAC address from dhcpHWAddress (e.g., "ethernet 00:11:22:33:44:55")
 */
function formatMacAddress(hwAddress?: string | null): string {
  if (!hwAddress) return ''
  const parts = hwAddress.split(' ')
  return parts.length > 1 ? parts[1] : hwAddress
}

/**
 * Build dhcpHWAddress from MAC (prepend "ethernet ")
 */
function buildHwAddress(mac: string): string {
  if (!mac) return ''
  return `ethernet ${mac.toLowerCase()}`
}

export function DhcpHostDetailPage() {
  const { serviceCn, hostCn } = useParams<{ serviceCn: string; hostCn: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  
  const dn = searchParams.get('dn') || ''
  
  const [isEditing, setIsEditing] = useState(false)
  const [formData, setFormData] = useState({
    macAddress: '',
    fixedAddress: '',
    statements: '',
    options: '',
    comments: '',
  })

  const { data: host, isLoading } = useDhcpHost(
    serviceCn || '',
    hostCn || '',
    dn,
    { enabled: !!serviceCn && !!hostCn && !!dn }
  )
  
  const updateMutation = useUpdateDhcpHost(serviceCn || '')
  const deleteMutation = useDeleteDhcpHost(serviceCn || '')

  // Initialize form when host data loads
  useEffect(() => {
    if (host && !isEditing) {
      setFormData({
        macAddress: formatMacAddress(host.dhcpHWAddress),
        fixedAddress: host.fixedAddress || '',
        statements: host.dhcpStatements?.filter(s => !s.startsWith('fixed-address ')).join('\n') || '',
        options: host.dhcpOption?.join('\n') || '',
        comments: host.dhcpComments || '',
      })
    }
  }, [host, isEditing])

  const handleSave = async () => {
    if (!serviceCn || !hostCn || !dn) return

    try {
      await updateMutation.mutateAsync({
        hostCn,
        dn,
        data: {
          dhcpHWAddress: formData.macAddress ? buildHwAddress(formData.macAddress) : undefined,
          fixedAddress: formData.fixedAddress || undefined,
          dhcpStatements: formData.statements.split('\n').filter(Boolean),
          dhcpOptions: formData.options.split('\n').filter(Boolean),
          comments: formData.comments || undefined,
        },
      })
      toast.success('Host updated successfully')
      setIsEditing(false)
    } catch (error) {
      AppError.toastError(error, 'Failed to update host')
    }
  }

  const handleDelete = async () => {
    if (!serviceCn || !hostCn || !dn) return

    try {
      await deleteMutation.mutateAsync({
        hostCn,
        dn,
      })
      toast.success('Host deleted successfully')
      navigate(dhcpServicePath(serviceCn))
    } catch (error) {
      AppError.toastError(error, 'Failed to delete host')
    }
  }

  if (!serviceCn || !hostCn) {
    return (
      <div className="container py-6">
        <p>Host not found</p>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="container py-6 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  const displayMac = formatMacAddress(host?.dhcpHWAddress)

  return (
    <div className="container py-6 space-y-6">
      <PageHeader
        title={hostCn}
        description={host?.dhcpComments || 'DHCP Host Reservation'}
        actions={
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => navigate(dhcpServicePath(serviceCn))}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Service
            </Button>
            {isEditing ? (
              <>
                <Button variant="outline" onClick={() => setIsEditing(false)}>
                  Cancel
                </Button>
                <Button onClick={handleSave} disabled={updateMutation.isPending}>
                  {updateMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                  <Save className="h-4 w-4 mr-2" />
                  Save Changes
                </Button>
              </>
            ) : (
              <>
                <Button onClick={() => setIsEditing(true)}>Edit</Button>
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button variant="destructive">
                      <Trash2 className="h-4 w-4 mr-2" />
                      Delete
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Delete Host</AlertDialogTitle>
                      <AlertDialogDescription>
                        Are you sure you want to delete host "{hostCn}"? 
                        This action cannot be undone.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={handleDelete}
                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                      >
                        {deleteMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                        Delete
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </>
            )}
          </div>
        }
      />

      <div className="grid gap-6 md:grid-cols-2">
        {/* Basic Info */}
        <Card>
          <CardHeader>
            <CardTitle>Host Information</CardTitle>
            <CardDescription>
              Basic host reservation settings
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Hostname</Label>
              <Input value={hostCn} disabled />
            </div>
            <div className="space-y-2">
              <Label>MAC Address</Label>
              {isEditing ? (
                <Input
                  value={formData.macAddress}
                  onChange={(e) => setFormData({ ...formData, macAddress: e.target.value })}
                  placeholder="00:11:22:33:44:55"
                  className="font-mono"
                />
              ) : (
                <p className="font-mono">{displayMac || 'Not configured'}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <Network className="h-4 w-4" />
                Fixed IP Address
              </Label>
              {isEditing ? (
                <Input
                  value={formData.fixedAddress}
                  onChange={(e) => setFormData({ ...formData, fixedAddress: e.target.value })}
                  placeholder="192.168.1.100"
                  className="font-mono"
                />
              ) : (
                <p className="font-mono">
                  {host?.fixedAddress || <span className="text-muted-foreground">Dynamic (no fixed IP)</span>}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label>Comments</Label>
              {isEditing ? (
                <Textarea
                  value={formData.comments}
                  onChange={(e) => setFormData({ ...formData, comments: e.target.value })}
                  placeholder="Description of this host"
                />
              ) : (
                <p className="text-muted-foreground">
                  {host?.dhcpComments || 'No description'}
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Statements */}
        <Card>
          <CardHeader>
            <CardTitle>DHCP Statements</CardTitle>
            <CardDescription>
              Additional ISC DHCP statements for this host
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isEditing ? (
              <Textarea
                value={formData.statements}
                onChange={(e) => setFormData({ ...formData, statements: e.target.value })}
                placeholder="filename &quot;pxelinux.0&quot;&#10;next-server 192.168.1.1&#10;One statement per line"
                rows={4}
              />
            ) : host?.dhcpStatements && host.dhcpStatements.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {host.dhcpStatements.map((stmt, i) => (
                  <Badge key={i} variant="secondary" className="font-mono text-xs">
                    {stmt}
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground text-sm">No statements configured</p>
            )}
          </CardContent>
        </Card>

        {/* Options */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>DHCP Options</CardTitle>
            <CardDescription>
              Options sent specifically to this host
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isEditing ? (
              <Textarea
                value={formData.options}
                onChange={(e) => setFormData({ ...formData, options: e.target.value })}
                placeholder="host-name &quot;myhost&quot;&#10;routers 192.168.1.1&#10;One option per line"
                rows={4}
              />
            ) : host?.dhcpOption && host.dhcpOption.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {host.dhcpOption.map((opt, i) => (
                  <Badge key={i} variant="outline" className="font-mono text-xs">
                    {opt}
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground text-sm">No options configured</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* DN Info */}
      <Card>
        <CardHeader>
          <CardTitle>LDAP Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label className="text-muted-foreground">Distinguished Name (DN)</Label>
              <code className="block text-sm bg-muted p-2 rounded font-mono break-all">
                {host?.dn || dn}
              </code>
            </div>
            {host?.parentDn && (
              <div className="space-y-2">
                <Label className="text-muted-foreground">Parent DN</Label>
                <code className="block text-sm bg-muted p-2 rounded font-mono break-all">
                  {host.parentDn}
                </code>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
