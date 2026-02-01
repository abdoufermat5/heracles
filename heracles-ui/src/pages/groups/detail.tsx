import { useParams, useNavigate, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { Save, ArrowLeft, Trash2, Users, UserPlus, UserMinus } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
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
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { PageHeader, LoadingPage, ErrorDisplay, LoadingSpinner, ConfirmDialog } from '@/components/common'
import { PosixGroupTab } from '@/components/plugins/posix'
import { MailGroupTab } from '@/components/plugins/mail'
import { useGroup, useUpdateGroup, useDeleteGroup, useAddGroupMember, useRemoveGroupMember } from '@/hooks'
import { groupUpdateSchema, type GroupUpdateFormData } from '@/lib/schemas'
import { AppError } from '@/lib/errors'
import { ROUTES } from '@/config/constants'

export function GroupDetailPage() {
  const { cn } = useParams<{ cn: string }>()
  const navigate = useNavigate()
  const [showAddMemberDialog, setShowAddMemberDialog] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [memberToRemove, setMemberToRemove] = useState<string | null>(null)
  const [newMemberUid, setNewMemberUid] = useState('')

  const { data: group, isLoading, error, refetch } = useGroup(cn!)
  const updateMutation = useUpdateGroup(cn!)
  const deleteMutation = useDeleteGroup()
  const addMemberMutation = useAddGroupMember(cn!)
  const removeMemberMutation = useRemoveGroupMember(cn!)

  const form = useForm<GroupUpdateFormData>({
    resolver: zodResolver(groupUpdateSchema),
    values: group ? {
      description: group.description || '',
    } : undefined,
  })

  if (isLoading) {
    return <LoadingPage message="Loading group..." />
  }

  if (error || !group) {
    return <ErrorDisplay message={error?.message || 'Group not found'} onRetry={() => refetch()} />
  }

  const onSubmit = async (data: GroupUpdateFormData) => {
    try {
      await updateMutation.mutateAsync(data)
      toast.success('Group updated successfully')
    } catch (error) {
      AppError.toastError(error, 'Failed to update group')
    }
  }

  const onDelete = async () => {
    try {
      await deleteMutation.mutateAsync(cn!)
      toast.success(`Group "${cn}" deleted successfully`)
      navigate(ROUTES.GROUPS)
    } catch (error) {
      AppError.toastError(error, 'Failed to delete group')
    }
  }

  const onAddMember = async () => {
    if (!newMemberUid.trim()) return
    try {
      await addMemberMutation.mutateAsync(newMemberUid.trim())
      toast.success(`User "${newMemberUid}" added to group`)
      setShowAddMemberDialog(false)
      setNewMemberUid('')
      refetch()
    } catch (error) {
      AppError.toastError(error, 'Failed to add member')
    }
  }

  const onRemoveMember = async () => {
    if (!memberToRemove) return
    try {
      await removeMemberMutation.mutateAsync(memberToRemove)
      toast.success(`User "${memberToRemove}" removed from group`)
      setMemberToRemove(null)
      refetch()
    } catch (error) {
      AppError.toastError(error, 'Failed to remove member')
    }
  }

  return (
    <div>
      <PageHeader
        title={group.cn}
        description={group.description || 'No description'}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate(ROUTES.GROUPS)}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
            <Button variant="destructive" onClick={() => setShowDeleteDialog(true)}>
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </Button>
          </div>
        }
      />

      <Tabs defaultValue="general" className="space-y-6">
        <TabsList>
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="members">Members</TabsTrigger>
          <TabsTrigger value="posix">POSIX</TabsTrigger>
          <TabsTrigger value="mail">Mail</TabsTrigger>
        </TabsList>

        <TabsContent value="general">
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                  <Card>
                    <CardHeader>
                      <CardTitle>Group Information</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div>
                        <Label>Group Name</Label>
                        <Input value={group.cn} disabled className="mt-2" />
                      </div>

                      <FormField
                        control={form.control}
                        name="description"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Description</FormLabel>
                            <FormControl>
                              <Input {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    </CardContent>
                  </Card>

                  <div className="flex justify-end">
                    <Button type="submit" disabled={updateMutation.isPending}>
                      {updateMutation.isPending ? (
                        <>
                          <LoadingSpinner size="sm" className="mr-2" />
                          Saving...
                        </>
                      ) : (
                        <>
                          <Save className="mr-2 h-4 w-4" />
                          Save Changes
                        </>
                      )}
                    </Button>
                  </div>
                </form>
              </Form>
            </div>

            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>LDAP Details</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">DN:</span>
                    <p className="font-mono text-xs break-all">{group.dn}</p>
                  </div>
                  {group.objectClass && group.objectClass.length > 0 && (
                    <div>
                      <span className="text-muted-foreground">Object Classes:</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {group.objectClass.map((oc) => (
                          <Badge key={oc} variant="outline" className="text-xs">
                            {oc}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="members">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-5 w-5" />
                  Members
                  <Badge variant="secondary">{group.members?.length || 0}</Badge>
                </CardTitle>
                <Button size="sm" onClick={() => setShowAddMemberDialog(true)}>
                  <UserPlus className="mr-1 h-4 w-4" />
                  Add Member
                </Button>
              </div>
              <CardDescription>Users in this group</CardDescription>
            </CardHeader>
            <CardContent>
              {group.members && group.members.length > 0 ? (
                <div className="space-y-2">
                  {group.members.map((memberDn) => {
                    // Extract uid or cn from DN
                    const uidMatch = memberDn.match(/^uid=([^,]+)/)
                    const cnMatch = memberDn.match(/^cn=([^,]+)/)
                    const memberName = uidMatch ? uidMatch[1] : (cnMatch ? cnMatch[1] : memberDn)
                    const isUser = uidMatch !== null
                    return (
                      <div key={memberDn} className="flex items-center justify-between p-2 rounded-md hover:bg-muted">
                        {isUser ? (
                          <Link
                            to={ROUTES.USER_DETAIL.replace(':uid', memberName)}
                            className="text-sm font-medium text-primary hover:underline"
                          >
                            {memberName}
                          </Link>
                        ) : (
                          <span className="text-sm font-medium">{memberName}</span>
                        )}
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-destructive hover:text-destructive"
                          onClick={() => setMemberToRemove(memberDn)}
                        >
                          <UserMinus className="h-4 w-4" />
                        </Button>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground py-8 text-center">No members in this group</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="posix">
          <div className="max-w-3xl">
            <PosixGroupTab cn={group.cn} />
          </div>
        </TabsContent>

        <TabsContent value="mail">
          <div className="max-w-4xl">
            <MailGroupTab cn={group.cn} displayName={group.cn} />
          </div>
        </TabsContent>
      </Tabs>

      {/* Add Member Dialog */}
      <Dialog open={showAddMemberDialog} onOpenChange={setShowAddMemberDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Member</DialogTitle>
            <DialogDescription>Add a user to the {group.cn} group</DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label>Username</Label>
            <Input
              value={newMemberUid}
              onChange={(e) => setNewMemberUid(e.target.value)}
              placeholder="Enter username"
              className="mt-2"
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setShowAddMemberDialog(false)}>
              Cancel
            </Button>
            <Button onClick={onAddMember} disabled={addMemberMutation.isPending || !newMemberUid.trim()}>
              {addMemberMutation.isPending ? 'Adding...' : 'Add Member'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Remove Member Confirmation */}
      <ConfirmDialog
        open={!!memberToRemove}
        onOpenChange={(open) => !open && setMemberToRemove(null)}
        title="Remove Member"
        description={`Are you sure you want to remove "${memberToRemove}" from this group?`}
        confirmLabel="Remove"
        variant="destructive"
        onConfirm={onRemoveMember}
        isLoading={removeMemberMutation.isPending}
      />

      {/* Delete Group Confirmation */}
      <ConfirmDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        title="Delete Group"
        description={`Are you sure you want to delete group "${cn}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={onDelete}
        isLoading={deleteMutation.isPending}
      />
    </div>
  )
}
