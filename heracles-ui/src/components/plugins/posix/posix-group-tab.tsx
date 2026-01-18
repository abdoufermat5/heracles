import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { Users, Power, PowerOff, AlertTriangle } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
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
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import {
  useGroupPosix,
  useActivateGroupPosix,
  useUpdateGroupPosix,
  useDeactivateGroupPosix,
  useNextIds,
} from '@/hooks'
import type { PosixGroupCreate, PosixGroupUpdate, PosixGroupData } from '@/types/posix'

interface PosixGroupTabProps {
  cn: string
}

// Activation form schema
const activateSchema = z.object({
  gidNumber: z.number().min(1000, 'GID must be at least 1000'),
})

// Edit form schema
const editSchema = z.object({
  gidNumber: z.number().min(1000, 'GID must be at least 1000'),
  description: z.string().optional(),
})

type ActivateFormData = z.infer<typeof activateSchema>
type EditFormData = z.infer<typeof editSchema>

export function PosixGroupTab({ cn }: PosixGroupTabProps) {
  const [showDeactivateDialog, setShowDeactivateDialog] = useState(false)
  const [showActivateForm, setShowActivateForm] = useState(false)

  const { data: posixStatus, isLoading, error, refetch } = useGroupPosix(cn)
  const { data: nextIds } = useNextIds()
  const activateMutation = useActivateGroupPosix(cn)
  const updateMutation = useUpdateGroupPosix(cn)
  const deactivateMutation = useDeactivateGroupPosix(cn)

  const handleActivate = async (data: PosixGroupCreate) => {
    try {
      await activateMutation.mutateAsync(data)
      toast.success('POSIX group enabled successfully')
      setShowActivateForm(false)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to enable POSIX group')
    }
  }

  const handleUpdate = async (data: PosixGroupUpdate) => {
    try {
      await updateMutation.mutateAsync(data)
      toast.success('POSIX group updated successfully')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to update POSIX group')
    }
  }

  const handleDeactivate = async () => {
    try {
      await deactivateMutation.mutateAsync()
      toast.success('POSIX group disabled successfully')
      setShowDeactivateDialog(false)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to disable POSIX group')
    }
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-72" />
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            POSIX Group
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-6 text-destructive">
            <p>Failed to load POSIX data</p>
            <Button variant="outline" size="sm" className="mt-2" onClick={() => refetch()}>
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  const isActive = posixStatus?.active ?? false
  const posixData = posixStatus?.data

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              <CardTitle>POSIX Group</CardTitle>
              {isActive ? (
                <Badge variant="default" className="bg-green-600">
                  <Power className="h-3 w-3 mr-1" />
                  Active
                </Badge>
              ) : (
                <Badge variant="secondary">
                  <PowerOff className="h-3 w-3 mr-1" />
                  Inactive
                </Badge>
              )}
            </div>
            {isActive && (
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setShowDeactivateDialog(true)}
              >
                <PowerOff className="h-4 w-4 mr-2" />
                Disable
              </Button>
            )}
          </div>
          <CardDescription>
            {isActive
              ? 'POSIX group settings for Unix/Linux systems'
              : 'Enable POSIX group to make it available on Unix/Linux systems'}
          </CardDescription>
        </CardHeader>

        <CardContent>
          {isActive && posixData ? (
            <PosixGroupEditForm
              data={posixData}
              onSubmit={handleUpdate}
              isSubmitting={updateMutation.isPending}
            />
          ) : showActivateForm ? (
            <PosixGroupActivateForm
              nextGid={nextIds?.gidNumber}
              onSubmit={handleActivate}
              onCancel={() => setShowActivateForm(false)}
              isSubmitting={activateMutation.isPending}
            />
          ) : (
            <div className="text-center py-8">
              <Users className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">POSIX Group Not Enabled</h3>
              <p className="text-muted-foreground mb-4">
                This group does not have POSIX attributes. Enable POSIX to make this 
                group available on Unix/Linux systems with a GID number.
              </p>
              <Button onClick={() => setShowActivateForm(true)}>
                <Power className="h-4 w-4 mr-2" />
                Enable POSIX Group
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Deactivate Confirmation Dialog */}
      <AlertDialog open={showDeactivateDialog} onOpenChange={setShowDeactivateDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-destructive" />
              Disable POSIX Group?
            </AlertDialogTitle>
            <AlertDialogDescription>
              This will remove POSIX attributes from this group:
              <ul className="list-disc list-inside mt-2 space-y-1">
                <li>GID number ({posixData?.gidNumber})</li>
                <li>POSIX group membership capabilities</li>
              </ul>
              <p className="mt-2 font-medium">
                Users will no longer be able to use this group as a POSIX group.
              </p>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeactivate}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deactivateMutation.isPending ? 'Disabling...' : 'Disable POSIX Group'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}

// Activation form sub-component
interface PosixGroupActivateFormProps {
  nextGid?: number
  onSubmit: (data: PosixGroupCreate) => void
  onCancel: () => void
  isSubmitting: boolean
}

function PosixGroupActivateForm({
  nextGid,
  onSubmit,
  onCancel,
  isSubmitting,
}: PosixGroupActivateFormProps) {
  const form = useForm<ActivateFormData>({
    resolver: zodResolver(activateSchema),
    defaultValues: {
      gidNumber: nextGid ?? 10000,
    },
  })

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <FormField
          control={form.control}
          name="gidNumber"
          render={({ field }) => (
            <FormItem>
              <FormLabel>GID Number *</FormLabel>
              <FormControl>
                <Input type="number" {...field} />
              </FormControl>
              <FormDescription>
                Group ID number for Unix/Linux systems.
                {nextGid && ` Next available: ${nextGid}`}
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="flex gap-2 justify-end">
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Enabling...' : 'Enable POSIX Group'}
          </Button>
        </div>
      </form>
    </Form>
  )
}

// Edit form sub-component
interface PosixGroupEditFormProps {
  data: PosixGroupData
  onSubmit: (data: PosixGroupUpdate) => void
  isSubmitting: boolean
}

function PosixGroupEditForm({
  data,
  onSubmit,
  isSubmitting,
}: PosixGroupEditFormProps) {
  const form = useForm<EditFormData>({
    resolver: zodResolver(editSchema),
    defaultValues: {
      gidNumber: data.gidNumber,
      description: data.description ?? '',
    },
  })

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2">
          <FormField
            control={form.control}
            name="gidNumber"
            render={({ field }) => (
              <FormItem>
                <FormLabel>GID Number</FormLabel>
                <FormControl>
                  <Input type="number" {...field} readOnly className="bg-muted" />
                </FormControl>
                <FormDescription>
                  Group ID number (read-only after creation)
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormItem>
            <FormLabel>Group Name</FormLabel>
            <Input value={data.cn} readOnly className="bg-muted" />
            <FormDescription>
              POSIX group name (cn attribute)
            </FormDescription>
          </FormItem>
        </div>

        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Description</FormLabel>
              <FormControl>
                <Input {...field} placeholder="Group description" />
              </FormControl>
              <FormDescription>
                Optional description for the POSIX group
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Members display (read-only) */}
        {data.memberUid && data.memberUid.length > 0 && (
          <div className="space-y-2">
            <FormLabel>Members ({data.memberUid.length})</FormLabel>
            <div className="flex flex-wrap gap-2 p-3 bg-muted rounded-md">
              {data.memberUid.map((member: string) => (
                <Badge key={member} variant="secondary">
                  {member}
                </Badge>
              ))}
            </div>
            <p className="text-sm text-muted-foreground">
              Manage members from the group members tab
            </p>
          </div>
        )}

        <div className="flex justify-end">
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </form>
    </Form>
  )
}
