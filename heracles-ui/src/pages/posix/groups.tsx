/**
 * POSIX Groups List Page
 * 
 * Lists all standalone POSIX groups and provides CRUD operations.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Users, Trash2, Edit, RefreshCw, Search } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import { usePosixGroups, useCreatePosixGroup, useDeletePosixGroup, useNextIds } from '@/hooks'
import type { PosixGroupListItem } from '@/types/posix'

// Form schema for creating a new POSIX group
const createGroupSchema = z.object({
  cn: z.string()
    .min(1, 'Group name is required')
    .max(64, 'Group name must be at most 64 characters')
    .regex(/^[a-z][a-z0-9_-]*$/i, 'Group name must start with a letter and contain only letters, numbers, underscores, and hyphens'),
  gidNumber: z.number().min(1000, 'GID must be at least 1000').optional(),
  description: z.string().max(255).optional(),
})

type CreateGroupFormData = z.infer<typeof createGroupSchema>

export default function PosixGroupsPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [groupToDelete, setGroupToDelete] = useState<PosixGroupListItem | null>(null)

  const { data: groupsResponse, isLoading, error, refetch } = usePosixGroups()
  const { data: nextIds } = useNextIds()
  const createMutation = useCreatePosixGroup()
  const deleteMutation = useDeletePosixGroup()

  const form = useForm<CreateGroupFormData>({
    resolver: zodResolver(createGroupSchema),
    defaultValues: {
      cn: '',
      description: '',
    },
  })

  // Filter groups by search query
  const filteredGroups = groupsResponse?.groups?.filter((group) =>
    group.cn.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (group.description?.toLowerCase().includes(searchQuery.toLowerCase()))
  ) ?? []

  const handleCreate = async (data: CreateGroupFormData) => {
    try {
      await createMutation.mutateAsync({
        cn: data.cn,
        gidNumber: data.gidNumber,
        description: data.description,
      })
      toast.success(`POSIX group "${data.cn}" created successfully`)
      setShowCreateDialog(false)
      form.reset()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to create POSIX group')
    }
  }

  const handleDelete = async () => {
    if (!groupToDelete) return

    try {
      await deleteMutation.mutateAsync(groupToDelete.cn)
      toast.success(`POSIX group "${groupToDelete.cn}" deleted successfully`)
      setGroupToDelete(null)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to delete POSIX group')
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
              <p>Failed to load POSIX groups</p>
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
            <Users className="h-6 w-6" />
            POSIX Groups
          </h1>
          <p className="text-muted-foreground">
            Manage standalone POSIX groups for UNIX/Linux systems
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Create Group
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
          {groupsResponse?.total ?? 0} group{(groupsResponse?.total ?? 0) !== 1 ? 's' : ''}
        </Badge>
        <Button variant="outline" size="icon" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* Groups Table */}
      <Card>
        <CardHeader>
          <CardTitle>POSIX Groups</CardTitle>
          <CardDescription>
            These are standalone POSIX groups (posixGroup objectClass) used for UNIX/Linux permissions
          </CardDescription>
        </CardHeader>
        <CardContent>
          {filteredGroups.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {searchQuery ? 'No groups match your search' : 'No POSIX groups found'}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Group Name (cn)</TableHead>
                  <TableHead>GID</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Members</TableHead>
                  <TableHead className="w-[100px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredGroups.map((group) => (
                  <TableRow key={group.cn}>
                    <TableCell className="font-medium">
                      <Link 
                        to={`/posix/groups/${group.cn}`}
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
                      <div className="flex items-center gap-1">
                        <Button variant="ghost" size="icon" asChild>
                          <Link to={`/posix/groups/${group.cn}`}>
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
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create POSIX Group</DialogTitle>
            <DialogDescription>
              Create a new standalone POSIX group for UNIX/Linux systems
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
            <AlertDialogTitle>Delete POSIX Group</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the POSIX group "{groupToDelete?.cn}"?
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
