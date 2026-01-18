import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Terminal, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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
import { useAvailableShells, usePosixGroups, useNextIds } from '@/hooks'
import type { PosixAccountCreate } from '@/types/posix'

const posixActivateSchema = z.object({
  uidNumber: z.number().min(1000).max(65534).optional().nullable(),
  gidNumber: z.number().min(1000).max(65534),
  homeDirectory: z.string().min(1).regex(/^\/[\w./-]+$/, 'Must be an absolute path').optional().nullable(),
  loginShell: z.string().min(1),
  gecos: z.string().optional().nullable(),
})

type PosixActivateFormData = z.infer<typeof posixActivateSchema>

interface PosixActivateFormProps {
  uid: string
  displayName: string
  onSubmit: (data: PosixAccountCreate) => Promise<void>
  onCancel: () => void
  isSubmitting?: boolean
}

export function PosixActivateForm({
  uid,
  displayName,
  onSubmit,
  onCancel,
  isSubmitting = false,
}: PosixActivateFormProps) {
  const { data: shellsData } = useAvailableShells()
  const { data: posixGroupsData, isLoading: groupsLoading } = usePosixGroups()
  const { data: nextIdsData } = useNextIds()

  const form = useForm<PosixActivateFormData>({
    resolver: zodResolver(posixActivateSchema),
    defaultValues: {
      uidNumber: undefined,
      gidNumber: 10000,
      homeDirectory: `/home/${uid}`,
      loginShell: shellsData?.default || '/bin/bash',
      gecos: displayName || '',
    },
  })

  const handleSubmit = async (data: PosixActivateFormData) => {
    await onSubmit({
      uidNumber: data.uidNumber,
      gidNumber: data.gidNumber,
      homeDirectory: data.homeDirectory,
      loginShell: data.loginShell,
      gecos: data.gecos,
    })
  }

  const defaultShells = [
    { value: '/bin/bash', label: 'Bash' },
    { value: '/bin/zsh', label: 'Zsh' },
    { value: '/bin/sh', label: 'Sh' },
    { value: '/usr/sbin/nologin', label: 'No Login' },
    { value: '/bin/false', label: 'False (disabled)' },
  ]

  // API returns shells as {value, label} objects
  const shells = shellsData?.shells || defaultShells

  const posixGroups = posixGroupsData?.groups || []

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
        <div className="flex items-center gap-2 mb-4">
          <Terminal className="h-5 w-5 text-muted-foreground" />
          <h3 className="text-lg font-medium">Enable Unix Account</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* UID Number */}
          <FormField
            control={form.control}
            name="uidNumber"
            render={({ field }) => (
              <FormItem>
                <FormLabel>UID Number</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    placeholder={nextIdsData ? `Auto (next: ${nextIdsData.next_uid})` : 'Auto'}
                    {...field}
                    value={field.value ?? ''}
                    onChange={(e) => {
                      const value = e.target.value
                      field.onChange(value === '' ? null : parseInt(value, 10))
                    }}
                  />
                </FormControl>
                <FormDescription>
                  Leave empty for auto-allocation
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Primary Group */}
          <FormField
            control={form.control}
            name="gidNumber"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Primary Group *</FormLabel>
                <Select
                  disabled={groupsLoading}
                  onValueChange={(value) => field.onChange(parseInt(value, 10))}
                  value={field.value?.toString()}
                >
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder={groupsLoading ? 'Loading...' : 'Select a group'} />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {posixGroups.map((group) => (
                      <SelectItem key={group.gidNumber} value={group.gidNumber.toString()}>
                        {group.cn} ({group.gidNumber})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormDescription>
                  User's primary Unix group
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Home Directory */}
          <FormField
            control={form.control}
            name="homeDirectory"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Home Directory</FormLabel>
                <FormControl>
                  <Input
                    placeholder={`/home/${uid}`}
                    {...field}
                    value={field.value ?? ''}
                    onChange={(e) => field.onChange(e.target.value || null)}
                  />
                </FormControl>
                <FormDescription>
                  User's home directory path
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Login Shell */}
          <FormField
            control={form.control}
            name="loginShell"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Login Shell</FormLabel>
                <Select onValueChange={field.onChange} value={field.value}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Select shell" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {shells.map((shell) => (
                      <SelectItem key={shell.value} value={shell.value}>
                        {shell.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormDescription>
                  Default shell for the user
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        {/* GECOS */}
        <FormField
          control={form.control}
          name="gecos"
          render={({ field }) => (
            <FormItem>
              <FormLabel>GECOS (Full Name)</FormLabel>
              <FormControl>
                <Input
                  placeholder={displayName || 'Full Name'}
                  {...field}
                  value={field.value ?? ''}
                  onChange={(e) => field.onChange(e.target.value || null)}
                />
              </FormControl>
              <FormDescription>
                General information, typically the full name
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="flex justify-end gap-2 pt-4">
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Enable Unix Account
          </Button>
        </div>
      </form>
    </Form>
  )
}
