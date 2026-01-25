import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Save, Loader2 } from 'lucide-react'
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
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { HostSelector } from '@/components/common'
import { useAvailableShells, usePosixGroups } from '@/hooks'
import type { PosixAccountData, PosixAccountUpdate, TrustMode } from '@/types/posix'

const posixEditSchema = z.object({
  gidNumber: z.number().min(1000).max(65534).optional().nullable(),
  homeDirectory: z.string().min(1).regex(/^\/[\w./-]+$/, 'Must be an absolute path').optional().nullable(),
  loginShell: z.string().optional().nullable(),
  gecos: z.string().optional().nullable(),
  shadowMin: z.number().min(0).optional().nullable(),
  shadowMax: z.number().min(0).optional().nullable(),
  shadowWarning: z.number().min(0).optional().nullable(),
  shadowInactive: z.number().min(-1).optional().nullable(),
  shadowExpire: z.number().min(-1).optional().nullable(),
  // System trust
  trustMode: z.enum(['fullaccess', 'byhost']).optional().nullable(),
  host: z.array(z.string()).optional().nullable(),
}).refine(
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

type PosixEditFormData = z.infer<typeof posixEditSchema>

interface PosixEditFormProps {
  data: PosixAccountData
  onSubmit: (data: PosixAccountUpdate) => Promise<void>
  isSubmitting?: boolean
}

export function PosixEditForm({
  data,
  onSubmit,
  isSubmitting = false,
}: PosixEditFormProps) {
  const { data: shellsData } = useAvailableShells()
  const { data: posixGroupsData, isLoading: groupsLoading } = usePosixGroups()

  const form = useForm<PosixEditFormData>({
    resolver: zodResolver(posixEditSchema),
    defaultValues: {
      gidNumber: data.gidNumber ?? undefined,
      homeDirectory: data.homeDirectory ?? '',
      loginShell: data.loginShell ?? '/bin/bash',
      gecos: data.gecos ?? '',
      shadowMin: data.shadowMin ?? undefined,
      shadowMax: data.shadowMax ?? undefined,
      shadowWarning: data.shadowWarning ?? undefined,
      shadowInactive: data.shadowInactive ?? undefined,
      shadowExpire: data.shadowExpire,
      trustMode: data.trustMode ?? null,
      host: data.host ?? [],
    },
  })

  const trustMode = form.watch('trustMode')

  const handleSubmit = async (formData: PosixEditFormData) => {
    // Only include fields that have changed
    const update: PosixAccountUpdate = {}
    
    if (formData.gidNumber !== data.gidNumber && formData.gidNumber != null) {
      update.gidNumber = formData.gidNumber
    }
    if (formData.homeDirectory !== data.homeDirectory && formData.homeDirectory != null) {
      update.homeDirectory = formData.homeDirectory
    }
    if (formData.loginShell !== data.loginShell && formData.loginShell != null) {
      update.loginShell = formData.loginShell
    }
    if (formData.gecos !== data.gecos && formData.gecos != null) {
      update.gecos = formData.gecos
    }
    if (formData.shadowMin !== data.shadowMin && formData.shadowMin != null) {
      update.shadowMin = formData.shadowMin
    }
    if (formData.shadowMax !== data.shadowMax && formData.shadowMax != null) {
      update.shadowMax = formData.shadowMax
    }
    if (formData.shadowWarning !== data.shadowWarning && formData.shadowWarning != null) {
      update.shadowWarning = formData.shadowWarning
    }
    if (formData.shadowInactive !== data.shadowInactive && formData.shadowInactive != null) {
      update.shadowInactive = formData.shadowInactive
    }
    if (formData.shadowExpire !== data.shadowExpire && formData.shadowExpire != null) {
      update.shadowExpire = formData.shadowExpire
    }
    // Trust mode - include if changed (can set to null to remove)
    if (formData.trustMode !== data.trustMode) {
      update.trustMode = formData.trustMode as TrustMode | undefined
      update.host = formData.trustMode === 'byhost' ? formData.host ?? undefined : undefined
    } else if (formData.trustMode === 'byhost' && JSON.stringify(formData.host) !== JSON.stringify(data.host)) {
      update.host = formData.host ?? undefined
    }

    // Only submit if there are changes
    if (Object.keys(update).length > 0) {
      await onSubmit(update)
    }
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
        {/* Read-only UID */}
        <div className="space-y-2">
          <label className="text-sm font-medium">UID Number</label>
          <Input value={data.uidNumber} disabled className="bg-muted" />
          <p className="text-sm text-muted-foreground">
            UID cannot be changed after creation
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Primary Group */}
          <FormField
            control={form.control}
            name="gidNumber"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Primary Group</FormLabel>
                <Select
                  disabled={groupsLoading}
                  onValueChange={(value) => field.onChange(parseInt(value, 10))}
                  value={field.value?.toString()}
                >
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Select a group" />
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
                <Select
                  onValueChange={field.onChange}
                  value={field.value ?? undefined}
                >
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
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        {/* Home Directory */}
        <FormField
          control={form.control}
          name="homeDirectory"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Home Directory</FormLabel>
              <FormControl>
                <Input
                  {...field}
                  value={field.value ?? ''}
                  onChange={(e) => field.onChange(e.target.value || null)}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* GECOS */}
        <FormField
          control={form.control}
          name="gecos"
          render={({ field }) => (
            <FormItem>
              <FormLabel>GECOS (Full Name)</FormLabel>
              <FormControl>
                <Input
                  {...field}
                  value={field.value ?? ''}
                  onChange={(e) => field.onChange(e.target.value || null)}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Shadow/Password Policy - Collapsible */}
        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="shadow">
            <AccordionTrigger>Password Policy (Shadow)</AccordionTrigger>
            <AccordionContent className="space-y-4 pt-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="shadowMin"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Min Days Between Changes</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          placeholder="0"
                          {...field}
                          value={field.value ?? ''}
                          onChange={(e) => {
                            const value = e.target.value
                            field.onChange(value === '' ? null : parseInt(value, 10))
                          }}
                        />
                      </FormControl>
                      <FormDescription>
                        Minimum days before password can be changed
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="shadowMax"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Max Password Age (Days)</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          placeholder="99999"
                          {...field}
                          value={field.value ?? ''}
                          onChange={(e) => {
                            const value = e.target.value
                            field.onChange(value === '' ? null : parseInt(value, 10))
                          }}
                        />
                      </FormControl>
                      <FormDescription>
                        Maximum days password is valid
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="shadowWarning"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Warning Days</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          placeholder="7"
                          {...field}
                          value={field.value ?? ''}
                          onChange={(e) => {
                            const value = e.target.value
                            field.onChange(value === '' ? null : parseInt(value, 10))
                          }}
                        />
                      </FormControl>
                      <FormDescription>
                        Days before expiry to warn user
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="shadowInactive"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Inactive Days</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          placeholder="-1"
                          {...field}
                          value={field.value ?? ''}
                          onChange={(e) => {
                            const value = e.target.value
                            field.onChange(value === '' ? null : parseInt(value, 10))
                          }}
                        />
                      </FormControl>
                      <FormDescription>
                        Days after expiry before disable (-1 = never)
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              {/* Last Password Change (read-only) */}
              {data.shadowLastChange && (
                <div className="space-y-2">
                  <label className="text-sm font-medium">Last Password Change</label>
                  <Input
                    value={new Date(data.shadowLastChange * 86400 * 1000).toLocaleDateString()}
                    disabled
                    className="bg-muted"
                  />
                </div>
              )}
            </AccordionContent>
          </AccordionItem>
        </Accordion>

        {/* System Trust Section */}
        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="trust">
            <AccordionTrigger>System Trust</AccordionTrigger>
            <AccordionContent className="space-y-4 pt-4">
              <p className="text-xs text-muted-foreground mb-4">
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
            </AccordionContent>
          </AccordionItem>
        </Accordion>

        <div className="flex justify-end pt-4">
          <Button type="submit" disabled={isSubmitting || !form.formState.isDirty}>
            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            <Save className="mr-2 h-4 w-4" />
            Save Changes
          </Button>
        </div>
      </form>
    </Form>
  )
}
