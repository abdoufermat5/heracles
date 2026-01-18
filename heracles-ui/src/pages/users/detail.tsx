import { useParams, useNavigate, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { Save, ArrowLeft, Key, Trash2, UsersRound } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
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
import { useUser, useUpdateUser, useDeleteUser, useSetUserPassword } from '@/hooks'
import { userUpdateSchema, setPasswordSchema, type UserUpdateFormData, type SetPasswordFormData } from '@/lib/schemas'
import { ROUTES } from '@/config/constants'

export function UserDetailPage() {
  const { uid } = useParams<{ uid: string }>()
  const navigate = useNavigate()
  const [showPasswordDialog, setShowPasswordDialog] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)

  const { data: user, isLoading, error, refetch } = useUser(uid!)
  const updateMutation = useUpdateUser(uid!)
  const deleteMutation = useDeleteUser()
  const setPasswordMutation = useSetUserPassword(uid!)

  const form = useForm<UserUpdateFormData>({
    resolver: zodResolver(userUpdateSchema),
    values: user ? {
      givenName: user.givenName,
      sn: user.sn,
      mail: user.mail || '',
      telephoneNumber: user.telephoneNumber || '',
      title: user.title || '',
      description: user.description || '',
      uidNumber: user.uidNumber,
      gidNumber: user.gidNumber,
      homeDirectory: user.homeDirectory || '',
      loginShell: user.loginShell || '',
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
      await updateMutation.mutateAsync(data)
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

  return (
    <div>
      <PageHeader
        title={user.displayName || `${user.givenName} ${user.sn}`}
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

              <Card>
                <CardHeader>
                  <CardTitle>POSIX Attributes</CardTitle>
                </CardHeader>
                <CardContent className="grid gap-4 md:grid-cols-2">
                  <FormField
                    control={form.control}
                    name="uidNumber"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>UID Number</FormLabel>
                        <FormControl>
                          <Input type="number" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="gidNumber"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>GID Number</FormLabel>
                        <FormControl>
                          <Input type="number" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="homeDirectory"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Home Directory</FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="loginShell"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Login Shell</FormLabel>
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
