/**
 * Create Record Dialog
 *
 * Dialog for creating a new DNS record.
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

import { useCreateDnsRecord } from '@/hooks/use-dns'
import {
  RECORD_TYPES,
  RECORD_TYPE_LABELS,
  RECORD_TYPE_DESCRIPTIONS,
  recordRequiresPriority,
  getRecordValuePlaceholder,
  type RecordType,
} from '@/types/dns'

// IPv4 validation
const ipv4Regex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/

// Form schema
const createRecordSchema = z
  .object({
    name: z
      .string()
      .min(1, 'Record name is required')
      .max(253, 'Name is too long')
      .toLowerCase(),
    recordType: z.enum(RECORD_TYPES as unknown as [RecordType, ...RecordType[]]),
    value: z.string().min(1, 'Value is required'),
    ttl: z.union([z.coerce.number().int().min(60).max(604800), z.null()]).optional(),
    priority: z.union([z.coerce.number().int().min(0).max(65535), z.null()]).optional(),
  })
  .refine(
    (data) => {
      // A records must be valid IPv4
      if (data.recordType === 'A') {
        return ipv4Regex.test(data.value)
      }
      return true
    },
    { message: 'Invalid IPv4 address', path: ['value'] }
  )
  .refine(
    (data) => {
      // MX and SRV require priority
      if (recordRequiresPriority(data.recordType)) {
        return data.priority !== null && data.priority !== undefined
      }
      return true
    },
    { message: 'Priority is required for this record type', path: ['priority'] }
  )

type CreateRecordFormData = z.infer<typeof createRecordSchema>

interface CreateRecordDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  zoneName: string
}

export function CreateRecordDialog({
  open,
  onOpenChange,
  zoneName,
}: CreateRecordDialogProps) {
  const createMutation = useCreateDnsRecord(zoneName)

  const form = useForm<CreateRecordFormData>({
    resolver: zodResolver(createRecordSchema),
    defaultValues: {
      name: '',
      recordType: 'A',
      value: '',
      ttl: null,
      priority: null,
    },
  })

  const watchedType = form.watch('recordType')
  const showPriority = recordRequiresPriority(watchedType)

  const handleCreate = async (data: CreateRecordFormData) => {
    try {
      await createMutation.mutateAsync({
        name: data.name,
        recordType: data.recordType,
        value: data.value,
        ttl: data.ttl ?? undefined,
        priority: data.priority ?? undefined,
      })
      toast.success('Record created successfully')
      onOpenChange(false)
      form.reset()
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to create record'
      )
    }
  }

  const handleClose = () => {
    onOpenChange(false)
    form.reset()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Add DNS Record</DialogTitle>
          <DialogDescription>
            Add a new record to zone <code className="font-mono">{zoneName}</code>
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(handleCreate)}
            className="space-y-4"
          >
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name *</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="www"
                        className="font-mono"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      Use @ for zone apex
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="recordType"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Type *</FormLabel>
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
                        {RECORD_TYPES.map((type) => (
                          <SelectItem key={type} value={type}>
                            {RECORD_TYPE_LABELS[type]}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      {RECORD_TYPE_DESCRIPTIONS[watchedType]}
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="value"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Value *</FormLabel>
                  <FormControl>
                    <Input
                      placeholder={getRecordValuePlaceholder(watchedType)}
                      className="font-mono"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-2 gap-4">
              {showPriority && (
                <FormField
                  control={form.control}
                  name="priority"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Priority *</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min={0}
                          max={65535}
                          placeholder="10"
                          {...field}
                          value={field.value ?? ''}
                        />
                      </FormControl>
                      <FormDescription>
                        Lower = higher priority
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}

              <FormField
                control={form.control}
                name="ttl"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>TTL (seconds)</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min={60}
                        max={604800}
                        placeholder="3600"
                        {...field}
                        value={field.value ?? ''}
                      />
                    </FormControl>
                    <FormDescription>
                      Leave empty for zone default
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? 'Creating...' : 'Add Record'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
