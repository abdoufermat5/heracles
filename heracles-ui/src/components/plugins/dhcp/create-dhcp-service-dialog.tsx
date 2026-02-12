/**
 * Create DHCP Service Dialog
 *
 * Dialog for creating a new DHCP service configuration
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

// CN validation regex (LDAP common name)
const cnRegex = /^[a-zA-Z0-9][a-zA-Z0-9_.-]*$/

// Form schema
const createServiceSchema = z.object({
  cn: z
    .string()
    .min(1, 'Service name is required')
    .max(64, 'Service name must be at most 64 characters')
    .regex(cnRegex, 'Service name can only contain letters, numbers, dots, hyphens, and underscores'),
  description: z.string().max(1024).optional(),
  statements: z.string().optional(),
  options: z.string().optional(),
  primary_server_dn: z.string().max(512).optional(),
  secondary_server_dn: z.string().max(512).optional(),
})

type CreateServiceFormData = z.infer<typeof createServiceSchema>

interface CreateDhcpServiceDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (data: {
    cn: string
    description?: string
    statements?: string[]
    options?: string[]
    primary_server_dn?: string
    secondary_server_dn?: string
  }) => Promise<void>
  isSubmitting?: boolean
}

export function CreateDhcpServiceDialog({
  open,
  onOpenChange,
  onSubmit,
  isSubmitting = false,
}: CreateDhcpServiceDialogProps) {
  const form = useForm<CreateServiceFormData>({
    resolver: zodResolver(createServiceSchema),
    defaultValues: {
      cn: '',
      description: '',
      statements: '',
      options: '',
      primary_server_dn: '',
      secondary_server_dn: '',
    },
  })

  const handleSubmit = async (data: CreateServiceFormData) => {
    try {
      // Parse multi-line statements and options into arrays
      const statements = data.statements
        ? data.statements.split('\n').map((s) => s.trim()).filter(Boolean)
        : undefined
      const options = data.options
        ? data.options.split('\n').map((o) => o.trim()).filter(Boolean)
        : undefined

      await onSubmit({
        cn: data.cn,
        description: data.description || undefined,
        statements,
        options,
        primary_server_dn: data.primary_server_dn || undefined,
        secondary_server_dn: data.secondary_server_dn || undefined,
      })

      toast.success(`DHCP service "${data.cn}" created successfully`)
      form.reset()
      onOpenChange(false)
    } catch {
      toast.error('Failed to create DHCP service')
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create DHCP Service</DialogTitle>
          <DialogDescription>
            Create a new DHCP service configuration. This will be the root container
            for subnets, hosts, and other DHCP objects.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
            {/* Service Name */}
            <FormField
              control={form.control}
              name="cn"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Service Name *</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="e.g., main-dhcp, production-dhcp"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    A unique identifier for this DHCP service
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
                      placeholder="Optional description of this DHCP service"
                      className="resize-none"
                      rows={2}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* DHCP Statements */}
            <FormField
              control={form.control}
              name="statements"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Global Statements</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder={`One statement per line, e.g.:\nauthoritative\nddns-update-style interim\ndefault-lease-time 3600`}
                      className="resize-none font-mono text-sm"
                      rows={4}
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    ISC DHCP server statements applied globally
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
                  <FormLabel>Global Options</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder={`One option per line, e.g.:\ndomain-name-servers 8.8.8.8, 8.8.4.4\ndomain-name "example.com"\nrouters 192.168.1.1`}
                      className="resize-none font-mono text-sm"
                      rows={4}
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    DHCP options sent to all clients (can be overridden at subnet/host level)
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Server DNs (collapsed by default) */}
            <details className="group">
              <summary className="cursor-pointer text-sm font-medium text-muted-foreground hover:text-foreground">
                Advanced: Server Configuration
              </summary>
              <div className="mt-4 space-y-4 pl-4 border-l">
                <FormField
                  control={form.control}
                  name="primary_server_dn"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Primary Server DN</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="cn=dhcp1,ou=servers,dc=example,dc=com"
                          {...field}
                        />
                      </FormControl>
                      <FormDescription>
                        LDAP DN of the primary DHCP server
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="secondary_server_dn"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Secondary Server DN</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="cn=dhcp2,ou=servers,dc=example,dc=com"
                          {...field}
                        />
                      </FormControl>
                      <FormDescription>
                        LDAP DN of the secondary/backup DHCP server
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </details>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Creating...' : 'Create Service'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
