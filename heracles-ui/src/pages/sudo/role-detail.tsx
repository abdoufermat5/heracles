/**
 * Sudo Role Detail Page
 * 
 * View and edit a single sudo role.
 */

import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { 
  ArrowLeft, Shield, Save, Trash2, RefreshCw, 
  Users, Server, Terminal, Settings 
} from 'lucide-react'
import { toast } from 'sonner'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
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
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Separator } from '@/components/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

import {
  useSudoRole,
  useUpdateSudoRole,
  useDeleteSudoRole,
} from '@/hooks/use-sudo'
import { SUDO_OPTIONS, COMMON_COMMANDS } from '@/types/sudo'

// Form schema for editing the role
const editSchema = z.object({
  description: z.string().max(255).optional(),
  sudoUser: z.string().optional(),
  sudoHost: z.string().optional(),
  sudoCommand: z.string().optional(),
  sudoRunAsUser: z.string().optional(),
  sudoRunAsGroup: z.string().optional(),
  sudoOption: z.array(z.string()).optional(),
  sudoOrder: z.number().min(0).optional(),
  sudoNotBefore: z.string().optional(),
  sudoNotAfter: z.string().optional(),
})

type EditFormData = z.infer<typeof editSchema>

// Helper functions
function arrayToString(arr: string[] | undefined): string {
  return arr?.join(', ') ?? ''
}

function stringToArray(str: string | undefined): string[] {
  if (!str) return []
  return str.split(',').map(s => s.trim()).filter(s => s.length > 0)
}

export default function SudoRoleDetailPage() {
  const { cn } = useParams<{ cn: string }>()
  const navigate = useNavigate()

  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)

  const { data: role, isLoading, error, refetch } = useSudoRole(cn!)
  const updateMutation = useUpdateSudoRole()
  const deleteMutation = useDeleteSudoRole()

  const form = useForm<EditFormData>({
    resolver: zodResolver(editSchema),
  })

  // Reset form when role data loads
  useEffect(() => {
    if (role) {
      form.reset({
        description: role.description ?? '',
        sudoUser: arrayToString(role.sudoUser),
        sudoHost: arrayToString(role.sudoHost),
        sudoCommand: arrayToString(role.sudoCommand),
        sudoRunAsUser: arrayToString(role.sudoRunAsUser),
        sudoRunAsGroup: arrayToString(role.sudoRunAsGroup),
        sudoOption: role.sudoOption ?? [],
        sudoOrder: role.sudoOrder ?? 0,
        sudoNotBefore: role.sudoNotBefore ?? '',
        sudoNotAfter: role.sudoNotAfter ?? '',
      })
      setHasChanges(false)
    }
  }, [role, form])

  // Track changes
  useEffect(() => {
    const subscription = form.watch(() => setHasChanges(true))
    return () => subscription.unsubscribe()
  }, [form])

  const handleUpdate = async (data: EditFormData) => {
    try {
      await updateMutation.mutateAsync({
        cn: cn!,
        data: {
          description: data.description || undefined,
          sudoUser: stringToArray(data.sudoUser),
          sudoHost: stringToArray(data.sudoHost),
          sudoCommand: stringToArray(data.sudoCommand),
          sudoRunAsUser: stringToArray(data.sudoRunAsUser),
          sudoRunAsGroup: stringToArray(data.sudoRunAsGroup),
          sudoOption: data.sudoOption,
          sudoOrder: data.sudoOrder,
          sudoNotBefore: data.sudoNotBefore || undefined,
          sudoNotAfter: data.sudoNotAfter || undefined,
        },
      })
      toast.success('Sudo role updated successfully')
      setHasChanges(false)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to update sudo role')
    }
  }

  const handleDelete = async () => {
    try {
      await deleteMutation.mutateAsync(cn!)
      toast.success('Sudo role deleted successfully')
      navigate('/sudo/roles')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to delete sudo role')
    }
  }

  if (isLoading) {
    return (
      <div className="container mx-auto py-6 space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-6 md:grid-cols-2">
          <Card>
            <CardContent className="pt-6 space-y-4">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6 space-y-4">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  if (error || !role) {
    return (
      <div className="container mx-auto py-6">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-8 text-destructive">
              <p>Failed to load sudo role</p>
              <div className="flex items-center justify-center gap-2 mt-4">
                <Button variant="outline" size="sm" onClick={() => refetch()}>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Retry
                </Button>
                <Button variant="outline" size="sm" asChild>
                  <Link to="/sudo/roles">
                    <ArrowLeft className="h-4 w-4 mr-2" />
                    Back to Roles
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
            <Link to="/sudo/roles">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Shield className="h-6 w-6" />
              {role.cn}
            </h1>
            <p className="text-muted-foreground">
              Sudo Role • Priority {role.sudoOrder}
              {role.isDefault && (
                <Badge variant="secondary" className="ml-2">Default</Badge>
              )}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {hasChanges && (
            <Badge variant="outline" className="text-yellow-600">
              Unsaved changes
            </Badge>
          )}
          <Button variant="destructive" onClick={() => setShowDeleteDialog(true)}>
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </Button>
        </div>
      </div>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(handleUpdate)}>
          <Tabs defaultValue="general" className="space-y-6">
            <TabsList>
              <TabsTrigger value="general">
                <Settings className="h-4 w-4 mr-2" />
                General
              </TabsTrigger>
              <TabsTrigger value="access">
                <Users className="h-4 w-4 mr-2" />
                Access Control
              </TabsTrigger>
              <TabsTrigger value="commands">
                <Terminal className="h-4 w-4 mr-2" />
                Commands
              </TabsTrigger>
              <TabsTrigger value="options">
                <Shield className="h-4 w-4 mr-2" />
                Options
              </TabsTrigger>
            </TabsList>

            {/* General Tab */}
            <TabsContent value="general" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Basic Information</CardTitle>
                  <CardDescription>Role identification and priority</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Role Name (cn)</label>
                      <Input value={role.cn} disabled />
                      <p className="text-xs text-muted-foreground">
                        Role name cannot be changed
                      </p>
                    </div>
                    <FormField
                      control={form.control}
                      name="sudoOrder"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Priority Order</FormLabel>
                          <FormControl>
                            <Input
                              type="number"
                              {...field}
                              value={field.value ?? 0}
                              onChange={(e) => field.onChange(parseInt(e.target.value) || 0)}
                            />
                          </FormControl>
                          <FormDescription>
                            Higher number = higher priority
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                  <FormField
                    control={form.control}
                    name="description"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Description</FormLabel>
                        <FormControl>
                          <Input placeholder="Role description" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <Separator />

                  <div className="grid grid-cols-2 gap-4">
                    <FormField
                      control={form.control}
                      name="sudoNotBefore"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Valid From</FormLabel>
                          <FormControl>
                            <Input
                              type="datetime-local"
                              {...field}
                            />
                          </FormControl>
                          <FormDescription>
                            Optional time restriction
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="sudoNotAfter"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Valid Until</FormLabel>
                          <FormControl>
                            <Input
                              type="datetime-local"
                              {...field}
                            />
                          </FormControl>
                          <FormDescription>
                            Optional expiration time
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Access Control Tab */}
            <TabsContent value="access" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Users className="h-5 w-5" />
                    Users & Groups
                  </CardTitle>
                  <CardDescription>Who can use this sudo role</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <FormField
                    control={form.control}
                    name="sudoUser"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Sudo Users</FormLabel>
                        <FormControl>
                          <Textarea
                            placeholder="user1, %groupname, ALL"
                            className="h-24 font-mono"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          Comma-separated list of users or groups (%groupname). Use ALL for everyone.
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <div className="flex flex-wrap gap-2">
                    <span className="text-xs text-muted-foreground mr-2">Current:</span>
                    {role.sudoUser.map((user, i) => (
                      <Badge key={i} variant="secondary">{user}</Badge>
                    ))}
                    {role.sudoUser.length === 0 && (
                      <span className="text-xs text-muted-foreground">None</span>
                    )}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Server className="h-5 w-5" />
                    Hosts
                  </CardTitle>
                  <CardDescription>Where this sudo role applies</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <FormField
                    control={form.control}
                    name="sudoHost"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Sudo Hosts</FormLabel>
                        <FormControl>
                          <Textarea
                            placeholder="ALL, server1.example.com, 192.168.1.0/24"
                            className="h-20 font-mono"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          Comma-separated hostnames, IP addresses, or CIDR ranges. Use ALL for any host.
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <div className="flex flex-wrap gap-2">
                    <span className="text-xs text-muted-foreground mr-2">Current:</span>
                    {role.sudoHost.map((host, i) => (
                      <Badge key={i} variant="outline">{host}</Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Run As</CardTitle>
                  <CardDescription>Target user/group for command execution</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <FormField
                      control={form.control}
                      name="sudoRunAsUser"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Run As User</FormLabel>
                          <FormControl>
                            <Input placeholder="ALL, root" {...field} />
                          </FormControl>
                          <FormDescription>
                            Target user(s) for sudo execution
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="sudoRunAsGroup"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Run As Group</FormLabel>
                          <FormControl>
                            <Input placeholder="root, wheel" {...field} />
                          </FormControl>
                          <FormDescription>
                            Target group(s) for sudo execution
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Commands Tab */}
            <TabsContent value="commands" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Terminal className="h-5 w-5" />
                    Allowed Commands
                  </CardTitle>
                  <CardDescription>Commands this role can execute with sudo</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <FormField
                    control={form.control}
                    name="sudoCommand"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Commands</FormLabel>
                        <FormControl>
                          <Textarea
                            placeholder="ALL, /usr/bin/systemctl restart nginx, !/bin/su"
                            className="h-32 font-mono"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          Comma-separated list of commands with full paths. Use ! prefix to deny. ALL allows everything.
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  <div className="space-y-2">
                    <span className="text-sm font-medium">Quick Add Commands:</span>
                    <div className="flex flex-wrap gap-2">
                      {COMMON_COMMANDS.map((cmd) => (
                        <Badge
                          key={cmd.value}
                          variant="outline"
                          className="cursor-pointer hover:bg-accent"
                          onClick={() => {
                            const current = form.getValues('sudoCommand') || ''
                            const newValue = current ? `${current}, ${cmd.value}` : cmd.value
                            form.setValue('sudoCommand', newValue, { shouldDirty: true })
                          }}
                        >
                          {cmd.label}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  <Separator />

                  <div className="space-y-2">
                    <span className="text-sm font-medium">Current Commands:</span>
                    <div className="flex flex-wrap gap-2">
                      {role.sudoCommand.map((cmd, i) => (
                        <Badge 
                          key={i} 
                          variant={cmd === 'ALL' ? 'destructive' : cmd.startsWith('!') ? 'outline' : 'default'}
                        >
                          {cmd}
                        </Badge>
                      ))}
                      {role.sudoCommand.length === 0 && (
                        <span className="text-muted-foreground">No commands specified</span>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Options Tab */}
            <TabsContent value="options" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="h-5 w-5" />
                    Sudo Options
                  </CardTitle>
                  <CardDescription>Configure sudo behavior for this role</CardDescription>
                </CardHeader>
                <CardContent>
                  <FormField
                    control={form.control}
                    name="sudoOption"
                    render={({ field }) => (
                      <FormItem>
                        <div className="grid grid-cols-2 gap-4">
                          {SUDO_OPTIONS.map((option) => (
                            <div
                              key={option.value}
                              className="flex items-start space-x-3 p-3 rounded-lg border hover:bg-accent/50"
                            >
                              <Checkbox
                                id={option.value}
                                checked={field.value?.includes(option.value)}
                                onCheckedChange={(checked) => {
                                  const current = field.value || []
                                  if (checked) {
                                    field.onChange([...current, option.value])
                                  } else {
                                    field.onChange(current.filter(v => v !== option.value))
                                  }
                                }}
                              />
                              <div className="grid gap-1 leading-none">
                                <label
                                  htmlFor={option.value}
                                  className="text-sm font-medium cursor-pointer"
                                >
                                  {option.label}
                                </label>
                                <p className="text-xs text-muted-foreground">
                                  {option.description}
                                </p>
                                <code className="text-xs bg-muted px-1 rounded">
                                  {option.value}
                                </code>
                              </div>
                            </div>
                          ))}
                        </div>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <Separator className="my-4" />

                  <div className="space-y-2">
                    <span className="text-sm font-medium">Active Options:</span>
                    <div className="flex flex-wrap gap-2">
                      {role.sudoOption.map((opt, i) => (
                        <Badge key={i} variant="secondary">{opt}</Badge>
                      ))}
                      {role.sudoOption.length === 0 && (
                        <span className="text-muted-foreground">No options configured</span>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>

          {/* Save Button - Fixed at bottom */}
          <div className="sticky bottom-4 flex justify-end pt-4">
            <Button 
              type="submit" 
              disabled={updateMutation.isPending || !hasChanges}
              className="shadow-lg"
            >
              <Save className="h-4 w-4 mr-2" />
              {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        </form>
      </Form>

      {/* Delete Confirmation */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Sudo Role</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the sudo role "{role.cn}"?
              This will remove all associated sudo privileges. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete Role'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
