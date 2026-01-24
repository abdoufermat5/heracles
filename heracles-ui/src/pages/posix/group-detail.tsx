/**
 * POSIX Group Detail Page
 * 
 * View and edit a single POSIX group, manage members.
 */

import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, Users, Plus, Trash2, Save, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

import {
  usePosixGroup,
  useUpdatePosixGroup,
  useDeletePosixGroup,
  useAddPosixGroupMember,
  useRemovePosixGroupMember,
} from '@/hooks'
import type { TrustMode } from '@/types/posix'

// Form schema for editing the group
const editSchema = z.object({
  description: z.string().max(255).optional(),
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

// Form schema for adding a member
const addMemberSchema = z.object({
  uid: z.string().min(1, 'User ID is required'),
})

type EditFormData = z.infer<typeof editSchema>
type AddMemberFormData = z.infer<typeof addMemberSchema>

export default function PosixGroupDetailPage() {
  const { cn } = useParams<{ cn: string }>()
  const navigate = useNavigate()

  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [showAddMemberDialog, setShowAddMemberDialog] = useState(false)
  const [memberToRemove, setMemberToRemove] = useState<string | null>(null)

  const { data: group, isLoading, error, refetch } = usePosixGroup(cn!)
  const updateMutation = useUpdatePosixGroup(cn!)
  const deleteMutation = useDeletePosixGroup()
  const addMemberMutation = useAddPosixGroupMember(cn!)
  const removeMemberMutation = useRemovePosixGroupMember(cn!)

  const editForm = useForm<EditFormData>({
    resolver: zodResolver(editSchema),
    values: {
      description: group?.description ?? '',
      trustMode: group?.trustMode ?? null,
      host: group?.host ?? [],
    },
  })

  const trustMode = editForm.watch('trustMode')

  const addMemberForm = useForm<AddMemberFormData>({
    resolver: zodResolver(addMemberSchema),
    defaultValues: {
      uid: '',
    },
  })

  const handleUpdate = async (data: EditFormData) => {
    try {
      await updateMutation.mutateAsync({
        description: data.description || undefined,
        trustMode: data.trustMode as TrustMode | null,
        host: data.trustMode === 'byhost' ? data.host : null,
      })
      toast.success('Group updated successfully')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to update group')
    }
  }

  const handleDelete = async () => {
    try {
      await deleteMutation.mutateAsync(cn!)
      toast.success('Group deleted successfully')
      navigate('/posix/groups')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to delete group')
    }
  }

  const handleAddMember = async (data: AddMemberFormData) => {
    try {
      await addMemberMutation.mutateAsync(data.uid)
      toast.success(`Added ${data.uid} to the group`)
      setShowAddMemberDialog(false)
      addMemberForm.reset()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to add member')
    }
  }

  const handleRemoveMember = async () => {
    if (!memberToRemove) return

    try {
      await removeMemberMutation.mutateAsync(memberToRemove)
      toast.success(`Removed ${memberToRemove} from the group`)
      setMemberToRemove(null)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to remove member')
    }
  }

  if (isLoading) {
    return (
      <div className="container mx-auto py-6 space-y-6">
        <Skeleton className="h-8 w-48" />
        <Card>
          <CardContent className="pt-6 space-y-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error || !group) {
    return (
      <div className="container mx-auto py-6">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-8 text-destructive">
              <p>Failed to load POSIX group</p>
              <div className="flex items-center justify-center gap-2 mt-4">
                <Button variant="outline" size="sm" onClick={() => refetch()}>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Retry
                </Button>
                <Button variant="outline" size="sm" asChild>
                  <Link to="/posix/groups">
                    <ArrowLeft className="h-4 w-4 mr-2" />
                    Back to Groups
                  </Link>
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link to="/posix/groups">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Users className="h-6 w-6" />
              {group.cn}
            </h1>
            <p className="text-muted-foreground">
              POSIX Group • GID {group.gidNumber}
            </p>
          </div>
        </div>
        <Button variant="destructive" onClick={() => setShowDeleteDialog(true)}>
          <Trash2 className="h-4 w-4 mr-2" />
          Delete Group
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Group Details */}
        <Card>
          <CardHeader>
            <CardTitle>Group Details</CardTitle>
            <CardDescription>Edit the POSIX group settings</CardDescription>
          </CardHeader>
          <CardContent>
            <Form {...editForm}>
              <form onSubmit={editForm.handleSubmit(handleUpdate)} className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Group Name (cn)</label>
                  <Input value={group.cn} disabled />
                  <p className="text-xs text-muted-foreground">
                    Group name cannot be changed
                  </p>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">GID Number</label>
                  <Input value={group.gidNumber} disabled />
                  <p className="text-xs text-muted-foreground">
                    GID cannot be changed after creation
                  </p>
                </div>

                <FormField
                  control={editForm.control}
                  name="description"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Description</FormLabel>
                      <FormControl>
                        <Input placeholder="Group description" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* System Trust Section */}
                <div className="border rounded-lg p-4 space-y-4">
                  <div className="flex items-center justify-between">
                    <h4 className="font-medium text-sm">System Trust</h4>
                    {group.trustMode && (
                      <Badge variant={group.trustMode === 'fullaccess' ? 'default' : 'secondary'}>
                        {group.trustMode === 'fullaccess' ? 'Full Access' : 'By Host'}
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Control which systems this group has access to
                  </p>

                  <FormField
                    control={editForm.control}
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
                          {!trustMode && 'Group will have default system access'}
                          {trustMode === 'fullaccess' && 'Group can access all systems'}
                          {trustMode === 'byhost' && 'Group can only access specified hosts'}
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {trustMode === 'byhost' && (
                    <FormField
                      control={editForm.control}
                      name="host"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Allowed Hosts *</FormLabel>
                          <FormControl>
                            <Input
                              placeholder="server1.example.com, server2.example.com"
                              value={field.value?.join(', ') ?? ''}
                              onChange={(e) => {
                                const hosts = e.target.value
                                  .split(',')
                                  .map((h) => h.trim())
                                  .filter((h) => h.length > 0)
                                field.onChange(hosts.length > 0 ? hosts : [])
                              }}
                            />
                          </FormControl>
                          <FormDescription>
                            Comma-separated list of hostnames
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  )}
                </div>

                <Button type="submit" disabled={updateMutation.isPending}>
                  <Save className="h-4 w-4 mr-2" />
                  {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
                </Button>
              </form>
            </Form>
          </CardContent>
        </Card>

        {/* Members */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Members</CardTitle>
                <CardDescription>
                  Users in this POSIX group (memberUid)
                </CardDescription>
              </div>
              <Button size="sm" onClick={() => setShowAddMemberDialog(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Member
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {group.memberUid.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <p>No members in this group</p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-4"
                  onClick={() => setShowAddMemberDialog(true)}
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add First Member
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                {group.memberUid.map((uid) => (
                  <div
                    key={uid}
                    className="flex items-center justify-between p-2 rounded-md bg-muted/50"
                  >
                    <div className="flex items-center gap-2">
                      <Users className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">{uid}</span>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setMemberToRemove(uid)}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Add Member Dialog */}
      <Dialog open={showAddMemberDialog} onOpenChange={setShowAddMemberDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Member</DialogTitle>
            <DialogDescription>
              Add a user to this POSIX group by their UID
            </DialogDescription>
          </DialogHeader>
          <Form {...addMemberForm}>
            <form onSubmit={addMemberForm.handleSubmit(handleAddMember)} className="space-y-4">
              <FormField
                control={addMemberForm.control}
                name="uid"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>User ID (uid)</FormLabel>
                    <FormControl>
                      <Input placeholder="jdoe" {...field} />
                    </FormControl>
                    <FormDescription>
                      Enter the user's uid attribute value
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setShowAddMemberDialog(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={addMemberMutation.isPending}>
                  {addMemberMutation.isPending ? 'Adding...' : 'Add Member'}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      {/* Remove Member Confirmation */}
      <AlertDialog open={!!memberToRemove} onOpenChange={(open) => !open && setMemberToRemove(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove Member</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to remove "{memberToRemove}" from this group?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRemoveMember}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {removeMemberMutation.isPending ? 'Removing...' : 'Remove'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete Group Confirmation */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete POSIX Group</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the POSIX group "{group.cn}"?
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
