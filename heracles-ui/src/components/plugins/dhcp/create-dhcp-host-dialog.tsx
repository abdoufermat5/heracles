/**
 * Create DHCP Host Dialog
 *
 * Dialog for creating a new DHCP host reservation
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

// Hostname validation regex (RFC 1123)
const hostnameRegex =
  /^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/

// IP address validation
const ipAddressRegex =
  /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/

// MAC address validation (colon or hyphen separated)
const macAddressRegex = /^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$/

// Hardware types for DHCP
const HARDWARE_TYPES = [
  { value: 'ethernet', label: 'Ethernet' },
  { value: 'token-ring', label: 'Token Ring' },
  { value: 'fddi', label: 'FDDI' },
]

// Form schema
const createHostSchema = z
  .object({
    cn: z
      .string()
      .min(1, 'Hostname is required')
      .max(255, 'Hostname must be at most 255 characters')
      .regex(hostnameRegex, 'Invalid hostname format'),
    description: z.string().max(1024).optional(),
    hardware_type: z.string().default('ethernet'),
    mac_address: z
      .string()
      .optional()
      .refine(
        (val) => !val || macAddressRegex.test(val),
        'Invalid MAC address format (use XX:XX:XX:XX:XX:XX)'
      ),
    fixed_address: z
      .string()
      .optional()
      .refine(
        (val) => !val || ipAddressRegex.test(val),
        'Invalid IP address format'
      ),
    statements: z.string().optional(),
    options: z.string().optional(),
  })

type CreateHostFormData = z.infer<typeof createHostSchema>

interface CreateDhcpHostDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  serviceCn: string
  onSubmit: (data: {
    cn: string
    description?: string
    hw_address?: string
    statements?: string[]
    options?: string[]
  }) => Promise<void>
  isSubmitting?: boolean
}

export function CreateDhcpHostDialog({
  open,
  onOpenChange,
  serviceCn,
  onSubmit,
  isSubmitting = false,
}: CreateDhcpHostDialogProps) {
  const form = useForm<CreateHostFormData>({
    resolver: zodResolver(createHostSchema),
    defaultValues: {
      cn: '',
      description: '',
      hardware_type: 'ethernet',
      mac_address: '',
      fixed_address: '',
      statements: '',
      options: '',
    },
  })

  const handleSubmit = async (data: CreateHostFormData) => {
    try {
      // Build hardware address string
      const hw_address = data.mac_address
        ? `${data.hardware_type} ${data.mac_address}`
        : undefined

      // Build statements array, including fixed-address if provided
      let statementsArray = data.statements
        ? data.statements.split('\n').map((s) => s.trim()).filter(Boolean)
        : []
      
      if (data.fixed_address) {
        statementsArray = [`fixed-address ${data.fixed_address}`, ...statementsArray]
      }

      // Parse options
      const options = data.options
        ? data.options.split('\n').map((o) => o.trim()).filter(Boolean)
        : undefined

      await onSubmit({
        cn: data.cn,
        description: data.description || undefined,
        hw_address,
        statements: statementsArray.length > 0 ? statementsArray : undefined,
        options,
      })

      toast.success(`DHCP host "${data.cn}" created successfully`)
      form.reset()
      onOpenChange(false)
    } catch {
      toast.error('Failed to create DHCP host')
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create DHCP Host</DialogTitle>
          <DialogDescription>
            Add a new host reservation to the DHCP service "{serviceCn}".
            This allows assigning a fixed IP address based on MAC address.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
            {/* Hostname */}
            <FormField
              control={form.control}
              name="cn"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Hostname *</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="e.g., workstation1, server-db"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    A unique identifier for this host
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Description */}
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Optional description of this host"
                      className="resize-none"
                      rows={2}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Hardware Address */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Hardware Address</label>
              <div className="grid grid-cols-3 gap-4">
                <FormField
                  control={form.control}
                  name="hardware_type"
                  render={({ field }) => (
                    <FormItem>
                      <Select
                        onValueChange={field.onChange}
                        defaultValue={field.value}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Type" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {HARDWARE_TYPES.map((type) => (
                            <SelectItem key={type.value} value={type.value}>
                              {type.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <div className="col-span-2">
                  <FormField
                    control={form.control}
                    name="mac_address"
                    render={({ field }) => (
                      <FormItem>
                        <FormControl>
                          <Input
                            placeholder="00:11:22:33:44:55"
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                The client's MAC address for identification
              </p>
            </div>

            {/* Fixed IP Address */}
            <FormField
              control={form.control}
              name="fixed_address"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Fixed IP Address</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="e.g., 192.168.1.50"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    The IP address to assign to this host. Leave empty for dynamic assignment.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* DHCP Options */}
            <FormField
              control={form.control}
              name="options"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Host-Specific Options</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder={`One option per line, e.g.:\nhost-name "myhost"\nrouters 192.168.1.1`}
                      className="resize-none font-mono text-sm"
                      rows={3}
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    DHCP options specific to this host
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Additional Statements */}
            <FormField
              control={form.control}
              name="statements"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Additional Statements</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder={`One statement per line, e.g.:\nfilename "pxelinux.0"\nnext-server 192.168.1.5`}
                      className="resize-none font-mono text-sm"
                      rows={3}
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    Additional ISC DHCP statements (e.g., for PXE boot)
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Creating...' : 'Create Host'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
