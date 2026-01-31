/**
 * System Detail Page
 *
 * View and edit a single system's details.
 */

import { useParams, useNavigate, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import {
  ArrowLeft,
  Save,
  Trash2,
  Server,
  Monitor,
  MonitorSmartphone,
  Printer,
  Cpu,
  Phone,
  Smartphone,
  Network,
  MapPin,
  Info,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

import { DeleteDialog } from '@/components/common'
import { useSystem, useUpdateSystem, useDeleteSystem } from '@/hooks/use-systems'
import {
  SYSTEM_TYPE_LABELS,
  LOCK_MODES,
  LOCK_MODE_LABELS,
  MOBILE_OS_OPTIONS,
  type SystemType,
  type LockMode,
} from '@/types/systems'
import { PLUGIN_ROUTES } from '@/config/routes'
import { useState } from 'react'
import { useDepartmentStore } from '@/stores'

// Icon mapping
const SystemTypeIcon: Record<SystemType, React.ElementType> = {
  server: Server,
  workstation: Monitor,
  terminal: MonitorSmartphone,
  printer: Printer,
  component: Cpu,
  phone: Phone,
  mobile: Smartphone,
}

// Mode badge variants
const modeBadgeVariant: Record<
  LockMode,
  'default' | 'secondary' | 'destructive' | 'outline'
> = {
  unlocked: 'default',
  locked: 'destructive',
}

// IMEI validation (15 digits)
const imeiRegex = /^[0-9]{15}$/

// Update form schema
const updateSystemSchema = z.object({
  description: z.string().max(1024).optional(),
  ip_addresses: z.string().optional(),
  mac_addresses: z.string().optional(),
  mode: z.enum(LOCK_MODES).optional(),
  location: z.string().max(128).optional(),
  // Printer specific
  labeled_uri: z.string().max(1024).optional(),
  windows_inf_file: z.string().max(512).optional(),
  windows_driver_dir: z.string().max(512).optional(),
  windows_driver_name: z.string().max(256).optional(),
  // Phone specific
  telephone_number: z.string().max(32).optional(),
  serial_number: z.string().max(128).optional(),
  // Mobile specific
  imei: z
    .string()
    .optional()
    .refine((val) => !val || imeiRegex.test(val), 'IMEI must be 15 digits'),
  operating_system: z.string().optional(),
  puk: z.string().max(16).optional(),
  // Component specific
  owner: z.string().max(256).optional(),
})

type UpdateSystemFormData = z.infer<typeof updateSystemSchema>

export function SystemDetailPage() {
  const { type, cn } = useParams<{ type: string; cn: string }>()
  const navigate = useNavigate()
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)

  const systemType = type as SystemType
  const { currentBase } = useDepartmentStore()

  const {
    data: system,
    isLoading,
    error,
  } = useSystem(systemType, cn ?? '', {
    enabled: !!type && !!cn,
    baseDn: currentBase || undefined,
  })

  const updateMutation = useUpdateSystem()
  const deleteMutation = useDeleteSystem()

  const form = useForm<UpdateSystemFormData>({
    resolver: zodResolver(updateSystemSchema),
    values: system
      ? {
        description: system.description ?? '',
        ip_addresses: system.ipHostNumber?.join(', ') ?? '',
        mac_addresses: system.macAddress?.join(', ') ?? '',
        mode: system.hrcMode,
        location: system.l ?? '',
        labeled_uri: system.labeledURI ?? '',
        windows_inf_file: system.hrcPrinterWindowsInfFile ?? '',
        windows_driver_dir: system.hrcPrinterWindowsDriverDir ?? '',
        windows_driver_name: system.hrcPrinterWindowsDriverName ?? '',
        telephone_number: system.telephoneNumber ?? '',
        serial_number: system.serialNumber ?? '',
        imei: system.hrcMobileIMEI ?? '',
        operating_system: system.hrcMobileOS ?? '',
        puk: system.hrcMobilePUK ?? '',
        owner: system.owner ?? '',
      }
      : undefined,
  })

  const handleUpdate = async (data: UpdateSystemFormData) => {
    if (!system) return

    try {
      // Parse arrays from comma-separated strings
      const ipAddresses = data.ip_addresses
        ? data.ip_addresses.split(/[,\s]+/).filter(Boolean)
        : undefined
      const macAddresses = data.mac_addresses
        ? data.mac_addresses.split(/[,\s]+/).filter(Boolean)
        : undefined

      await updateMutation.mutateAsync({
        systemType: system.systemType,
        cn: system.cn,
        data: {
          description: data.description || undefined,
          ip_addresses: ipAddresses,
          mac_addresses: macAddresses,
          mode: data.mode,
          location: data.location || undefined,
          labeled_uri: data.labeled_uri || undefined,
          windows_inf_file: data.windows_inf_file || undefined,
          windows_driver_dir: data.windows_driver_dir || undefined,
          windows_driver_name: data.windows_driver_name || undefined,
          telephone_number: data.telephone_number || undefined,
          serial_number: data.serial_number || undefined,
          imei: data.imei || undefined,
          operating_system: data.operating_system || undefined,
          puk: data.puk || undefined,
          owner: data.owner || undefined,
        },
        baseDn: currentBase || undefined,
      })
      toast.success('System updated successfully')
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to update system'
      )
    }
  }

  const handleDelete = async () => {
    if (!system) return

    try {
      await deleteMutation.mutateAsync({
        systemType: system.systemType,
        cn: system.cn,
        baseDn: currentBase || undefined,
      })
      toast.success(`System "${system.cn}" deleted successfully`)
      navigate(PLUGIN_ROUTES.SYSTEMS.LIST)
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to delete system'
      )
    }
  }

  if (isLoading) {
    return (
      <div className="container mx-auto py-6 space-y-6">
        <Skeleton className="h-8 w-64" />
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-4">
              {[1, 2, 3, 4].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error || !system) {
    return (
      <div className="container mx-auto py-6">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-8 text-destructive">
              <p>System not found</p>
              <Button variant="outline" className="mt-4" asChild>
                <Link to={PLUGIN_ROUTES.SYSTEMS.LIST}>
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Back to Systems
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  const Icon = SystemTypeIcon[system.systemType]
  const showPrinterFields = system.systemType === 'printer'
  const showPhoneFields =
    system.systemType === 'phone' || system.systemType === 'mobile'
  const showMobileFields = system.systemType === 'mobile'
  const showComponentFields = system.systemType === 'component'

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link to={PLUGIN_ROUTES.SYSTEMS.LIST}>
              <ArrowLeft className="h-5 w-5" />
            </Link>
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <Icon className="h-6 w-6" />
              <h1 className="text-2xl font-bold">{system.cn}</h1>
              {system.hrcMode && (
                <Badge variant={modeBadgeVariant[system.hrcMode]}>
                  {LOCK_MODE_LABELS[system.hrcMode]}
                </Badge>
              )}
            </div>
            <p className="text-muted-foreground">
              {SYSTEM_TYPE_LABELS[system.systemType]} • {system.dn}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setShowDeleteDialog(true)}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </Button>
        </div>
      </div>

      {/* Content */}
      <Form {...form}>
        <form onSubmit={form.handleSubmit(handleUpdate)}>
          <Tabs defaultValue="general" className="space-y-6">
            <TabsList>
              <TabsTrigger value="general">
                <Info className="h-4 w-4 mr-2" />
                General
              </TabsTrigger>
              <TabsTrigger value="network">
                <Network className="h-4 w-4 mr-2" />
                Network
              </TabsTrigger>
              {(showPrinterFields ||
                showPhoneFields ||
                showComponentFields) && (
                  <TabsTrigger value="specific">
                    <Icon className="h-4 w-4 mr-2" />
                    {SYSTEM_TYPE_LABELS[system.systemType]} Settings
                  </TabsTrigger>
                )}
            </TabsList>

            {/* General Tab */}
            <TabsContent value="general">
              <Card>
                <CardHeader>
                  <CardTitle>General Information</CardTitle>
                  <CardDescription>
                    Basic system information and status
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm font-medium">Hostname</label>
                      <p className="text-lg font-mono">{system.cn}</p>
                    </div>
                    <div>
                      <label className="text-sm font-medium">Type</label>
                      <p className="text-lg">
                        {SYSTEM_TYPE_LABELS[system.systemType]}
                      </p>
                    </div>
                  </div>

                  <Separator />

                  <FormField
                    control={form.control}
                    name="description"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Description</FormLabel>
                        <FormControl>
                          <Textarea
                            placeholder="Description of this system..."
                            className="resize-none"
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <div className="grid grid-cols-2 gap-4">
                    <FormField
                      control={form.control}
                      name="mode"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Status</FormLabel>
                          <Select
                            onValueChange={field.onChange}
                            value={field.value}
                          >
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue placeholder="Select status" />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              {LOCK_MODES.map((mode) => (
                                <SelectItem key={mode} value={mode}>
                                  {LOCK_MODE_LABELS[mode]}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="location"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Location</FormLabel>
                          <FormControl>
                            <div className="relative">
                              <MapPin className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                              <Input
                                className="pl-9"
                                placeholder="Datacenter A, Rack 12"
                                {...field}
                              />
                            </div>
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Network Tab */}
            <TabsContent value="network">
              <Card>
                <CardHeader>
                  <CardTitle>Network Configuration</CardTitle>
                  <CardDescription>
                    IP and MAC addresses for this system
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <FormField
                    control={form.control}
                    name="ip_addresses"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>IP Addresses</FormLabel>
                        <FormControl>
                          <Input
                            placeholder="192.168.1.10, 10.0.0.5"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          Comma-separated list of IPv4 or IPv6 addresses
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="mac_addresses"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>MAC Addresses</FormLabel>
                        <FormControl>
                          <Input
                            placeholder="00:11:22:33:44:55, AA:BB:CC:DD:EE:FF"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          Comma-separated list of MAC addresses (format:
                          XX:XX:XX:XX:XX:XX)
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </CardContent>
              </Card>
            </TabsContent>

            {/* Type-specific Tab */}
            {(showPrinterFields ||
              showPhoneFields ||
              showComponentFields) && (
                <TabsContent value="specific">
                  <Card>
                    <CardHeader>
                      <CardTitle>
                        {SYSTEM_TYPE_LABELS[system.systemType]} Settings
                      </CardTitle>
                      <CardDescription>
                        Type-specific configuration options
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {/* Printer Fields */}
                      {showPrinterFields && (
                        <>
                          <FormField
                            control={form.control}
                            name="labeled_uri"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Printer URI</FormLabel>
                                <FormControl>
                                  <Input
                                    placeholder="ipp://printer.example.com/printers/main"
                                    {...field}
                                  />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                          <Separator />
                          <h4 className="font-medium text-sm">Windows Driver</h4>
                          <div className="grid grid-cols-3 gap-4">
                            <FormField
                              control={form.control}
                              name="windows_inf_file"
                              render={({ field }) => (
                                <FormItem>
                                  <FormLabel>INF File</FormLabel>
                                  <FormControl>
                                    <Input
                                      placeholder="/path/to/driver.inf"
                                      {...field}
                                    />
                                  </FormControl>
                                  <FormMessage />
                                </FormItem>
                              )}
                            />
                            <FormField
                              control={form.control}
                              name="windows_driver_dir"
                              render={({ field }) => (
                                <FormItem>
                                  <FormLabel>Driver Directory</FormLabel>
                                  <FormControl>
                                    <Input
                                      placeholder="/share/drivers/hp"
                                      {...field}
                                    />
                                  </FormControl>
                                  <FormMessage />
                                </FormItem>
                              )}
                            />
                            <FormField
                              control={form.control}
                              name="windows_driver_name"
                              render={({ field }) => (
                                <FormItem>
                                  <FormLabel>Driver Name</FormLabel>
                                  <FormControl>
                                    <Input
                                      placeholder="HP LaserJet Pro"
                                      {...field}
                                    />
                                  </FormControl>
                                  <FormMessage />
                                </FormItem>
                              )}
                            />
                          </div>
                        </>
                      )}

                      {/* Phone Fields */}
                      {showPhoneFields && (
                        <div className="grid grid-cols-2 gap-4">
                          <FormField
                            control={form.control}
                            name="telephone_number"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Phone Number / Extension</FormLabel>
                                <FormControl>
                                  <Input
                                    placeholder="+1-555-123-4567"
                                    {...field}
                                  />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                          <FormField
                            control={form.control}
                            name="serial_number"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Serial Number</FormLabel>
                                <FormControl>
                                  <Input placeholder="FCH2345ABCD" {...field} />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                        </div>
                      )}

                      {/* Mobile-only Fields */}
                      {showMobileFields && (
                        <>
                          <Separator />
                          <h4 className="font-medium text-sm">
                            Mobile Device Information
                          </h4>
                          <div className="grid grid-cols-3 gap-4">
                            <FormField
                              control={form.control}
                              name="imei"
                              render={({ field }) => (
                                <FormItem>
                                  <FormLabel>IMEI</FormLabel>
                                  <FormControl>
                                    <Input
                                      placeholder="123456789012345"
                                      {...field}
                                    />
                                  </FormControl>
                                  <FormDescription>15 digits</FormDescription>
                                  <FormMessage />
                                </FormItem>
                              )}
                            />
                            <FormField
                              control={form.control}
                              name="operating_system"
                              render={({ field }) => (
                                <FormItem>
                                  <FormLabel>Operating System</FormLabel>
                                  <Select
                                    onValueChange={field.onChange}
                                    value={field.value}
                                  >
                                    <FormControl>
                                      <SelectTrigger>
                                        <SelectValue placeholder="Select OS" />
                                      </SelectTrigger>
                                    </FormControl>
                                    <SelectContent>
                                      {MOBILE_OS_OPTIONS.map((os) => (
                                        <SelectItem key={os.value} value={os.value}>
                                          {os.label}
                                        </SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                  <FormMessage />
                                </FormItem>
                              )}
                            />
                            <FormField
                              control={form.control}
                              name="puk"
                              render={({ field }) => (
                                <FormItem>
                                  <FormLabel>PUK Code</FormLabel>
                                  <FormControl>
                                    <Input
                                      type="password"
                                      placeholder="••••••••"
                                      {...field}
                                    />
                                  </FormControl>
                                  <FormMessage />
                                </FormItem>
                              )}
                            />
                          </div>
                        </>
                      )}

                      {/* Component Fields */}
                      {showComponentFields && (
                        <div className="grid grid-cols-2 gap-4">
                          <FormField
                            control={form.control}
                            name="serial_number"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Serial Number</FormLabel>
                                <FormControl>
                                  <Input placeholder="FCW2345L0AB" {...field} />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                          <FormField
                            control={form.control}
                            name="owner"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Owner</FormLabel>
                                <FormControl>
                                  <Input
                                    placeholder="uid=admin,ou=users,..."
                                    {...field}
                                  />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>
              )}
          </Tabs>

          {/* Save Button */}
          <div className="flex justify-end">
            <Button type="submit" disabled={updateMutation.isPending}>
              <Save className="h-4 w-4 mr-2" />
              {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        </form>
      </Form>

      {/* Delete Confirmation */}
      <DeleteDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        itemName={system.cn}
        itemType="system"
        description={`Are you sure you want to delete the system "${system.cn}"? This will remove it from the directory. This action cannot be undone.`}
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
      />
    </div>
  )
}
