/**
 * Mixed Groups List Page
 * 
 * Lists all MixedGroups (groupOfNames + posixGroup) and provides CRUD operations.
 */

import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Plus, Layers, Trash2, Edit, RefreshCw, Search, Users, Terminal } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Checkbox } from '@/components/ui/checkbox'
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import { useMixedGroups, useCreateMixedGroup, useDeleteMixedGroup, useNextIds } from '@/hooks'
import type { MixedGroupListItem, TrustMode } from '@/types/posix'

// Form schema for creating a new MixedGroup
const createMixedGroupSchema = z.object({
  cn: z.string()
    .min(1, 'Group name is required')
    .max(64, 'Group name must be at most 64 characters')
    .regex(/^[a-z][a-z0-9_-]*$/i, 'Group name must start with a letter and contain only letters, numbers, underscores, and hyphens'),
  gidNumber: z.number().min(1000, 'GID must be at least 1000').optional(),
  forceGid: z.boolean().default(false),
  description: z.string().max(255).optional(),
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

type CreateMixedGroupFormData = z.infer<typeof createMixedGroupSchema>

export default function MixedGroupsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [searchQuery, setSearchQuery] = useState('')
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [groupToDelete, setGroupToDelete] = useState<MixedGroupListItem | null>(null)

  // Open create dialog if ?create=true is in URL
  useEffect(() => {
    if (searchParams.get('create') === 'true') {
      setShowCreateDialog(true)
      // Remove the query param to avoid reopening on refresh
      searchParams.delete('create')
      setSearchParams(searchParams, { replace: true })
    }
  }, [searchParams, setSearchParams])

  const { data: groupsResponse, isLoading, error, refetch } = useMixedGroups()
  const { data: nextIds } = useNextIds()
  const createMutation = useCreateMixedGroup()
  const deleteMutation = useDeleteMixedGroup()

  const form = useForm<CreateMixedGroupFormData>({
    resolver: zodResolver(createMixedGroupSchema),
    defaultValues: {
      cn: '',
      description: '',
      forceGid: false,
      trustMode: undefined,
      host: [],
    },
  })

  const trustMode = form.watch('trustMode')

  // Filter groups by search query
  const filteredGroups = groupsResponse?.groups?.filter((group) =>
    group.cn.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (group.description?.toLowerCase().includes(searchQuery.toLowerCase()))
  ) ?? []

  const handleCreate = async (data: CreateMixedGroupFormData) => {
    try {
      await createMutation.mutateAsync({
        cn: data.cn,
        gidNumber: data.gidNumber,
        forceGid: data.forceGid,
        description: data.description,
        trustMode: data.trustMode as TrustMode | undefined,
        host: data.trustMode === 'byhost' ? data.host ?? undefined : undefined,
      })
      toast.success(`Mixed group "${data.cn}" created successfully`)
      setShowCreateDialog(false)
      form.reset()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to create mixed group')
    }
  }

  const handleDelete = async () => {
    if (!groupToDelete) return

    try {
      await deleteMutation.mutateAsync(groupToDelete.cn)
      toast.success(`Mixed group "${groupToDelete.cn}" deleted successfully`)
      setGroupToDelete(null)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to delete mixed group')
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
              <p>Failed to load mixed groups</p>
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
            <Layers className="h-6 w-6" />
            Mixed Groups
          </h1>
          <p className="text-muted-foreground">
            Hybrid groups combining LDAP organizational groups with POSIX capabilities
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Create Mixed Group
        </Button>
      </div>

      {/* Search and Stats */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search groups..."
            className="pl-9"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <Badge variant="secondary">
          {groupsResponse?.groups?.length ?? 0} group{(groupsResponse?.groups?.length ?? 0) !== 1 ? 's' : ''}
        </Badge>
        <Button variant="outline" size="icon" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* Groups Table */}
      <Card>
        <CardHeader>
          <CardTitle>All Mixed Groups</CardTitle>
          <CardDescription>
            Mixed groups support both LDAP member DNs (groupOfNames) and POSIX memberUid
          </CardDescription>
        </CardHeader>
        <CardContent>
          {filteredGroups.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Layers className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No mixed groups found</p>
              <Button
                variant="outline"
                size="sm"
                className="mt-4"
                onClick={() => setShowCreateDialog(true)}
              >
                <Plus className="h-4 w-4 mr-2" />
                Create your first mixed group
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>GID</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>
                    <span className="flex items-center gap-1">
                      <Users className="h-3 w-3" />
                      LDAP
                    </span>
                  </TableHead>
                  <TableHead>
                    <span className="flex items-center gap-1">
                      <Terminal className="h-3 w-3" />
                      POSIX
                    </span>
                  </TableHead>
                  <TableHead className="w-[100px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredGroups.map((group) => (
                  <TableRow key={group.cn}>
                    <TableCell className="font-medium">
                      <Link 
                        to={`/posix/mixed-groups/${group.cn}`}
                        className="hover:underline text-primary"
                      >
                        {group.cn}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{group.gidNumber}</Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {group.description || '-'}
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">
                        {group.memberCount} member{group.memberCount !== 1 ? 's' : ''}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">
                        {group.memberUidCount} uid{group.memberUidCount !== 1 ? 's' : ''}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button variant="ghost" size="icon" asChild>
                          <Link to={`/posix/mixed-groups/${group.cn}`}>
                            <Edit className="h-4 w-4" />
                          </Link>
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setGroupToDelete(group)}
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
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Create Mixed Group</DialogTitle>
            <DialogDescription>
              Create a new hybrid group with both LDAP organizational and POSIX capabilities
            </DialogDescription>
          </DialogHeader>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(handleCreate)} className="space-y-4">
              <FormField
                control={form.control}
                name="cn"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Group Name</FormLabel>
                    <FormControl>
                      <Input placeholder="developers" {...field} />
                    </FormControl>
                    <FormDescription>
                      Must start with a letter and contain only letters, numbers, underscores, and hyphens
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="space-y-2">
                <FormField
                  control={form.control}
                  name="gidNumber"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>GID Number (optional)</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          placeholder={nextIds ? `Next available: ${nextIds.next_gid}` : 'Auto-assign'}
                          {...field}
                          value={field.value ?? ''}
                          onChange={(e) => field.onChange(e.target.value ? parseInt(e.target.value) : undefined)}
                        />
                      </FormControl>
                      <FormDescription>
                        Leave empty to auto-assign the next available GID
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="forceGid"
                  render={({ field }) => (
                    <FormItem className="flex items-center gap-2 space-y-0">
                      <FormControl>
                        <Checkbox
                          checked={field.value}
                          onCheckedChange={field.onChange}
                        />
                      </FormControl>
                      <FormLabel className="text-xs font-normal text-muted-foreground">
                        Force GID (allow duplicate)
                      </FormLabel>
                    </FormItem>
                  )}
                />
              </div>
              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Description (optional)</FormLabel>
                    <FormControl>
                      <Input placeholder="Development team" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              {/* System Trust Section */}
              <div className="border rounded-lg p-4 space-y-4">
                <h4 className="font-medium text-sm">System Trust (Optional)</h4>
                <p className="text-xs text-muted-foreground">
                  Control which systems this group has access to
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
                    control={form.control}
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
              
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setShowCreateDialog(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? 'Creating...' : 'Create'}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={!!groupToDelete} onOpenChange={(open) => !open && setGroupToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Mixed Group</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the mixed group "{groupToDelete?.cn}"?
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
