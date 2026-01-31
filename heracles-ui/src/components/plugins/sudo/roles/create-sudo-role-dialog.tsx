/**
 * Create Sudo Role Dialog
 *
 * Dialog for creating a new sudo role with all configuration options.
 */

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
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

import { useCreateSudoRole } from '@/hooks/use-sudo'
import { stringToArray } from '@/lib/string-helpers'
import { SUDO_OPTIONS, COMMON_COMMANDS } from '@/types/sudo'
import { toast } from 'sonner'
import { useDepartmentStore } from '@/stores'

// Form schema for creating a new sudo role
const createRoleSchema = z.object({
  cn: z
    .string()
    .min(1, 'Role name is required')
    .max(64, 'Role name must be at most 64 characters')
    .regex(
      /^[a-z][a-z0-9_-]*$/i,
      'Role name must start with a letter and contain only letters, numbers, underscores, and hyphens'
    ),
  description: z.string().max(255).optional(),
  sudoUser: z.string().optional(),
  sudoHost: z.string().optional(),
  sudoCommand: z.string().optional(),
  sudoRunAsUser: z.string().optional(),
  sudoRunAsGroup: z.string().optional(),
  sudoOption: z.array(z.string()).optional(),
  sudoOrder: z.number().min(0).optional(),
})

type CreateRoleFormData = z.infer<typeof createRoleSchema>

interface CreateSudoRoleDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CreateSudoRoleDialog({
  open,
  onOpenChange,
}: CreateSudoRoleDialogProps) {
  const createMutation = useCreateSudoRole()
  const { currentBase } = useDepartmentStore()

  const form = useForm<CreateRoleFormData>({
    resolver: zodResolver(createRoleSchema),
    defaultValues: {
      cn: '',
      description: '',
      sudoUser: '',
      sudoHost: 'ALL',
      sudoCommand: 'ALL',
      sudoRunAsUser: 'ALL',
      sudoRunAsGroup: '',
      sudoOption: [],
      sudoOrder: 0,
    },
  })

  const handleCreate = async (data: CreateRoleFormData) => {
    try {
      await createMutation.mutateAsync({
        data: {
          cn: data.cn,
          description: data.description,
          sudoUser: stringToArray(data.sudoUser),
          sudoHost: stringToArray(data.sudoHost),
          sudoCommand: stringToArray(data.sudoCommand),
          sudoRunAsUser: stringToArray(data.sudoRunAsUser),
          sudoRunAsGroup: stringToArray(data.sudoRunAsGroup),
          sudoOption: data.sudoOption,
          sudoOrder: data.sudoOrder,
        },
        baseDn: currentBase || undefined,
      })
      toast.success(`Sudo role "${data.cn}" created successfully`)
      onOpenChange(false)
      form.reset()
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to create sudo role'
      )
    }
  }

  const handleClose = () => {
    onOpenChange(false)
    form.reset()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create Sudo Role</DialogTitle>
          <DialogDescription>
            Define who can run which commands with elevated privileges
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleCreate)} className="space-y-6">
            {/* Basic Info */}
            <div className="space-y-4">
              <h4 className="font-medium text-sm border-b pb-2">
                Basic Information
              </h4>
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="cn"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Role Name *</FormLabel>
                      <FormControl>
                        <Input placeholder="webadmins" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="sudoOrder"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Priority Order</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          placeholder="0"
                          {...field}
                          value={field.value ?? 0}
                          onChange={(e) =>
                            field.onChange(parseInt(e.target.value) || 0)
                          }
                        />
                      </FormControl>
                      <FormDescription className="text-xs">
                        Higher = higher priority
                      </FormDescription>
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
                      <Input
                        placeholder="Web server administrators"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Who */}
            <div className="space-y-4">
              <h4 className="font-medium text-sm border-b pb-2">
                Who (Users/Groups)
              </h4>
              <FormField
                control={form.control}
                name="sudoUser"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Sudo Users</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="user1, %groupname, ALL"
                        className="h-20"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      Comma-separated. Use %groupname for groups, ALL for
                      everyone
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Where */}
            <div className="space-y-4">
              <h4 className="font-medium text-sm border-b pb-2">
                Where (Hosts)
              </h4>
              <FormField
                control={form.control}
                name="sudoHost"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Sudo Hosts</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="ALL, server1.example.com, 192.168.1.0/24"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      Comma-separated hostnames, IPs, or ALL
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* What */}
            <div className="space-y-4">
              <h4 className="font-medium text-sm border-b pb-2">
                What (Commands)
              </h4>
              <FormField
                control={form.control}
                name="sudoCommand"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Allowed Commands</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="ALL, /usr/bin/systemctl restart nginx, !/bin/su"
                        className="h-20"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      Comma-separated commands. Use ! prefix to deny. ALL allows
                      everything.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="flex flex-wrap gap-2">
                <span className="text-xs text-muted-foreground">Quick add:</span>
                {COMMON_COMMANDS.slice(0, 6).map((cmd) => (
                  <Badge
                    key={cmd.value}
                    variant="outline"
                    className="cursor-pointer hover:bg-accent"
                    onClick={() => {
                      const current = form.getValues('sudoCommand') || ''
                      const newValue = current
                        ? `${current}, ${cmd.value}`
                        : cmd.value
                      form.setValue('sudoCommand', newValue)
                    }}
                  >
                    {cmd.label}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Run As */}
            <div className="space-y-4">
              <h4 className="font-medium text-sm border-b pb-2">Run As</h4>
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="sudoRunAsUser"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Run As User</FormLabel>
                      <FormControl>
                        <Input placeholder="ALL, root" {...field} />
                      </FormControl>
                      <FormDescription className="text-xs">
                        Target user(s) for sudo
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="sudoRunAsGroup"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Run As Group</FormLabel>
                      <FormControl>
                        <Input placeholder="root, wheel" {...field} />
                      </FormControl>
                      <FormDescription className="text-xs">
                        Target group(s) for sudo
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>

            {/* Options */}
            <div className="space-y-4">
              <h4 className="font-medium text-sm border-b pb-2">Options</h4>
              <FormField
                control={form.control}
                name="sudoOption"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Sudo Options</FormLabel>
                    <div className="grid grid-cols-2 gap-3">
                      {SUDO_OPTIONS.map((option) => (
                        <div
                          key={option.value}
                          className="flex items-start space-x-2"
                        >
                          <Checkbox
                            id={option.value}
                            checked={field.value?.includes(option.value)}
                            onCheckedChange={(checked) => {
                              const current = field.value || []
                              if (checked) {
                                field.onChange([...current, option.value])
                              } else {
                                field.onChange(
                                  current.filter((v) => v !== option.value)
                                )
                              }
                            }}
                          />
                          <div className="grid gap-0.5 leading-none">
                            <label
                              htmlFor={option.value}
                              className="text-sm font-medium cursor-pointer"
                            >
                              {option.label}
                            </label>
                            <p className="text-xs text-muted-foreground">
                              {option.description}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
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
                {createMutation.isPending ? 'Creating...' : 'Create Role'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
