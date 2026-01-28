/**
 * Create Zone Dialog
 *
 * Dialog for creating a new DNS zone with SOA configuration.
 */

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'

import { useCreateDnsZone } from '@/hooks/use-dns'

// Zone name validation regex
const zoneNameRegex = /^[a-z0-9]([a-z0-9\-\.]*[a-z0-9])?$/

// FQDN validation (must end with dot or we add it)
const fqdnRegex = /^[a-z0-9]([a-z0-9\-\.]*[a-z0-9])?\.?$/

// Form schema
const createZoneSchema = z.object({
  zoneName: z
    .string()
    .min(1, 'Zone name is required')
    .max(253, 'Zone name is too long')
    .toLowerCase()
    .refine((v) => zoneNameRegex.test(v.replace(/\.$/, '')), {
      message: 'Invalid zone name format',
    }),
  soaPrimaryNs: z
    .string()
    .min(1, 'Primary nameserver is required')
    .toLowerCase()
    .refine((v) => fqdnRegex.test(v), {
      message: 'Invalid FQDN format',
    }),
  soaAdminEmail: z
    .string()
    .min(1, 'Admin email is required')
    .toLowerCase()
    .refine((v) => fqdnRegex.test(v), {
      message: 'Use DNS format (admin.example.org.)',
    }),
  defaultTtl: z.coerce
    .number()
    .int()
    .min(60, 'Minimum TTL is 60 seconds')
    .max(604800, 'Maximum TTL is 7 days')
    .default(3600),
  soaRefresh: z.coerce.number().int().min(60).default(3600),
  soaRetry: z.coerce.number().int().min(60).default(600),
  soaExpire: z.coerce.number().int().min(3600).default(604800),
  soaMinimum: z.coerce.number().int().min(60).default(86400),
})

type CreateZoneFormData = z.infer<typeof createZoneSchema>

interface CreateZoneDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CreateZoneDialog({ open, onOpenChange }: CreateZoneDialogProps) {
  const createMutation = useCreateDnsZone()

  const form = useForm<CreateZoneFormData>({
    resolver: zodResolver(createZoneSchema),
    defaultValues: {
      zoneName: '',
      soaPrimaryNs: '',
      soaAdminEmail: '',
      defaultTtl: 3600,
      soaRefresh: 3600,
      soaRetry: 600,
      soaExpire: 604800,
      soaMinimum: 86400,
    },
  })

  const handleCreate = async (data: CreateZoneFormData) => {
    try {
      // Ensure FQDNs end with dot
      const primaryNs = data.soaPrimaryNs.endsWith('.')
        ? data.soaPrimaryNs
        : `${data.soaPrimaryNs}.`
      const adminEmail = data.soaAdminEmail.endsWith('.')
        ? data.soaAdminEmail
        : `${data.soaAdminEmail}.`

      await createMutation.mutateAsync({
        zoneName: data.zoneName.replace(/\.$/, ''), // Remove trailing dot from zone name
        soaPrimaryNs: primaryNs,
        soaAdminEmail: adminEmail,
        defaultTtl: data.defaultTtl,
        soaRefresh: data.soaRefresh,
        soaRetry: data.soaRetry,
        soaExpire: data.soaExpire,
        soaMinimum: data.soaMinimum,
      })
      toast.success(`Zone "${data.zoneName}" created successfully`)
      onOpenChange(false)
      form.reset()
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to create zone'
      )
    }
  }

  const handleClose = () => {
    onOpenChange(false)
    form.reset()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create DNS Zone</DialogTitle>
          <DialogDescription>
            Create a new DNS zone with SOA configuration
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(handleCreate)}
            className="space-y-6"
          >
            {/* Basic Info */}
            <div className="space-y-4">
              <FormField
                control={form.control}
                name="zoneName"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Zone Name *</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="example.org"
                        className="font-mono"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      Domain name (e.g., example.org) or reverse zone
                      (e.g., 168.192.in-addr.arpa)
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="soaPrimaryNs"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Primary Nameserver *</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="ns1.example.org."
                        className="font-mono"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      FQDN of the primary nameserver (with trailing dot)
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="soaAdminEmail"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Admin Email *</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="admin.example.org."
                        className="font-mono"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      Email in DNS format (admin.example.org. = admin@example.org)
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="defaultTtl"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Default TTL (seconds)</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min={60}
                        max={604800}
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      Default time-to-live for records (3600 = 1 hour)
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Advanced SOA Settings */}
            <Accordion type="single" collapsible>
              <AccordionItem value="soa-advanced">
                <AccordionTrigger className="text-sm">
                  Advanced SOA Settings
                </AccordionTrigger>
                <AccordionContent className="space-y-4 pt-4">
                  <div className="grid grid-cols-2 gap-4">
                    <FormField
                      control={form.control}
                      name="soaRefresh"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Refresh (seconds)</FormLabel>
                          <FormControl>
                            <Input type="number" min={60} {...field} />
                          </FormControl>
                          <FormDescription>
                            How often secondaries check for updates
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="soaRetry"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Retry (seconds)</FormLabel>
                          <FormControl>
                            <Input type="number" min={60} {...field} />
                          </FormControl>
                          <FormDescription>
                            Wait time if refresh fails
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <FormField
                      control={form.control}
                      name="soaExpire"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Expire (seconds)</FormLabel>
                          <FormControl>
                            <Input type="number" min={3600} {...field} />
                          </FormControl>
                          <FormDescription>
                            When secondaries stop serving zone
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="soaMinimum"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Minimum TTL (seconds)</FormLabel>
                          <FormControl>
                            <Input type="number" min={60} {...field} />
                          </FormControl>
                          <FormDescription>
                            Negative cache TTL
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                </AccordionContent>
              </AccordionItem>
            </Accordion>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? 'Creating...' : 'Create Zone'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
