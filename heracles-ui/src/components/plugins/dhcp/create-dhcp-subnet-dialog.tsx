/**
 * Create DHCP Subnet Dialog
 *
 * Dialog for creating a new DHCP subnet
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

// IP address validation
const ipAddressRegex =
  /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/

// Form schema
const createSubnetSchema = z
  .object({
    cn: z
      .string()
      .min(1, 'Network address is required')
      .regex(ipAddressRegex, 'Invalid network address format'),
    netmask: z.coerce
      .number()
      .min(0, 'Netmask must be between 0 and 32')
      .max(32, 'Netmask must be between 0 and 32'),
    description: z.string().max(1024).optional(),
    range_start: z.string().optional(),
    range_end: z.string().optional(),
    statements: z.string().optional(),
    options: z.string().optional(),
  })
  .refine(
    (data) => {
      // Validate range start if provided
      if (data.range_start && !ipAddressRegex.test(data.range_start)) {
        return false
      }
      return true
    },
    { message: 'Invalid IP address format', path: ['range_start'] }
  )
  .refine(
    (data) => {
      // Validate range end if provided
      if (data.range_end && !ipAddressRegex.test(data.range_end)) {
        return false
      }
      return true
    },
    { message: 'Invalid IP address format', path: ['range_end'] }
  )
  .refine(
    (data) => {
      // If one range field is set, both must be set
      if ((data.range_start && !data.range_end) || (!data.range_start && data.range_end)) {
        return false
      }
      return true
    },
    { message: 'Both range start and end must be specified', path: ['range_end'] }
  )

type CreateSubnetFormData = z.infer<typeof createSubnetSchema>

// Common netmask values
const COMMON_NETMASKS = [
  { value: '8', label: '/8 (255.0.0.0) - Class A' },
  { value: '16', label: '/16 (255.255.0.0) - Class B' },
  { value: '24', label: '/24 (255.255.255.0) - Class C' },
  { value: '25', label: '/25 (255.255.255.128) - 128 hosts' },
  { value: '26', label: '/26 (255.255.255.192) - 64 hosts' },
  { value: '27', label: '/27 (255.255.255.224) - 32 hosts' },
  { value: '28', label: '/28 (255.255.255.240) - 16 hosts' },
  { value: '29', label: '/29 (255.255.255.248) - 8 hosts' },
  { value: '30', label: '/30 (255.255.255.252) - 4 hosts' },
]

interface CreateDhcpSubnetDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  serviceCn: string
  onSubmit: (data: {
    cn: string
    netmask: number
    description?: string
    range?: string
    statements?: string[]
    options?: string[]
  }) => Promise<void>
  isSubmitting?: boolean
}

export function CreateDhcpSubnetDialog({
  open,
  onOpenChange,
  serviceCn,
  onSubmit,
  isSubmitting = false,
}: CreateDhcpSubnetDialogProps) {
  const form = useForm<CreateSubnetFormData>({
    resolver: zodResolver(createSubnetSchema),
    defaultValues: {
      cn: '',
      netmask: 24,
      description: '',
      range_start: '',
      range_end: '',
      statements: '',
      options: '',
    },
  })

  const handleSubmit = async (data: CreateSubnetFormData) => {
    try {
      // Build range string if both values provided
      const range =
        data.range_start && data.range_end
          ? `${data.range_start} ${data.range_end}`
          : undefined

      // Parse multi-line statements and options into arrays
      const statements = data.statements
        ? data.statements.split('\n').map((s) => s.trim()).filter(Boolean)
        : undefined
      const options = data.options
        ? data.options.split('\n').map((o) => o.trim()).filter(Boolean)
        : undefined

      await onSubmit({
        cn: data.cn,
        netmask: data.netmask,
        description: data.description || undefined,
        range,
        statements,
        options,
      })

      toast.success(`Subnet "${data.cn}/${data.netmask}" created successfully`)
      form.reset()
      onOpenChange(false)
    } catch {
      toast.error('Failed to create subnet')
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create Subnet</DialogTitle>
          <DialogDescription>
            Add a new subnet to the DHCP service "{serviceCn}".
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              {/* Network Address */}
              <FormField
                control={form.control}
                name="cn"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Network Address *</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="e.g., 192.168.1.0"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      Network ID (host bits should be 0)
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Netmask */}
              <FormField
                control={form.control}
                name="netmask"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Netmask (CIDR) *</FormLabel>
                    <Select
                      onValueChange={field.onChange}
                      defaultValue={String(field.value)}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select netmask" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {COMMON_NETMASKS.map((nm) => (
                          <SelectItem key={nm.value} value={nm.value}>
                            {nm.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Description */}
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Optional description of this subnet"
                      className="resize-none"
                      rows={2}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* IP Range */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Dynamic IP Range</label>
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="range_start"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <Input
                          placeholder="Start IP (e.g., 192.168.1.100)"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="range_end"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <Input
                          placeholder="End IP (e.g., 192.168.1.200)"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              <p className="text-xs text-muted-foreground">
                Leave empty if addresses are only assigned to specific hosts
              </p>
            </div>

            {/* DHCP Options */}
            <FormField
              control={form.control}
              name="options"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>DHCP Options</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder={`One option per line, e.g.:\nrouters 192.168.1.1\ndomain-name-servers 192.168.1.2, 192.168.1.3\nbroadcast-address 192.168.1.255`}
                      className="resize-none font-mono text-sm"
                      rows={4}
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    DHCP options specific to this subnet
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Statements */}
            <FormField
              control={form.control}
              name="statements"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>DHCP Statements</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder={`One statement per line, e.g.:\ndefault-lease-time 3600\nmax-lease-time 7200`}
                      className="resize-none font-mono text-sm"
                      rows={3}
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    ISC DHCP statements for this subnet
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
                {isSubmitting ? 'Creating...' : 'Create Subnet'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
