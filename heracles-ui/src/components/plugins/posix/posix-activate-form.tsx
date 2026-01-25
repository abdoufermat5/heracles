import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Terminal, Loader2, Info } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { HostSelector } from '@/components/common'
import { useAvailableShells, usePosixGroups, useNextIds } from '@/hooks'
import type { PosixAccountCreate, TrustMode, PrimaryGroupMode } from '@/types/posix'

const posixActivateSchema = z.object({
  // ID allocation
  uidNumber: z.number().min(1000).max(65534).optional().nullable(),
  forceUid: z.boolean().default(false),
  // Primary group
  primaryGroupMode: z.enum(['select_existing', 'create_personal']).default('select_existing'),
  gidNumber: z.number().min(1000).max(65534).optional().nullable(),
  forceGid: z.boolean().default(false),
  // Basic attributes
  homeDirectory: z.string().min(1).regex(/^\/[\w./-]+$/, 'Must be an absolute path').optional().nullable(),
  loginShell: z.string().min(1).default('/bin/bash'),
  gecos: z.string().optional().nullable(),
  // System trust
  trustMode: z.enum(['fullaccess', 'byhost']).optional().nullable(),
  host: z.array(z.string()).optional().nullable(),
}).refine(
  (data) => {
    if (data.primaryGroupMode === 'select_existing' && !data.gidNumber) {
      return false
    }
    return true
  },
  {
    message: 'Please select a primary group',
    path: ['gidNumber'],
  }
).refine(
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
      forceUid: false,
      primaryGroupMode: 'select_existing',
      gidNumber: undefined,
      forceGid: false,
      homeDirectory: `/home/${uid}`,
      loginShell: shellsData?.default || '/bin/bash',
      gecos: displayName || '',
      trustMode: undefined,
      host: [],
    },
  })

  const primaryGroupMode = form.watch('primaryGroupMode')
  const trustMode = form.watch('trustMode')
  const forceUid = form.watch('forceUid')

  const handleSubmit = async (data: PosixActivateFormData) => {
    const submitData: PosixAccountCreate = {
      uidNumber: data.uidNumber,
      forceUid: data.forceUid,
      primaryGroupMode: data.primaryGroupMode as PrimaryGroupMode,
      gidNumber: data.primaryGroupMode === 'select_existing' ? data.gidNumber : undefined,
      forceGid: data.forceGid,
      homeDirectory: data.homeDirectory,
      loginShell: data.loginShell,
      gecos: data.gecos,
      trustMode: data.trustMode as TrustMode | undefined,
      host: data.trustMode === 'byhost' ? data.host ?? undefined : undefined,
    }
    await onSubmit(submitData)
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
                <FormLabel className="flex items-center gap-2">
                  UID Number
                  {forceUid && (
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger>
                          <Info className="h-3 w-3 text-muted-foreground" />
                        </TooltipTrigger>
                        <TooltipContent>Force UID is enabled</TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  )}
                </FormLabel>
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
                <div className="flex items-center gap-2 mt-1">
                  <FormField
                    control={form.control}
                    name="forceUid"
                    render={({ field: forceField }) => (
                      <FormItem className="flex items-center gap-2 space-y-0">
                        <FormControl>
                          <Checkbox
                            checked={forceField.value}
                            onCheckedChange={forceField.onChange}
                          />
                        </FormControl>
                        <FormLabel className="text-xs font-normal text-muted-foreground">
                          Force UID
                        </FormLabel>
                      </FormItem>
                    )}
                  />
                </div>
                <FormDescription>
                  Leave empty for auto-allocation
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Primary Group Mode */}
          <FormField
            control={form.control}
            name="primaryGroupMode"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Primary Group Mode *</FormLabel>
                <Select onValueChange={field.onChange} value={field.value}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Select mode" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="select_existing">Select existing group</SelectItem>
                    <SelectItem value="create_personal">Create personal group</SelectItem>
                  </SelectContent>
                </Select>
                <FormDescription>
                  {primaryGroupMode === 'create_personal' 
                    ? `A personal group "${uid}" will be created` 
                    : 'Select an existing POSIX group'}
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Primary Group Selection (only shown when mode is select_existing) */}
          {primaryGroupMode === 'select_existing' && (
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
          )}

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

        {/* System Trust Section */}
        <div className="border rounded-lg p-4 space-y-4">
          <h4 className="font-medium text-sm">System Trust (Optional)</h4>
          <p className="text-xs text-muted-foreground">
            Control which systems this user can access
          </p>

          <FormField
            control={form.control}
            name="trustMode"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Trust Mode</FormLabel>
                <Select 
                  onValueChange={(value) => field.onChange(value === 'none' ? null : value)} 
                  value={field.value ?? 'none'}
                >
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="No restriction" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="none">No restriction</SelectItem>
                    <SelectItem value="fullaccess">Full access (all systems)</SelectItem>
                    <SelectItem value="byhost">Restricted by host</SelectItem>
                  </SelectContent>
                </Select>
                <FormDescription>
                  {!trustMode && 'User will have default system access'}
                  {trustMode === 'fullaccess' && 'User can access all systems'}
                  {trustMode === 'byhost' && 'User can only access specified hosts'}
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          {trustMode === 'byhost' && (
            <FormField
              control={form.control}
              name="host"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Allowed Hosts *</FormLabel>
                  <FormControl>
                    <HostSelector
                      value={field.value ?? []}
                      onChange={field.onChange}
                      placeholder="Select allowed hosts..."
                    />
                  </FormControl>
                  <FormDescription>
                    Select the systems this user can access
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          )}
        </div>

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
