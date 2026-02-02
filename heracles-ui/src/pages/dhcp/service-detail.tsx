/**
 * DHCP Service Detail Page
 *
 * Displays detailed information about a specific DHCP service,
 * including subnets, hosts, and configuration.
 */

import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Network,
  ArrowLeft,
  Plus,
  RefreshCw,
  Blocks,
  Monitor,
  TreePine,
  Settings,
} from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { PageHeader } from '@/components/common/page-header'
import {
  DhcpSubnetsTable,
  DhcpHostsTable,
  DhcpTreeView,
  CreateDhcpSubnetDialog,
  CreateDhcpHostDialog,
} from '@/components/plugins/dhcp'
import {
  useDhcpService,
  useDhcpSubnets,
  useDhcpHosts,
  useDhcpServiceTree,
  useCreateDhcpSubnet,
  useCreateDhcpHost,
  useDeleteDhcpSubnet,
  useDeleteDhcpHost,
} from '@/hooks/use-dhcp'
import { AppError } from '@/lib/errors'
import { PLUGIN_ROUTES } from '@/config/routes'
import { useDepartmentStore } from '@/stores'
import type { DhcpSubnetListItem, DhcpHostListItem } from '@/types/dhcp'

export function DhcpServiceDetailPage() {
  const { serviceCn } = useParams<{ serviceCn: string }>()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('overview')
  const [createSubnetOpen, setCreateSubnetOpen] = useState(false)
  const [createHostOpen, setCreateHostOpen] = useState(false)
  const { currentBase } = useDepartmentStore()

  // Use actual hooks for API calls
  const { data: service, isLoading: serviceLoading } = useDhcpService(serviceCn || '')
  const { data: subnetsData, isLoading: subnetsLoading } = useDhcpSubnets(serviceCn || '')
  const { data: hostsData, isLoading: hostsLoading } = useDhcpHosts(serviceCn || '')
  const { data: treeData, isLoading: treeLoading } = useDhcpServiceTree(serviceCn || '')

  const createSubnetMutation = useCreateDhcpSubnet(serviceCn || '')
  const createHostMutation = useCreateDhcpHost(serviceCn || '')
  const deleteSubnetMutation = useDeleteDhcpSubnet(serviceCn || '')
  const deleteHostMutation = useDeleteDhcpHost(serviceCn || '')

  const handleCreateSubnet = async (data: any) => {
    try {
      await createSubnetMutation.mutateAsync({
        data: {
          cn: data.cn,
          dhcpNetMask: data.netmask,
          dhcpStatements: data.statements,
          dhcpOptions: data.options,
          comments: data.comments,
        },
        baseDn: currentBase || undefined,
      })
      toast.success(`Subnet ${data.cn} created successfully`)
      setCreateSubnetOpen(false)
    } catch (error) {
      AppError.toastError(error, 'Failed to create subnet')
    }
  }

  const handleCreateHost = async (data: any) => {
    try {
      await createHostMutation.mutateAsync({
        data: {
          cn: data.cn,
          dhcpHWAddress: data.hwAddress,
          fixedAddress: data.fixedAddress,
          dhcpStatements: data.statements,
          dhcpOptions: data.options,
          comments: data.comments,
        },
        parentDn: data.parentDn,
        baseDn: currentBase || undefined,
      })
      toast.success(`Host ${data.cn} created successfully`)
      setCreateHostOpen(false)
    } catch (error) {
      AppError.toastError(error, 'Failed to create host')
    }
  }

  const handleDeleteSubnet = async (subnet: DhcpSubnetListItem) => {
    if (!confirm(`Are you sure you want to delete subnet ${subnet.cn}?`)) return
    try {
      await deleteSubnetMutation.mutateAsync({
        subnetCn: subnet.cn,
        dn: subnet.dn,
      })
      toast.success(`Subnet ${subnet.cn} deleted successfully`)
    } catch (error) {
      AppError.toastError(error, 'Failed to delete subnet')
    }
  }

  const handleDeleteHost = async (host: DhcpHostListItem) => {
    if (!confirm(`Are you sure you want to delete host ${host.cn}?`)) return
    try {
      await deleteHostMutation.mutateAsync({
        hostCn: host.cn,
        dn: host.dn,
      })
      toast.success(`Host ${host.cn} deleted successfully`)
    } catch (error) {
      AppError.toastError(error, 'Failed to delete host')
    }
  }

  if (!serviceCn) {
    return (
      <div className="container py-6">
        <p>Service not found</p>
      </div>
    )
  }

  const statements = service?.dhcpStatements ?? []
  const options = service?.dhcpOption ?? []
  const subnets = subnetsData?.items ?? []
  const hosts = hostsData?.items ?? []
  const tree = treeData?.service ?? null

  return (
    <div className="container py-6 space-y-6">
      <PageHeader
        title={serviceCn}
        description={service?.dhcpComments || 'DHCP Service Configuration'}
        icon={<Network className="h-8 w-8" />}
        actions={
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => navigate(PLUGIN_ROUTES.DHCP.SERVICES)}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Services
            </Button>
          </div>
        }
      />

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="subnets" className="flex items-center gap-2">
            <Blocks className="h-4 w-4" />
            Subnets
          </TabsTrigger>
          <TabsTrigger value="hosts" className="flex items-center gap-2">
            <Monitor className="h-4 w-4" />
            Hosts
          </TabsTrigger>
          <TabsTrigger value="tree" className="flex items-center gap-2">
            <TreePine className="h-4 w-4" />
            Tree View
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            {/* Service Info */}
            <Card>
              <CardHeader>
                <CardTitle>Service Information</CardTitle>
                <CardDescription>
                  Basic configuration for this DHCP service
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Service Name
                  </label>
                  <p className="font-mono">{serviceCn}</p>
                </div>
                {service?.dhcpComments && (
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      Description
                    </label>
                    <p>{service.dhcpComments}</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Statements */}
            <Card>
              <CardHeader>
                <CardTitle>Global Statements</CardTitle>
                <CardDescription>
                  ISC DHCP server statements applied globally
                </CardDescription>
              </CardHeader>
              <CardContent>
                {statements.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {statements.map((stmt, i) => (
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
                <CardTitle>Global Options</CardTitle>
                <CardDescription>
                  DHCP options sent to all clients
                </CardDescription>
              </CardHeader>
              <CardContent>
                {options.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {options.map((opt, i) => (
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
        </TabsContent>

        <TabsContent value="subnets" className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={() => setCreateSubnetOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Subnet
            </Button>
          </div>
          <DhcpSubnetsTable
            serviceCn={serviceCn}
            subnets={subnets}
            isLoading={subnetsLoading}
            onDelete={handleDeleteSubnet}
            emptyMessage="No subnets configured. Add a subnet to define IP ranges."
          />
        </TabsContent>

        <TabsContent value="hosts" className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={() => setCreateHostOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Host
            </Button>
          </div>
          <DhcpHostsTable
            serviceCn={serviceCn}
            hosts={hosts}
            isLoading={hostsLoading}
            onDelete={handleDeleteHost}
            emptyMessage="No host reservations. Add a host to assign a fixed IP to a MAC address."
          />
        </TabsContent>

        <TabsContent value="tree" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Configuration Hierarchy</CardTitle>
              <CardDescription>
                Visual representation of the DHCP configuration structure
              </CardDescription>
            </CardHeader>
            <CardContent>
              <DhcpTreeView
                tree={tree}
                isLoading={treeLoading}
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <CreateDhcpSubnetDialog
        open={createSubnetOpen}
        onOpenChange={setCreateSubnetOpen}
        serviceCn={serviceCn}
        onSubmit={handleCreateSubnet}
      />

      <CreateDhcpHostDialog
        open={createHostOpen}
        onOpenChange={setCreateHostOpen}
        serviceCn={serviceCn}
        onSubmit={handleCreateHost}
      />
    </div>
  )
}
