/**
 * Sudo Roles List Page
 * 
 * Lists all sudo roles and provides CRUD operations.
 */

import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Plus, Shield, Trash2, Edit, RefreshCw, Search, Terminal, Users, Server } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
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
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import { Checkbox } from '@/components/ui/checkbox'

import { 
  useSudoRoles, 
  useCreateSudoRole, 
  useDeleteSudoRole 
} from '@/hooks/use-sudo'
import type { SudoRoleData } from '@/types/sudo'
import { SUDO_OPTIONS, COMMON_COMMANDS } from '@/types/sudo'

// Form schema for creating a new sudo role
const createRoleSchema = z.object({
  cn: z.string()
    .min(1, 'Role name is required')
    .max(64, 'Role name must be at most 64 characters')
    .regex(/^[a-z][a-z0-9_-]*$/i, 'Role name must start with a letter and contain only letters, numbers, underscores, and hyphens'),
  description: z.string().max(255).optional(),
  sudoUser: z.string().optional(),
  sudoHost: z.string().optional(),
  sudoCommand: z.string().optional(),
  sudoRunAsUser: z.string().optional(),
  sudoRunAsGroup: z.string().optional(),
  sudoOption: z.array(z.string()).optional(),
  sudoOrder: z.number().min(0).optional(),
})

type CreateRoleFormData = z.infer<typeof createRoleSchema>

// Helper to parse comma-separated string to array
function parseStringToArray(value: string | undefined): string[] {
  if (!value) return []
  return value.split(',').map(s => s.trim()).filter(s => s.length > 0)
}

// Helper to display array as badge list
function ArrayBadges({ items, max = 3, variant = 'secondary' }: { 
  items: string[], 
  max?: number, 
  variant?: 'default' | 'secondary' | 'outline' | 'destructive' 
}) {
  if (items.length === 0) return <span className="text-muted-foreground">-</span>
  
  const displayed = items.slice(0, max)
  const remaining = items.length - max

  return (
    <div className="flex flex-wrap gap-1">
      {displayed.map((item, i) => (
        <Badge key={i} variant={variant} className="text-xs">
          {item}
        </Badge>
      ))}
      {remaining > 0 && (
        <Badge variant="outline" className="text-xs">
          +{remaining}
        </Badge>
      )}
    </div>
  )
}

export default function SudoRolesPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [searchQuery, setSearchQuery] = useState('')
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [roleToDelete, setRoleToDelete] = useState<SudoRoleData | null>(null)

  // Open create dialog if ?create=true is in URL
  useEffect(() => {
    if (searchParams.get('create') === 'true') {
      setShowCreateDialog(true)
      searchParams.delete('create')
      setSearchParams(searchParams, { replace: true })
    }
  }, [searchParams, setSearchParams])

  const { data: rolesResponse, isLoading, error, refetch } = useSudoRoles()
  const createMutation = useCreateSudoRole()
  const deleteMutation = useDeleteSudoRole()

  const form = useForm<CreateRoleFormData>({
    resolver: zodResolver(createRoleSchema),
    defaultValues: {
      cn: '',
      description: '',
      sudoUser: '',
      sudoHost: 'ALL',
      sudoCommand: 'ALL',
      sudoRunAsUser: 'ALL',
      sudoRunAsGroup: '',
      sudoOption: [],
      sudoOrder: 0,
    },
  })

  // Filter roles by search query (exclude defaults)
  const filteredRoles = rolesResponse?.roles?.filter((role) => {
    if (role.isDefault) return false // Hide defaults from main list
    const matchesSearch = 
      role.cn.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (role.description?.toLowerCase().includes(searchQuery.toLowerCase()))
    return matchesSearch
  }) ?? []

  const handleCreate = async (data: CreateRoleFormData) => {
    try {
      await createMutation.mutateAsync({
        cn: data.cn,
        description: data.description,
        sudoUser: parseStringToArray(data.sudoUser),
        sudoHost: parseStringToArray(data.sudoHost),
        sudoCommand: parseStringToArray(data.sudoCommand),
        sudoRunAsUser: parseStringToArray(data.sudoRunAsUser),
        sudoRunAsGroup: parseStringToArray(data.sudoRunAsGroup),
        sudoOption: data.sudoOption,
        sudoOrder: data.sudoOrder,
      })
      toast.success(`Sudo role "${data.cn}" created successfully`)
      setShowCreateDialog(false)
      form.reset()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to create sudo role')
    }
  }

  const handleDelete = async () => {
    if (!roleToDelete) return

    try {
      await deleteMutation.mutateAsync(roleToDelete.cn)
      toast.success(`Sudo role "${roleToDelete.cn}" deleted successfully`)
      setRoleToDelete(null)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to delete sudo role')
    }
  }

  if (isLoading) {
    return (
      <div className="container mx-auto py-6 space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-32" />
        </div>
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container mx-auto py-6">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-8 text-destructive">
              <p>Failed to load sudo roles</p>
              <Button variant="outline" size="sm" className="mt-4" onClick={() => refetch()}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry
              </Button>
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
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Shield className="h-6 w-6" />
            Sudo Roles
          </h1>
          <p className="text-muted-foreground">
            Manage sudo rules for privilege escalation on UNIX/Linux systems
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Create Role
        </Button>
      </div>

      {/* Search and Stats */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search roles..."
            className="pl-9"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <Badge variant="secondary">
          {filteredRoles.length} role{filteredRoles.length !== 1 ? 's' : ''}
        </Badge>
        <Button variant="outline" size="icon" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* Roles Table */}
      <Card>
        <CardHeader>
          <CardTitle>Sudo Roles</CardTitle>
          <CardDescription>
            Configure who can run what commands with elevated privileges
          </CardDescription>
        </CardHeader>
        <CardContent>
          {filteredRoles.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {searchQuery ? 'No roles match your search' : 'No sudo roles found. Create one to get started.'}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Role Name</TableHead>
                  <TableHead>
                    <div className="flex items-center gap-1">
                      <Users className="h-4 w-4" />
                      Users
                    </div>
                  </TableHead>
                  <TableHead>
                    <div className="flex items-center gap-1">
                      <Server className="h-4 w-4" />
                      Hosts
                    </div>
                  </TableHead>
                  <TableHead>
                    <div className="flex items-center gap-1">
                      <Terminal className="h-4 w-4" />
                      Commands
                    </div>
                  </TableHead>
                  <TableHead>Options</TableHead>
                  <TableHead>Order</TableHead>
                  <TableHead className="w-[100px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredRoles.map((role) => (
                  <TableRow key={role.cn}>
                    <TableCell className="font-medium">
                      <Link 
                        to={`/sudo/roles/${role.cn}`}
                        className="hover:underline text-primary"
                      >
                        {role.cn}
                      </Link>
                      {role.description && (
                        <p className="text-xs text-muted-foreground mt-1">{role.description}</p>
                      )}
                    </TableCell>
                    <TableCell>
                      <ArrayBadges items={role.sudoUser} />
                    </TableCell>
                    <TableCell>
                      <ArrayBadges items={role.sudoHost} variant="outline" />
                    </TableCell>
                    <TableCell>
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <div>
                              <ArrayBadges 
                                items={role.sudoCommand} 
                                variant={role.sudoCommand.includes('ALL') ? 'destructive' : 'default'}
                              />
                            </div>
                          </TooltipTrigger>
                          {role.sudoCommand.length > 3 && (
                            <TooltipContent>
                              <div className="max-w-xs">
                                {role.sudoCommand.join(', ')}
                              </div>
                            </TooltipContent>
                          )}
                        </Tooltip>
                      </TooltipProvider>
                    </TableCell>
                    <TableCell>
                      <ArrayBadges items={role.sudoOption} max={2} />
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{role.sudoOrder}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button variant="ghost" size="icon" asChild>
                          <Link to={`/sudo/roles/${role.cn}`}>
                            <Edit className="h-4 w-4" />
                          </Link>
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setRoleToDelete(role)}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Create Sudo Role</DialogTitle>
            <DialogDescription>
              Define who can run which commands with elevated privileges
            </DialogDescription>
          </DialogHeader>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(handleCreate)} className="space-y-6">
              {/* Basic Info */}
              <div className="space-y-4">
                <h4 className="font-medium text-sm border-b pb-2">Basic Information</h4>
                <div className="grid grid-cols-2 gap-4">
                  <FormField
                    control={form.control}
                    name="cn"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Role Name *</FormLabel>
                        <FormControl>
                          <Input placeholder="webadmins" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="sudoOrder"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Priority Order</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            placeholder="0"
                            {...field}
                            value={field.value ?? 0}
                            onChange={(e) => field.onChange(parseInt(e.target.value) || 0)}
                          />
                        </FormControl>
                        <FormDescription className="text-xs">
                          Higher = higher priority
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
                        <Input placeholder="Web server administrators" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              {/* Who */}
              <div className="space-y-4">
                <h4 className="font-medium text-sm border-b pb-2">Who (Users/Groups)</h4>
                <FormField
                  control={form.control}
                  name="sudoUser"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Sudo Users</FormLabel>
                      <FormControl>
                        <Textarea
                          placeholder="user1, %groupname, ALL"
                          className="h-20"
                          {...field}
                        />
                      </FormControl>
                      <FormDescription>
                        Comma-separated. Use %groupname for groups, ALL for everyone
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              {/* Where */}
              <div className="space-y-4">
                <h4 className="font-medium text-sm border-b pb-2">Where (Hosts)</h4>
                <FormField
                  control={form.control}
                  name="sudoHost"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Sudo Hosts</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="ALL, server1.example.com, 192.168.1.0/24"
                          {...field}
                        />
                      </FormControl>
                      <FormDescription>
                        Comma-separated hostnames, IPs, or ALL
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              {/* What */}
              <div className="space-y-4">
                <h4 className="font-medium text-sm border-b pb-2">What (Commands)</h4>
                <FormField
                  control={form.control}
                  name="sudoCommand"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Allowed Commands</FormLabel>
                      <FormControl>
                        <Textarea
                          placeholder="ALL, /usr/bin/systemctl restart nginx, !/bin/su"
                          className="h-20"
                          {...field}
                        />
                      </FormControl>
                      <FormDescription>
                        Comma-separated commands. Use ! prefix to deny. ALL allows everything.
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <div className="flex flex-wrap gap-2">
                  <span className="text-xs text-muted-foreground">Quick add:</span>
                  {COMMON_COMMANDS.slice(0, 6).map((cmd) => (
                    <Badge
                      key={cmd.value}
                      variant="outline"
                      className="cursor-pointer hover:bg-accent"
                      onClick={() => {
                        const current = form.getValues('sudoCommand') || ''
                        const newValue = current ? `${current}, ${cmd.value}` : cmd.value
                        form.setValue('sudoCommand', newValue)
                      }}
                    >
                      {cmd.label}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* Run As */}
              <div className="space-y-4">
                <h4 className="font-medium text-sm border-b pb-2">Run As</h4>
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
                        <FormDescription className="text-xs">
                          Target user(s) for sudo
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
                        <FormDescription className="text-xs">
                          Target group(s) for sudo
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              </div>

              {/* Options */}
              <div className="space-y-4">
                <h4 className="font-medium text-sm border-b pb-2">Options</h4>
                <FormField
                  control={form.control}
                  name="sudoOption"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Sudo Options</FormLabel>
                      <div className="grid grid-cols-2 gap-3">
                        {SUDO_OPTIONS.map((option) => (
                          <div
                            key={option.value}
                            className="flex items-start space-x-2"
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
                            <div className="grid gap-0.5 leading-none">
                              <label
                                htmlFor={option.value}
                                className="text-sm font-medium cursor-pointer"
                              >
                                {option.label}
                              </label>
                              <p className="text-xs text-muted-foreground">
                                {option.description}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setShowCreateDialog(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? 'Creating...' : 'Create Role'}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={!!roleToDelete} onOpenChange={(open) => !open && setRoleToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Sudo Role</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the sudo role "{roleToDelete?.cn}"?
              This will remove all associated sudo privileges. This action cannot be undone.
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
