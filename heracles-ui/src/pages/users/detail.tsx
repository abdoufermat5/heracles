import { useParams, useNavigate, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { Save, ArrowLeft, Key, Trash2, UsersRound, Lock, Unlock, Shield, MoreHorizontal } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
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
import { PageHeader, DetailPageSkeleton, ErrorDisplay, LoadingSpinner, ConfirmDialog, PasswordRequirements, DataTable, SortableHeader, type ColumnDef } from '@/components/common'
import { PosixUserTab } from '@/components/plugins/posix'
import { SSHUserTab } from '@/components/plugins/ssh'
import { MailUserTab } from '@/components/plugins/mail'
import { EntityPermissionsTab } from '@/components/acl'
import { useUser, useUpdateUser, useDeleteUser, useSetUserPassword, useUserLockStatus, useLockUser, useUnlockUser } from '@/hooks'
import { usePluginStore, PLUGIN_NAMES, useRecentStore } from '@/stores'
import { userUpdateSchema, setPasswordSchema, type UserUpdateFormData, type SetPasswordFormData } from '@/lib/schemas'
import { AppError } from '@/lib/errors'
import { groupsApi } from '@/lib/api'
import { ROUTES } from '@/config/constants'

interface UserGroupRow {
  dn: string
  name: string
  type: string
  description: string
}

export function UserDetailPage() {
  const { uid } = useParams<{ uid: string }>()
  const navigate = useNavigate()
  const [showPasswordDialog, setShowPasswordDialog] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [showAddGroupDialog, setShowAddGroupDialog] = useState(false)
  const [groupToAdd, setGroupToAdd] = useState('')
  const addRecentItem = useRecentStore((state) => state.addItem)

  const { data: user, isLoading, error, refetch } = useUser(uid!)
  const { data: lockStatus } = useUserLockStatus(uid!)
  const updateMutation = useUpdateUser(uid!)
  const deleteMutation = useDeleteUser()
  const setPasswordMutation = useSetUserPassword(uid!)
  const lockMutation = useLockUser(uid!)
  const unlockMutation = useUnlockUser(uid!)
  const addGroupMutation = useMutation({
    mutationFn: (cn: string) => groupsApi.addMember(cn, uid!),
    onSuccess: (_, cn) => {
      toast.success(`Added "${user?.uid}" to "${cn}"`)
      setShowAddGroupDialog(false)
      setGroupToAdd('')
      refetch()
    },
    onError: (error) => {
      AppError.toastError(error, 'Failed to add user to group')
    },
  })

  // Check plugin enabled states
  const plugins = usePluginStore((state) => state.plugins)
  const isPluginEnabled = (name: string) => {
    if (!plugins || plugins.length === 0) return true
    const plugin = plugins.find((p) => p.name === name)
    return plugin?.enabled ?? true
  }
  const isPosixEnabled = isPluginEnabled(PLUGIN_NAMES.POSIX)
  const isSSHEnabled = isPluginEnabled(PLUGIN_NAMES.SSH)
  const isMailEnabled = isPluginEnabled(PLUGIN_NAMES.MAIL)

  useEffect(() => {
    if (!user) return
    addRecentItem({
      id: user.uid,
      label: user.displayName ? `${user.displayName} (${user.uid})` : user.uid,
      href: ROUTES.USER_DETAIL.replace(':uid', user.uid),
      type: 'user',
      description: user.mail || user.cn,
    })
  }, [addRecentItem, user])

  const form = useForm<UserUpdateFormData>({
    resolver: zodResolver(userUpdateSchema),
    values: user ? {
      givenName: user.givenName,
      sn: user.sn,
      mail: user.mail || '',
      telephoneNumber: user.telephoneNumber || '',
      title: user.title || '',
      description: user.description || '',
    } : undefined,
  })

  const passwordForm = useForm<SetPasswordFormData>({
    resolver: zodResolver(setPasswordSchema),
    defaultValues: { password: '', confirmPassword: '' },
  })

  const groupRows = useMemo<UserGroupRow[]>(() => {
    if (!user?.memberOf?.length) return []
    return user.memberOf.map((groupDn) => {
      const match = groupDn.match(/^cn=([^,]+)/i)
      return {
        dn: groupDn,
        name: match ? match[1] : groupDn,
        type: 'LDAP',
        description: groupDn,
      }
    })
  }, [user])

  const groupColumns = useMemo<ColumnDef<UserGroupRow>[]>(
    () => [
      {
        accessorKey: 'name',
        header: ({ column }) => (
          <SortableHeader column={column}>Group Name</SortableHeader>
        ),
        cell: ({ row }) => (
          <Link
            to={ROUTES.GROUP_DETAIL.replace(':cn', row.original.name)}
            className="font-medium text-primary hover:underline"
          >
            {row.original.name}
          </Link>
        ),
      },
      {
        accessorKey: 'type',
        header: ({ column }) => (
          <SortableHeader column={column}>Type</SortableHeader>
        ),
        cell: ({ row }) => (
          <Badge variant="outline">{row.original.type}</Badge>
        ),
      },
      {
        accessorKey: 'description',
        header: 'Description',
        cell: ({ row }) => (
          <span className="text-muted-foreground truncate block max-w-[300px]">
            {row.original.description}
          </span>
        ),
      },
    ],
    []
  )

  if (isLoading) {
    return <DetailPageSkeleton />
  }

  if (error || !user) {
    return <ErrorDisplay message={error?.message || 'User not found'} onRetry={() => refetch()} />
  }

  const onSubmit = async (data: UserUpdateFormData) => {
    try {
      // Convert empty strings to undefined for optional fields
      // This ensures LDAP deletes the attribute rather than setting it to empty
      const cleanedData = {
        ...data,
        mail: data.mail || undefined,
        telephoneNumber: data.telephoneNumber || undefined,
        title: data.title || undefined,
        description: data.description || undefined,
      }
      await updateMutation.mutateAsync(cleanedData)
      toast.success('User updated successfully')
    } catch (error) {
      AppError.toastError(error, 'Failed to update user')
    }
  }

  const onSetPassword = async (data: SetPasswordFormData) => {
    try {
      await setPasswordMutation.mutateAsync({ password: data.password })
      toast.success('Password updated successfully')
      setShowPasswordDialog(false)
      passwordForm.reset()
    } catch (error) {
      AppError.toastError(error, 'Failed to set password')
    }
  }

  const onDelete = async () => {
    try {
      await deleteMutation.mutateAsync(uid!)
      toast.success(`User "${uid}" deleted successfully`)
      navigate(ROUTES.USERS)
    } catch (error) {
      AppError.toastError(error, 'Failed to delete user')
    }
  }

  const onLockUser = async () => {
    try {
      await lockMutation.mutateAsync()
      toast.success(`User "${uid}" has been locked`)
    } catch (error) {
      AppError.toastError(error, 'Failed to lock user')
    }
  }

  const onUnlockUser = async () => {
    try {
      await unlockMutation.mutateAsync()
      toast.success(`User "${uid}" has been unlocked`)
    } catch (error) {
      AppError.toastError(error, 'Failed to unlock user')
    }
  }

  const onAddGroup = async () => {
    const cn = groupToAdd.trim()
    if (!cn) return
    await addGroupMutation.mutateAsync(cn)
  }

  const isLocked = lockStatus?.locked ?? false
  const parentDn = user.dn.split(',').slice(1).join(',')

  return (
    <div>
      <PageHeader
        title={
          <span className="flex items-center gap-2">
            {user.displayName || `${user.givenName} ${user.sn}`}
            {isLocked && (
              <Badge variant="destructive" className="ml-2">
                <Lock className="h-3 w-3 mr-1" />
                Locked
              </Badge>
            )}
          </span>
        }
        description={`@${user.uid}`}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate(ROUTES.USERS)}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline">
                  <MoreHorizontal className="mr-2 h-4 w-4" />
                  Actions
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  onClick={isLocked ? onUnlockUser : onLockUser}
                  disabled={lockMutation.isPending || unlockMutation.isPending}
                >
                  {isLocked ? (
                    <Unlock className="mr-2 h-4 w-4" />
                  ) : (
                    <Lock className="mr-2 h-4 w-4" />
                  )}
                  {isLocked ? 'Unlock user' : 'Lock user'}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setShowPasswordDialog(true)}>
                  <Key className="mr-2 h-4 w-4" />
                  Set password
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  className="text-destructive focus:text-destructive"
                  onClick={() => setShowDeleteDialog(true)}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete user
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        }
      />

      <Tabs defaultValue="general" className="space-y-6">
        <TabsList>
          <TabsTrigger value="general">General</TabsTrigger>
          {isPosixEnabled && <TabsTrigger value="posix">Unix Account</TabsTrigger>}
          {isSSHEnabled && <TabsTrigger value="ssh">SSH Keys</TabsTrigger>}
          {isMailEnabled && <TabsTrigger value="mail">Mail</TabsTrigger>}
          <TabsTrigger value="groups">Groups</TabsTrigger>
          <TabsTrigger value="permissions">
            <Shield className="mr-1 h-3.5 w-3.5" />
            Permissions
          </TabsTrigger>
        </TabsList>

        <TabsContent value="general">
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                  <Card>
                    <CardHeader>
                      <CardTitle>Basic Information</CardTitle>
                    </CardHeader>
                    <CardContent className="grid gap-4 md:grid-cols-2">
                      <div>
                        <Label>Username</Label>
                        <Input value={user.uid} disabled className="mt-2" />
                      </div>

                      <FormField
                        control={form.control}
                        name="mail"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Email</FormLabel>
                            <FormControl>
                              <Input type="email" {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />

                      <FormField
                        control={form.control}
                        name="givenName"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>First Name *</FormLabel>
                            <FormControl>
                              <Input {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />

                      <FormField
                        control={form.control}
                        name="sn"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Last Name *</FormLabel>
                            <FormControl>
                              <Input {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />

                      <FormField
                        control={form.control}
                        name="telephoneNumber"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Phone</FormLabel>
                            <FormControl>
                              <Input {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />

                      <FormField
                        control={form.control}
                        name="title"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Job Title</FormLabel>
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
                    <p className="font-mono text-xs break-all">{user.dn}</p>
                  </div>
                  {parentDn && (
                    <div>
                      <span className="text-muted-foreground">Parent OU:</span>
                      <p className="font-mono text-xs break-all">{parentDn}</p>
                    </div>
                  )}
                  {user.entryUUID && (
                    <div>
                      <span className="text-muted-foreground">Entry UUID:</span>
                      <p className="font-mono text-xs break-all">{user.entryUUID}</p>
                    </div>
                  )}
                  {user.createTimestamp && (
                    <div>
                      <span className="text-muted-foreground">Created:</span>
                      <p className="text-xs">{new Date(user.createTimestamp).toLocaleString()}</p>
                    </div>
                  )}
                  {user.modifyTimestamp && (
                    <div>
                      <span className="text-muted-foreground">Modified:</span>
                      <p className="text-xs">{new Date(user.modifyTimestamp).toLocaleString()}</p>
                    </div>
                  )}
                  {user.objectClass && user.objectClass.length > 0 && (
                    <div>
                      <span className="text-muted-foreground">Object Classes:</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {user.objectClass.map((oc) => (
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

        {isPosixEnabled && (
          <TabsContent value="posix" className="max-w-4xl">
            <div className="max-w-4xl">
              <PosixUserTab 
                uid={user.uid} 
                displayName={user.displayName || `${user.givenName} ${user.sn}`} 
              />
            </div>
          </TabsContent>
        )}

        {isSSHEnabled && (
          <TabsContent value="ssh" className="max-w-4xl">
            <div className="max-w-4xl">
              <SSHUserTab 
                uid={user.uid} 
                displayName={user.displayName || `${user.givenName} ${user.sn}`} 
              />
            </div>
          </TabsContent>
        )}

        {isMailEnabled && (
          <TabsContent value="mail" className="max-w-4xl">
            <div className="max-w-4xl">
              <MailUserTab 
                uid={user.uid} 
                displayName={user.displayName || `${user.givenName} ${user.sn}`} 
              />
            </div>
          </TabsContent>
        )}

        <TabsContent value="groups" className="max-w-4xl">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="flex items-center gap-2">
                <UsersRound className="h-5 w-5" />
                <h3 className="text-base font-semibold">Group Memberships</h3>
              </div>
              <p className="text-sm text-muted-foreground">
                Groups this user belongs to
              </p>
            </div>
            <Button variant="outline" onClick={() => setShowAddGroupDialog(true)}>
              <UsersRound className="mr-2 h-4 w-4" />
              Add to Group
            </Button>
          </div>

          <DataTable
            columns={groupColumns}
            data={groupRows}
            getRowId={(row) => row.dn}
            emptyMessage="No group memberships found"
            emptyDescription="Add the user to a group to get started"
            enableSearch
            searchPlaceholder="Search groups..."
            searchColumn="name"
            enablePagination
            defaultPageSize={10}
            enableColumnVisibility
            enableExport
            exportFilename={`user-${user.uid}-groups`}
          />
        </TabsContent>

        <TabsContent value="permissions" className="max-w-4xl">
          <EntityPermissionsTab
            subjectDn={user.dn}
            entityLabel={user.displayName || `${user.givenName} ${user.sn}`}
          />
        </TabsContent>
      </Tabs>

      {/* Set Password Dialog */}
      <Dialog open={showPasswordDialog} onOpenChange={setShowPasswordDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Set Password</DialogTitle>
            <DialogDescription>Set a new password for {user.uid}</DialogDescription>
          </DialogHeader>
          <form onSubmit={passwordForm.handleSubmit(onSetPassword)}>
            <div className="space-y-4 py-4">
              <PasswordRequirements />
              <div className="space-y-2">
                <Label>New Password</Label>
                <Input
                  type="password"
                  {...passwordForm.register('password')}
                />
                {passwordForm.formState.errors.password && (
                  <p className="text-sm text-destructive">
                    {passwordForm.formState.errors.password.message}
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <Label>Confirm Password</Label>
                <Input
                  type="password"
                  {...passwordForm.register('confirmPassword')}
                />
                {passwordForm.formState.errors.confirmPassword && (
                  <p className="text-sm text-destructive">
                    {passwordForm.formState.errors.confirmPassword.message}
                  </p>
                )}
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowPasswordDialog(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={setPasswordMutation.isPending}>
                {setPasswordMutation.isPending ? 'Setting...' : 'Set Password'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Add to Group Dialog */}
      <Dialog open={showAddGroupDialog} onOpenChange={setShowAddGroupDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add to Group</DialogTitle>
            <DialogDescription>
              Enter the group name (CN) to add {user.uid} to.
            </DialogDescription>
          </DialogHeader>
          <form
            onSubmit={(event) => {
              event.preventDefault()
              onAddGroup()
            }}
          >
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Group Name (CN)</Label>
                <Input
                  value={groupToAdd}
                  onChange={(event) => setGroupToAdd(event.target.value)}
                  placeholder="e.g. admins"
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowAddGroupDialog(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={addGroupMutation.isPending || !groupToAdd.trim()}>
                {addGroupMutation.isPending ? 'Adding...' : 'Add to Group'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        title="Delete User"
        description={`Are you sure you want to delete user "${uid}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={onDelete}
        isLoading={deleteMutation.isPending}
      />
    </div>
  )
}
