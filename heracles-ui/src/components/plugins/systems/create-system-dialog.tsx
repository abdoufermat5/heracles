/**
 * Create System Dialog
 *
 * Dialog for creating a new system with type-specific fields
 */

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
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

import { useCreateSystem } from '@/hooks/use-systems'
import {
  SYSTEM_TYPES,
  SYSTEM_TYPE_LABELS,
  LOCK_MODES,
  LOCK_MODE_LABELS,
  MOBILE_OS_OPTIONS,
  type SystemType,
} from '@/types/systems'
import { useDepartmentStore } from '@/stores'

// Hostname validation regex (RFC 1123)
const hostnameRegex =
  /^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/

// IP address validation (simplified)
const ipAddressRegex =
  /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/

// MAC address validation
const macAddressRegex = /^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$/

// IMEI validation (15 digits)
const imeiRegex = /^[0-9]{15}$/

// Form schema
const createSystemSchema = z
  .object({
    cn: z
      .string()
      .min(1, 'Hostname is required')
      .max(255, 'Hostname must be at most 255 characters')
      .regex(hostnameRegex, 'Invalid hostname format'),
    system_type: z.enum(SYSTEM_TYPES),
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
  .refine(
    (data) => {
      // Validate IP addresses if provided
      if (data.ip_addresses) {
        const ips = data.ip_addresses.split(/[,\s]+/).filter(Boolean)
        return ips.every((ip) => ipAddressRegex.test(ip.trim()))
      }
      return true
    },
    { message: 'Invalid IP address format', path: ['ip_addresses'] }
  )
  .refine(
    (data) => {
      // Validate MAC addresses if provided
      if (data.mac_addresses) {
        const macs = data.mac_addresses.split(/[,\s]+/).filter(Boolean)
        return macs.every((mac) => macAddressRegex.test(mac.trim()))
      }
      return true
    },
    { message: 'Invalid MAC address format (use XX:XX:XX:XX:XX:XX)', path: ['mac_addresses'] }
  )

type CreateSystemFormData = z.infer<typeof createSystemSchema>

interface CreateSystemDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  defaultType?: SystemType
}

export function CreateSystemDialog({
  open,
  onOpenChange,
  defaultType = 'server',
}: CreateSystemDialogProps) {
  const createMutation = useCreateSystem()
  const { currentBase } = useDepartmentStore()

  const form = useForm<CreateSystemFormData>({
    resolver: zodResolver(createSystemSchema),
    defaultValues: {
      cn: '',
      system_type: defaultType,
      description: '',
      ip_addresses: '',
      mac_addresses: '',
      mode: 'unlocked',
      location: '',
      labeled_uri: '',
      windows_inf_file: '',
      windows_driver_dir: '',
      windows_driver_name: '',
      telephone_number: '',
      serial_number: '',
      imei: '',
      operating_system: '',
      puk: '',
      owner: '',
    },
  })

  const handleCreate = async (data: CreateSystemFormData) => {
    try {
      // Parse arrays from comma-separated strings
      const ipAddresses = data.ip_addresses
        ? data.ip_addresses.split(/[,\s]+/).filter(Boolean)
        : undefined
      const macAddresses = data.mac_addresses
        ? data.mac_addresses.split(/[,\s]+/).filter(Boolean)
        : undefined

      await createMutation.mutateAsync({
        data: {
          cn: data.cn,
          system_type: data.system_type,
          description: data.description || undefined,
          ip_addresses: ipAddresses,
          mac_addresses: macAddresses,
          mode: data.mode,
          location: data.location || undefined,
          // Printer specific
          labeled_uri: data.labeled_uri || undefined,
          windows_inf_file: data.windows_inf_file || undefined,
          windows_driver_dir: data.windows_driver_dir || undefined,
          windows_driver_name: data.windows_driver_name || undefined,
          // Phone specific
          telephone_number: data.telephone_number || undefined,
          serial_number: data.serial_number || undefined,
          // Mobile specific
          imei: data.imei || undefined,
          operating_system: data.operating_system || undefined,
          puk: data.puk || undefined,
          // Component specific
          owner: data.owner || undefined,
        },
        baseDn: currentBase || undefined,
      })
      toast.success(`System "${data.cn}" created successfully`)
      onOpenChange(false)
      form.reset()
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to create system'
      )
    }
  }

  const handleClose = () => {
    onOpenChange(false)
    form.reset()
  }

  const watchedType = form.watch('system_type')

  // Show printer fields
  const showPrinterFields = watchedType === 'printer'
  // Show phone/mobile fields
  const showPhoneFields = watchedType === 'phone' || watchedType === 'mobile'
  // Show mobile-only fields
  const showMobileFields = watchedType === 'mobile'
  // Show component fields
  const showComponentFields = watchedType === 'component'

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create System</DialogTitle>
          <DialogDescription>
            Add a new system to the directory
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(handleCreate)}
            className="space-y-6"
          >
            {/* Basic Info */}
            <div className="space-y-4">
              <h4 className="font-medium text-sm border-b pb-2">
                Basic Information
              </h4>
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="system_type"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>System Type *</FormLabel>
                      <Select
                        onValueChange={field.onChange}
                        defaultValue={field.value}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select type" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {SYSTEM_TYPES.map((type) => (
                            <SelectItem key={type} value={type}>
                              {SYSTEM_TYPE_LABELS[type]}
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
                  name="cn"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Hostname *</FormLabel>
                      <FormControl>
                        <Input placeholder="server01.example.com" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
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
            </div>

            {/* Network Info */}
            <div className="space-y-4">
              <h4 className="font-medium text-sm border-b pb-2">
                Network Information
              </h4>
              <div className="grid grid-cols-2 gap-4">
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
                        Comma-separated list of IP addresses
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
                        <Input placeholder="00:11:22:33:44:55" {...field} />
                      </FormControl>
                      <FormDescription>
                        Comma-separated list of MAC addresses
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>

            {/* Status & Location */}
            <div className="space-y-4">
              <h4 className="font-medium text-sm border-b pb-2">
                Status & Location
              </h4>
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="mode"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Status</FormLabel>
                      <Select
                        onValueChange={field.onChange}
                        defaultValue={field.value}
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
                        <Input
                          placeholder="Datacenter A, Rack 12"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>

            {/* Printer-specific fields */}
            {showPrinterFields && (
              <div className="space-y-4">
                <h4 className="font-medium text-sm border-b pb-2">
                  Printer Configuration
                </h4>
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
                <div className="grid grid-cols-3 gap-4">
                  <FormField
                    control={form.control}
                    name="windows_inf_file"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Windows INF File</FormLabel>
                        <FormControl>
                          <Input placeholder="/path/to/driver.inf" {...field} />
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
                          <Input placeholder="/share/drivers/hp" {...field} />
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
                          <Input placeholder="HP LaserJet Pro" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              </div>
            )}

            {/* Phone-specific fields */}
            {showPhoneFields && (
              <div className="space-y-4">
                <h4 className="font-medium text-sm border-b pb-2">
                  Phone Information
                </h4>
                <div className="grid grid-cols-2 gap-4">
                  <FormField
                    control={form.control}
                    name="telephone_number"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Phone Number / Extension</FormLabel>
                        <FormControl>
                          <Input placeholder="+1-555-123-4567" {...field} />
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
              </div>
            )}

            {/* Mobile-specific fields */}
            {showMobileFields && (
              <div className="space-y-4">
                <h4 className="font-medium text-sm border-b pb-2">
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
                          <Input placeholder="123456789012345" {...field} />
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
                          defaultValue={field.value}
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
                          <Input type="password" placeholder="••••••••" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              </div>
            )}

            {/* Component-specific fields */}
            {showComponentFields && (
              <div className="space-y-4">
                <h4 className="font-medium text-sm border-b pb-2">
                  Component Information
                </h4>
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
                          <Input placeholder="uid=admin,ou=users,..." {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              </div>
            )}

            <DialogFooter>
              <Button type="button" variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? 'Creating...' : 'Create System'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
