/**
 * Mixed Group Detail Page
 *
 * View and edit a single Mixed Group (groupOfNames + posixGroup).
 * Mixed groups support both LDAP members (DNs) and UNIX members (UIDs).
 */

import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, Layers, Plus, Trash2, Save, RefreshCw, Users, UserPlus } from 'lucide-react'
import { toast } from 'sonner'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

import { DeleteDialog, TrustModeSection } from '@/components/common'
import {
  useMixedGroup,
  useUpdateMixedGroup,
  useDeleteMixedGroup,
  useAddMixedGroupMember,
  useRemoveMixedGroupMember,
  useAddMixedGroupMemberUid,
  useRemoveMixedGroupMemberUid,
} from '@/hooks'
import { PLUGIN_ROUTES } from '@/config/routes'
import type { TrustMode } from '@/types/posix'
import { useDepartmentStore } from '@/stores'

// Form schema for editing the group
const editSchema = z
  .object({
    description: z.string().max(255).optional(),
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

// Form schema for adding an LDAP member (DN)
const addMemberSchema = z.object({
  memberDn: z.string().min(1, 'Member DN is required'),
})

// Form schema for adding a UNIX member (UID)
const addMemberUidSchema = z.object({
  uid: z.string().min(1, 'User ID is required'),
})

type EditFormData = z.infer<typeof editSchema>
type AddMemberFormData = z.infer<typeof addMemberSchema>
type AddMemberUidFormData = z.infer<typeof addMemberUidSchema>

export function MixedGroupDetailPage() {
  const { cn } = useParams<{ cn: string }>()
  const navigate = useNavigate()

  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [showAddMemberDialog, setShowAddMemberDialog] = useState(false)
  const [showAddMemberUidDialog, setShowAddMemberUidDialog] = useState(false)
  const [memberToRemove, setMemberToRemove] = useState<string | null>(null)
  const [memberUidToRemove, setMemberUidToRemove] = useState<string | null>(null)

  const { currentBase } = useDepartmentStore()

  const { data: group, isLoading, error, refetch } = useMixedGroup(cn!, currentBase || undefined)
  const updateMutation = useUpdateMixedGroup(cn!)
  const deleteMutation = useDeleteMixedGroup()
  const addMemberMutation = useAddMixedGroupMember(cn!)
  const removeMemberMutation = useRemoveMixedGroupMember(cn!)
  const addMemberUidMutation = useAddMixedGroupMemberUid(cn!)
  const removeMemberUidMutation = useRemoveMixedGroupMemberUid(cn!)

  const editForm = useForm<EditFormData>({
    resolver: zodResolver(editSchema),
    values: {
      description: group?.description ?? '',
      trustMode: group?.trustMode ?? null,
      host: group?.host ?? [],
    },
  })

  const addMemberForm = useForm<AddMemberFormData>({
    resolver: zodResolver(addMemberSchema),
    defaultValues: {
      memberDn: '',
    },
  })

  const addMemberUidForm = useForm<AddMemberUidFormData>({
    resolver: zodResolver(addMemberUidSchema),
    defaultValues: {
      uid: '',
    },
  })

  const handleUpdate = async (data: EditFormData) => {
    try {
      await updateMutation.mutateAsync({
        data: {
          description: data.description || undefined,
          trustMode: data.trustMode as TrustMode | null,
          host: data.trustMode === 'byhost' ? data.host : null,
        },
        baseDn: currentBase || undefined,
      })
      toast.success('Mixed group updated successfully')
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to update group'
      )
    }
  }

  const handleDelete = async () => {
    try {
      await deleteMutation.mutateAsync({ cn: cn!, baseDn: currentBase || undefined })
      toast.success('Mixed group deleted successfully')
      navigate(PLUGIN_ROUTES.POSIX.MIXED_GROUPS)
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to delete group'
      )
    }
  }

  // LDAP member (DN) handlers
  const handleAddMember = async (data: AddMemberFormData) => {
    try {
      await addMemberMutation.mutateAsync({ memberDn: data.memberDn, baseDn: currentBase || undefined })
      toast.success(`Added member to the group`)
      setShowAddMemberDialog(false)
      addMemberForm.reset()
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to add member'
      )
    }
  }

  const handleRemoveMember = async () => {
    if (!memberToRemove) return

    try {
      await removeMemberMutation.mutateAsync({ memberDn: memberToRemove, baseDn: currentBase || undefined })
      toast.success(`Removed member from the group`)
      setMemberToRemove(null)
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to remove member'
      )
    }
  }

  // UNIX member (UID) handlers
  const handleAddMemberUid = async (data: AddMemberUidFormData) => {
    try {
      await addMemberUidMutation.mutateAsync(data.uid)
      toast.success(`Added ${data.uid} to the group`)
      setShowAddMemberUidDialog(false)
      addMemberUidForm.reset()
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to add member'
      )
    }
  }

  const handleRemoveMemberUid = async () => {
    if (!memberUidToRemove) return

    try {
      await removeMemberUidMutation.mutateAsync(memberUidToRemove)
      toast.success(`Removed ${memberUidToRemove} from the group`)
      setMemberUidToRemove(null)
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to remove member'
      )
    }
  }

  // Extract CN from DN for display
  const extractCnFromDn = (dn: string): string => {
    const match = dn.match(/^(?:cn|uid)=([^,]+)/i)
    return match ? match[1] : dn
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
              <p>Failed to load mixed group</p>
              <div className="flex items-center justify-center gap-2 mt-4">
                <Button variant="outline" size="sm" onClick={() => refetch()}>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Retry
                </Button>
                <Button variant="outline" size="sm" asChild>
                  <Link to={PLUGIN_ROUTES.POSIX.MIXED_GROUPS}>
                    <ArrowLeft className="h-4 w-4 mr-2" />
                    Back to Mixed Groups
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
            <Link to={PLUGIN_ROUTES.POSIX.MIXED_GROUPS}>
              <ArrowLeft className="h-5 w-5" />
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Layers className="h-6 w-6" />
              {group.cn}
            </h1>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>GID: {group.gidNumber}</span>
              <span>•</span>
              <Badge variant="outline">Mixed Group</Badge>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button
            variant="destructive"
            onClick={() => setShowDeleteDialog(true)}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </Button>
        </div>
      </div>

      {/* Group Details */}
      <Card>
        <CardHeader>
          <CardTitle>Group Details</CardTitle>
          <CardDescription>
            Edit group properties and system trust settings
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...editForm}>
            <form
              onSubmit={editForm.handleSubmit(handleUpdate)}
              className="space-y-6"
            >
              <FormField
                control={editForm.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Description</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Enter group description"
                        {...field}
                        value={field.value ?? ''}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <TrustModeSection control={editForm.control} />

              <div className="flex justify-end">
                <Button
                  type="submit"
                  disabled={updateMutation.isPending}
                >
                  {updateMutation.isPending ? (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="h-4 w-4 mr-2" />
                      Save Changes
                    </>
                  )}
                </Button>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>

      {/* Members Tabs */}
      <Card>
        <CardHeader>
          <CardTitle>Group Members</CardTitle>
          <CardDescription>
            Manage both LDAP members (DNs) and UNIX members (UIDs)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="ldap" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="ldap" className="flex items-center gap-2">
                <Users className="h-4 w-4" />
                LDAP Members ({group.member?.length ?? 0})
              </TabsTrigger>
              <TabsTrigger value="unix" className="flex items-center gap-2">
                <UserPlus className="h-4 w-4" />
                UNIX Members ({group.memberUid?.length ?? 0})
              </TabsTrigger>
            </TabsList>

            {/* LDAP Members Tab */}
            <TabsContent value="ldap" className="space-y-4">
              <div className="flex justify-between items-center">
                <p className="text-sm text-muted-foreground">
                  LDAP members are stored as Distinguished Names (DNs) in the <code>member</code> attribute.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowAddMemberDialog(true)}
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add LDAP Member
                </Button>
              </div>

              {group.member && group.member.length > 0 ? (
                <div className="border rounded-md">
                  <div className="divide-y">
                    {group.member.map((dn) => (
                      <div
                        key={dn}
                        className="flex items-center justify-between px-4 py-3"
                      >
                        <div>
                          <p className="font-medium">{extractCnFromDn(dn)}</p>
                          <p className="text-sm text-muted-foreground truncate max-w-md">
                            {dn}
                          </p>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setMemberToRemove(dn)}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground border rounded-md">
                  No LDAP members
                </div>
              )}
            </TabsContent>

            {/* UNIX Members Tab */}
            <TabsContent value="unix" className="space-y-4">
              <div className="flex justify-between items-center">
                <p className="text-sm text-muted-foreground">
                  UNIX members are stored as UIDs in the <code>memberUid</code> attribute.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowAddMemberUidDialog(true)}
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add UNIX Member
                </Button>
              </div>

              {group.memberUid && group.memberUid.length > 0 ? (
                <div className="border rounded-md">
                  <div className="divide-y">
                    {group.memberUid.map((uid) => (
                      <div
                        key={uid}
                        className="flex items-center justify-between px-4 py-3"
                      >
                        <span className="font-medium">{uid}</span>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setMemberUidToRemove(uid)}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground border rounded-md">
                  No UNIX members
                </div>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Delete Group Dialog */}
      <DeleteDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        title="Delete Mixed Group"
        description={`Are you sure you want to delete the mixed group "${cn}"? This will remove the group from both LDAP and POSIX. This action cannot be undone.`}
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
      />

      {/* Add LDAP Member Dialog */}
      <Dialog open={showAddMemberDialog} onOpenChange={setShowAddMemberDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add LDAP Member</DialogTitle>
            <DialogDescription>
              Add a member by their Distinguished Name (DN)
            </DialogDescription>
          </DialogHeader>
          <Form {...addMemberForm}>
            <form onSubmit={addMemberForm.handleSubmit(handleAddMember)}>
              <FormField
                control={addMemberForm.control}
                name="memberDn"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Member DN</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="uid=jsmith,ou=people,dc=example,dc=com"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <DialogFooter className="mt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowAddMemberDialog(false)}
                >
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

      {/* Add UNIX Member Dialog */}
      <Dialog open={showAddMemberUidDialog} onOpenChange={setShowAddMemberUidDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add UNIX Member</DialogTitle>
            <DialogDescription>
              Add a member by their UNIX username (UID)
            </DialogDescription>
          </DialogHeader>
          <Form {...addMemberUidForm}>
            <form onSubmit={addMemberUidForm.handleSubmit(handleAddMemberUid)}>
              <FormField
                control={addMemberUidForm.control}
                name="uid"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>User ID (UID)</FormLabel>
                    <FormControl>
                      <Input placeholder="jsmith" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <DialogFooter className="mt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowAddMemberUidDialog(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={addMemberUidMutation.isPending}>
                  {addMemberUidMutation.isPending ? 'Adding...' : 'Add Member'}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      {/* Remove LDAP Member Dialog */}
      <DeleteDialog
        open={!!memberToRemove}
        onOpenChange={(open) => !open && setMemberToRemove(null)}
        title="Remove LDAP Member"
        description={`Are you sure you want to remove "${memberToRemove ? extractCnFromDn(memberToRemove) : ''}" from this group?`}
        onConfirm={handleRemoveMember}
        isLoading={removeMemberMutation.isPending}
        confirmText="Remove"
      />

      {/* Remove UNIX Member Dialog */}
      <DeleteDialog
        open={!!memberUidToRemove}
        onOpenChange={(open) => !open && setMemberUidToRemove(null)}
        title="Remove UNIX Member"
        description={`Are you sure you want to remove "${memberUidToRemove}" from this group?`}
        onConfirm={handleRemoveMemberUid}
        isLoading={removeMemberUidMutation.isPending}
        confirmText="Remove"
      />
    </div>
  )
}
