import { useParams, useNavigate, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { Save, ArrowLeft, Key, Trash2, UsersRound, Lock, Unlock } from 'lucide-react'
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
import { PosixUserTab } from '@/components/plugins/posix'
import { SSHUserTab } from '@/components/plugins/ssh'
import { useUser, useUpdateUser, useDeleteUser, useSetUserPassword, useUserLockStatus, useLockUser, useUnlockUser } from '@/hooks'
import { userUpdateSchema, setPasswordSchema, type UserUpdateFormData, type SetPasswordFormData } from '@/lib/schemas'
import { ROUTES } from '@/config/constants'

export function UserDetailPage() {
  const { uid } = useParams<{ uid: string }>()
  const navigate = useNavigate()
  const [showPasswordDialog, setShowPasswordDialog] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)

  const { data: user, isLoading, error, refetch } = useUser(uid!)
  const { data: lockStatus } = useUserLockStatus(uid!)
  const updateMutation = useUpdateUser(uid!)
  const deleteMutation = useDeleteUser()
  const setPasswordMutation = useSetUserPassword(uid!)
  const lockMutation = useLockUser(uid!)
  const unlockMutation = useUnlockUser(uid!)

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

  if (isLoading) {
    return <LoadingPage message="Loading user..." />
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
      toast.error(error instanceof Error ? error.message : 'Failed to update user')
    }
  }

  const onSetPassword = async (data: SetPasswordFormData) => {
    try {
      await setPasswordMutation.mutateAsync({ password: data.password })
      toast.success('Password updated successfully')
      setShowPasswordDialog(false)
      passwordForm.reset()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to set password')
    }
  }

  const onDelete = async () => {
    try {
      await deleteMutation.mutateAsync(uid!)
      toast.success(`User "${uid}" deleted successfully`)
      navigate(ROUTES.USERS)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to delete user')
    }
  }

  const onLockUser = async () => {
    try {
      await lockMutation.mutateAsync()
      toast.success(`User "${uid}" has been locked`)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to lock user')
    }
  }

  const onUnlockUser = async () => {
    try {
      await unlockMutation.mutateAsync()
      toast.success(`User "${uid}" has been unlocked`)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to unlock user')
    }
  }

  const isLocked = lockStatus?.locked ?? false

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
        breadcrumbs={[
          { label: 'Users', href: ROUTES.USERS },
          { label: user.uid },
        ]}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate(ROUTES.USERS)}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
            {isLocked ? (
              <Button 
                variant="outline" 
                onClick={onUnlockUser}
                disabled={unlockMutation.isPending}
              >
                {unlockMutation.isPending ? (
                  <LoadingSpinner size="sm" className="mr-2" />
                ) : (
                  <Unlock className="mr-2 h-4 w-4" />
                )}
                Unlock
              </Button>
            ) : (
              <Button 
                variant="outline" 
                onClick={onLockUser}
                disabled={lockMutation.isPending}
              >
                {lockMutation.isPending ? (
                  <LoadingSpinner size="sm" className="mr-2" />
                ) : (
                  <Lock className="mr-2 h-4 w-4" />
                )}
                Lock
              </Button>
            )}
            <Button variant="outline" onClick={() => setShowPasswordDialog(true)}>
              <Key className="mr-2 h-4 w-4" />
              Set Password
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
          <TabsTrigger value="posix">Unix Account</TabsTrigger>
          <TabsTrigger value="ssh">SSH Keys</TabsTrigger>
          <TabsTrigger value="groups">Groups</TabsTrigger>
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

        <TabsContent value="posix">
          <div className="max-w-3xl">
            <PosixUserTab 
              uid={user.uid} 
              displayName={user.displayName || `${user.givenName} ${user.sn}`} 
            />
          </div>
        </TabsContent>

        <TabsContent value="ssh">
          <div className="max-w-4xl">
            <SSHUserTab 
              uid={user.uid} 
              displayName={user.displayName || `${user.givenName} ${user.sn}`} 
            />
          </div>
        </TabsContent>

        <TabsContent value="groups">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <UsersRound className="h-5 w-5" />
                Group Memberships
              </CardTitle>
              <CardDescription>Groups this user belongs to</CardDescription>
            </CardHeader>
            <CardContent>
              {user.memberOf && user.memberOf.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {user.memberOf.map((groupDn) => {
                    // Extract CN from DN (e.g., "cn=admins,ou=groups,..." -> "admins")
                    const cnMatch = groupDn.match(/^cn=([^,]+)/)
                    const groupName = cnMatch ? cnMatch[1] : groupDn
                    return (
                      <Link key={groupDn} to={ROUTES.GROUP_DETAIL.replace(':cn', groupName)}>
                        <Badge variant="secondary" className="cursor-pointer hover:bg-secondary/80">
                          {groupName}
                        </Badge>
                      </Link>
                    )
                  })}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Not a member of any groups</p>
              )}
            </CardContent>
          </Card>
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
