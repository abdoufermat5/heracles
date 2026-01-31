/**
 * Create POSIX Group Dialog Component
 *
 * Dialog for creating a new standalone POSIX group.
 */

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
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

import { TrustModeSection } from '@/components/common/forms'
import { useNextIds, useCreatePosixGroup } from '@/hooks'
import { useDepartmentStore } from '@/stores'
import type { TrustMode } from '@/types/posix'

// Form schema for creating a new POSIX group
const createGroupSchema = z
  .object({
    cn: z
      .string()
      .min(1, 'Group name is required')
      .max(64, 'Group name must be at most 64 characters')
      .regex(
        /^[a-z][a-z0-9_-]*$/i,
        'Group name must start with a letter and contain only letters, numbers, underscores, and hyphens'
      ),
    gidNumber: z.number().min(1000, 'GID must be at least 1000').optional(),
    forceGid: z.boolean().default(false),
    description: z.string().max(255).optional(),
    // System trust
    trustMode: z.enum(['fullaccess', 'byhost']).optional().nullable(),
    host: z.array(z.string()).optional().nullable(),
  })
  .refine(
    (data) => {
      if (data.trustMode === 'byhost' && (!data.host || data.host.length === 0)) {
        return false
      }
      return true
    },
    {
      message: 'At least one host is required when trust mode is "By Host"',
      path: ['host'],
    }
  )

type CreateGroupFormData = z.infer<typeof createGroupSchema>

interface CreatePosixGroupDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

export function CreatePosixGroupDialog({
  open,
  onOpenChange,
  onSuccess,
}: CreatePosixGroupDialogProps) {
  const { data: nextIds } = useNextIds()
  const createMutation = useCreatePosixGroup()
  const { currentBase } = useDepartmentStore()

  const form = useForm<CreateGroupFormData>({
    resolver: zodResolver(createGroupSchema),
    defaultValues: {
      cn: '',
      description: '',
      forceGid: false,
      trustMode: undefined,
      host: [],
    },
  })

  const handleSubmit = async (data: CreateGroupFormData) => {
    await createMutation.mutateAsync({
      data: {
        cn: data.cn,
        gidNumber: data.gidNumber,
        forceGid: data.forceGid,
        description: data.description,
        trustMode: data.trustMode as TrustMode | undefined,
        host: data.trustMode === 'byhost' ? (data.host ?? undefined) : undefined,
      },
      baseDn: currentBase || undefined,
    })
    form.reset()
    onOpenChange(false)
    onSuccess?.()
  }

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      form.reset()
    }
    onOpenChange(newOpen)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Create POSIX Group</DialogTitle>
          <DialogDescription>
            Create a new standalone POSIX group for UNIX/Linux systems
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="cn"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Group Name</FormLabel>
                  <FormControl>
                    <Input placeholder="developers" {...field} />
                  </FormControl>
                  <FormDescription>
                    Must start with a letter and contain only letters, numbers,
                    underscores, and hyphens
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="space-y-2">
              <FormField
                control={form.control}
                name="gidNumber"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>GID Number (optional)</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        placeholder={
                          nextIds
                            ? `Next available: ${nextIds.next_gid}`
                            : 'Auto-assign'
                        }
                        {...field}
                        value={field.value ?? ''}
                        onChange={(e) =>
                          field.onChange(
                            e.target.value ? parseInt(e.target.value) : undefined
                          )
                        }
                      />
                    </FormControl>
                    <FormDescription>
                      Leave empty to auto-assign the next available GID
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="forceGid"
                render={({ field }) => (
                  <FormItem className="flex items-center gap-2 space-y-0">
                    <FormControl>
                      <Checkbox
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    </FormControl>
                    <FormLabel className="text-xs font-normal text-muted-foreground">
                      Force GID (allow duplicate)
                    </FormLabel>
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description (optional)</FormLabel>
                  <FormControl>
                    <Input placeholder="Development team" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* System Trust Section */}
            <TrustModeSection control={form.control} />

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => handleOpenChange(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? 'Creating...' : 'Create'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
