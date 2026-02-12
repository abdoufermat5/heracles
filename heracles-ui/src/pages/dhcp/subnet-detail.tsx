/**
 * DHCP Subnet Detail Page
 *
 * Displays detailed information about a specific DHCP subnet,
 * including pools and configuration options.
 */

import { useState } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import {
  ArrowLeft,
  Save,
  Trash2,
  Loader2,
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
  useDhcpSubnet,
  useUpdateDhcpSubnet,
  useDeleteDhcpSubnet,
} from '@/hooks/use-dhcp'
import { AppError } from '@/lib/errors'
import { dhcpServicePath } from '@/config/routes'

export function DhcpSubnetDetailPage() {
  const { serviceCn, subnetCn } = useParams<{ serviceCn: string; subnetCn: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  
  const dn = searchParams.get('dn') || ''
  
  const [isEditing, setIsEditing] = useState(false)
  const [formData, setFormData] = useState({
    netmask: 24,
    range: '',
    statements: '',
    options: '',
    comments: '',
  })

  const { data: subnet, isLoading } = useDhcpSubnet(
    serviceCn || '',
    subnetCn || '',
    dn,
    { enabled: !!serviceCn && !!subnetCn && !!dn }
  )
  
  const updateMutation = useUpdateDhcpSubnet(serviceCn || '')
  const deleteMutation = useDeleteDhcpSubnet(serviceCn || '')

  const handleStartEdit = () => {
    setFormData({
      netmask: subnet?.dhcpNetMask ?? 24,
      range: subnet?.dhcpRange?.join('\n') || '',
      statements: subnet?.dhcpStatements?.join('\n') || '',
      options: subnet?.dhcpOption?.join('\n') || '',
      comments: subnet?.dhcpComments || '',
    })
    setIsEditing(true)
  }

  const handleSave = async () => {
    if (!serviceCn || !subnetCn || !dn) return

    try {
      await updateMutation.mutateAsync({
        subnetCn,
        dn,
        data: {
          dhcpNetMask: formData.netmask,
          dhcpRange: formData.range.split('\n').filter(Boolean),
          dhcpStatements: formData.statements.split('\n').filter(Boolean),
          dhcpOptions: formData.options.split('\n').filter(Boolean),
          comments: formData.comments || undefined,
        },
      })
      toast.success('Subnet updated successfully')
      setIsEditing(false)
    } catch (error) {
      AppError.toastError(error, 'Failed to update subnet')
    }
  }

  const handleDelete = async () => {
    if (!serviceCn || !subnetCn || !dn) return

    try {
      await deleteMutation.mutateAsync({
        subnetCn,
        dn,
        recursive: true,
      })
      toast.success('Subnet deleted successfully')
      navigate(dhcpServicePath(serviceCn))
    } catch (error) {
      AppError.toastError(error, 'Failed to delete subnet')
    }
  }

  if (!serviceCn || !subnetCn) {
    return (
      <div className="container py-6">
        <p>Subnet not found</p>
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

  return (
    <div className="container py-6 space-y-6">
      <PageHeader
        title={`${subnetCn}/${subnet?.dhcpNetMask || 24}`}
        description={subnet?.dhcpComments || 'DHCP Subnet Configuration'}
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
                <Button onClick={handleStartEdit}>Edit</Button>
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button variant="destructive">
                      <Trash2 className="h-4 w-4 mr-2" />
                      Delete
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Delete Subnet</AlertDialogTitle>
                      <AlertDialogDescription>
                        Are you sure you want to delete subnet "{subnetCn}"? 
                        This will also delete all pools and hosts within this subnet.
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
            <CardTitle>Network Configuration</CardTitle>
            <CardDescription>
              Basic subnet configuration
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Network Address</Label>
              <Input value={subnetCn} disabled />
            </div>
            <div className="space-y-2">
              <Label>Netmask (CIDR)</Label>
              {isEditing ? (
                <Input
                  type="number"
                  min={1}
                  max={32}
                  value={formData.netmask}
                  onChange={(e) => setFormData({ ...formData, netmask: parseInt(e.target.value) || 24 })}
                />
              ) : (
                <p className="font-mono">/{subnet?.dhcpNetMask || 24}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label>Comments</Label>
              {isEditing ? (
                <Textarea
                  value={formData.comments}
                  onChange={(e) => setFormData({ ...formData, comments: e.target.value })}
                  placeholder="Description of this subnet"
                />
              ) : (
                <p className="text-muted-foreground">
                  {subnet?.dhcpComments || 'No description'}
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* IP Ranges */}
        <Card>
          <CardHeader>
            <CardTitle>IP Ranges</CardTitle>
            <CardDescription>
              Dynamic IP address ranges for this subnet
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isEditing ? (
              <Textarea
                value={formData.range}
                onChange={(e) => setFormData({ ...formData, range: e.target.value })}
                placeholder="192.168.1.100 192.168.1.200&#10;One range per line"
                rows={4}
              />
            ) : subnet?.dhcpRange && subnet.dhcpRange.length > 0 ? (
              <div className="space-y-2">
                {subnet.dhcpRange.map((range, i) => (
                  <Badge key={i} variant="secondary" className="font-mono">
                    {range}
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground text-sm">No ranges configured</p>
            )}
          </CardContent>
        </Card>

        {/* Statements */}
        <Card>
          <CardHeader>
            <CardTitle>DHCP Statements</CardTitle>
            <CardDescription>
              ISC DHCP server statements for this subnet
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isEditing ? (
              <Textarea
                value={formData.statements}
                onChange={(e) => setFormData({ ...formData, statements: e.target.value })}
                placeholder="default-lease-time 600&#10;max-lease-time 7200&#10;One statement per line"
                rows={4}
              />
            ) : subnet?.dhcpStatements && subnet.dhcpStatements.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {subnet.dhcpStatements.map((stmt, i) => (
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
        <Card>
          <CardHeader>
            <CardTitle>DHCP Options</CardTitle>
            <CardDescription>
              Options sent to clients in this subnet
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isEditing ? (
              <Textarea
                value={formData.options}
                onChange={(e) => setFormData({ ...formData, options: e.target.value })}
                placeholder="routers 192.168.1.1&#10;domain-name-servers 8.8.8.8&#10;One option per line"
                rows={4}
              />
            ) : subnet?.dhcpOption && subnet.dhcpOption.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {subnet.dhcpOption.map((opt, i) => (
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
          <div className="space-y-2">
            <Label className="text-muted-foreground">Distinguished Name (DN)</Label>
            <code className="block text-sm bg-muted p-2 rounded font-mono break-all">
              {subnet?.dn || dn}
            </code>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
