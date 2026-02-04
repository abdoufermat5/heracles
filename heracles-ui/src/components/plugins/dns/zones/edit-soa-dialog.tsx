/**
 * Edit SOA Dialog
 *
 * Dialog for editing SOA record configuration for a DNS zone.
 * Allows modifying primary NS, admin email, TTL, and timing parameters.
 */

import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { Settings, Hash, Clock, RefreshCw } from 'lucide-react'

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
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'

import { useUpdateDnsZone } from '@/hooks/use-dns'
import type { DnsZone } from '@/types/dns'
import { useDepartmentStore } from '@/stores'

// FQDN validation (must end with dot or we add it)
const fqdnRegex = /^[a-z0-9]([a-z0-9\-\.]*[a-z0-9])?\.?$/

// Form schema for SOA update
const editSoaSchema = z.object({
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
    .max(604800, 'Maximum TTL is 7 days'),
  soaRefresh: z.coerce
    .number()
    .int()
    .min(60, 'Minimum refresh is 60 seconds')
    .max(2419200, 'Maximum refresh is 28 days'),
  soaRetry: z.coerce
    .number()
    .int()
    .min(60, 'Minimum retry is 60 seconds')
    .max(604800, 'Maximum retry is 7 days'),
  soaExpire: z.coerce
    .number()
    .int()
    .min(3600, 'Minimum expire is 1 hour')
    .max(31536000, 'Maximum expire is 1 year'),
  soaMinimum: z.coerce
    .number()
    .int()
    .min(60, 'Minimum is 60 seconds')
    .max(604800, 'Maximum is 7 days'),
})

type EditSoaFormData = z.infer<typeof editSoaSchema>

interface EditSoaDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  zone: DnsZone
}

// Helper function to format seconds to human readable
function formatDuration(seconds: number): string {
  if (seconds >= 86400) {
    const days = Math.floor(seconds / 86400)
    return `${days} day${days !== 1 ? 's' : ''}`
  }
  if (seconds >= 3600) {
    const hours = Math.floor(seconds / 3600)
    return `${hours} hour${hours !== 1 ? 's' : ''}`
  }
  if (seconds >= 60) {
    const mins = Math.floor(seconds / 60)
    return `${mins} minute${mins !== 1 ? 's' : ''}`
  }
  return `${seconds} seconds`
}

export function EditSoaDialog({ open, onOpenChange, zone }: EditSoaDialogProps) {
  const updateMutation = useUpdateDnsZone(zone.zoneName)
  const { currentBase } = useDepartmentStore()

  const form = useForm<EditSoaFormData>({
    resolver: zodResolver(editSoaSchema),
    defaultValues: {
      soaPrimaryNs: zone.soa.primaryNs,
      soaAdminEmail: zone.soa.adminEmail,
      defaultTtl: zone.defaultTtl,
      soaRefresh: zone.soa.refresh,
      soaRetry: zone.soa.retry,
      soaExpire: zone.soa.expire,
      soaMinimum: zone.soa.minimum,
    },
  })

  // Reset form when zone changes or dialog opens
  useEffect(() => {
    if (open) {
      form.reset({
        soaPrimaryNs: zone.soa.primaryNs,
        soaAdminEmail: zone.soa.adminEmail,
        defaultTtl: zone.defaultTtl,
        soaRefresh: zone.soa.refresh,
        soaRetry: zone.soa.retry,
        soaExpire: zone.soa.expire,
        soaMinimum: zone.soa.minimum,
      })
    }
  }, [open, zone, form])

  const handleUpdate = async (data: EditSoaFormData) => {
    try {
      // Ensure FQDNs end with dot
      const primaryNs = data.soaPrimaryNs.endsWith('.')
        ? data.soaPrimaryNs
        : `${data.soaPrimaryNs}.`
      const adminEmail = data.soaAdminEmail.endsWith('.')
        ? data.soaAdminEmail
        : `${data.soaAdminEmail}.`

      await updateMutation.mutateAsync({
        data: {
          soaPrimaryNs: primaryNs,
          soaAdminEmail: adminEmail,
          defaultTtl: data.defaultTtl,
          soaRefresh: data.soaRefresh,
          soaRetry: data.soaRetry,
          soaExpire: data.soaExpire,
          soaMinimum: data.soaMinimum,
        },
        baseDn: currentBase || undefined,
      })
      toast.success(`SOA record updated for "${zone.zoneName}"`, {
        description: 'Serial number has been incremented automatically.',
      })
      onOpenChange(false)
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to update SOA record'
      )
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Edit SOA Record
          </DialogTitle>
          <DialogDescription>
            Modify the Start of Authority record for{' '}
            <code className="font-mono font-medium">{zone.zoneName}</code>
          </DialogDescription>
        </DialogHeader>

        {/* Current Serial Info */}
        <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
          <Hash className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">Current Serial:</span>
          <Badge variant="secondary" className="font-mono">
            {zone.soa.serial}
          </Badge>
          <span className="text-xs text-muted-foreground ml-auto">
            Will auto-increment on save
          </span>
        </div>

        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(handleUpdate)}
            className="space-y-6"
          >
            <Tabs defaultValue="general" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="general">General</TabsTrigger>
                <TabsTrigger value="timing">Timing Parameters</TabsTrigger>
              </TabsList>

              {/* General Tab */}
              <TabsContent value="general" className="space-y-4 mt-4">
                <FormField
                  control={form.control}
                  name="soaPrimaryNs"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Primary Nameserver</FormLabel>
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
                      <FormLabel>Admin Email</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="admin.example.org."
                          className="font-mono"
                          {...field}
                        />
                      </FormControl>
                      <FormDescription>
                        DNS format: admin@example.org becomes admin.example.org.
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
                      <FormLabel>Default TTL</FormLabel>
                      <FormControl>
                        <div className="flex items-center gap-2">
                          <Input
                            type="number"
                            min={60}
                            max={604800}
                            className="font-mono"
                            {...field}
                          />
                          <span className="text-sm text-muted-foreground w-24">
                            {formatDuration(field.value || 0)}
                          </span>
                        </div>
                      </FormControl>
                      <FormDescription>
                        Default time-to-live for records (in seconds)
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </TabsContent>

              {/* Timing Tab */}
              <TabsContent value="timing" className="space-y-4 mt-4">
                <div className="grid grid-cols-2 gap-4">
                  <FormField
                    control={form.control}
                    name="soaRefresh"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="flex items-center gap-1">
                          <RefreshCw className="h-3 w-3" />
                          Refresh
                        </FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            min={60}
                            className="font-mono"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          {formatDuration(field.value || 0)}
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
                        <FormLabel className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          Retry
                        </FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            min={60}
                            className="font-mono"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          {formatDuration(field.value || 0)}
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="soaExpire"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Expire</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            min={3600}
                            className="font-mono"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          {formatDuration(field.value || 0)}
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
                        <FormLabel>Minimum (Negative TTL)</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            min={60}
                            className="font-mono"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          {formatDuration(field.value || 0)}
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                {/* Timing explanations */}
                <div className="text-xs text-muted-foreground space-y-1 p-3 bg-muted rounded-lg">
                  <p>
                    <strong>Refresh:</strong> How often secondary DNS servers check for updates
                  </p>
                  <p>
                    <strong>Retry:</strong> Wait time before retrying a failed refresh
                  </p>
                  <p>
                    <strong>Expire:</strong> When secondary servers stop answering if primary is unreachable
                  </p>
                  <p>
                    <strong>Minimum:</strong> TTL for negative responses (NXDOMAIN)
                  </p>
                </div>
              </TabsContent>
            </Tabs>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
