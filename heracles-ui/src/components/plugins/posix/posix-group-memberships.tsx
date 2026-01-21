/**
 * POSIX Group Memberships Component
 * 
 * Displays and manages the POSIX groups a user belongs to.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Users, Plus, X, Loader2 } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
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
  usePosixGroups,
  useAddUserToGroup,
  useRemoveUserFromGroup,
} from '@/hooks'

interface PosixGroupMembershipsProps {
  uid: string
  groupMemberships: string[]
  primaryGroupCn?: string
  onMembershipChange?: () => void
}

export function PosixGroupMemberships({
  uid,
  groupMemberships,
  primaryGroupCn,
  onMembershipChange,
}: PosixGroupMembershipsProps) {
  const [showAddDialog, setShowAddDialog] = useState(false)
  const [groupToRemove, setGroupToRemove] = useState<string | null>(null)
  const [selectedGroup, setSelectedGroup] = useState<string>('')

  const { data: allGroupsResponse, isLoading: groupsLoading } = usePosixGroups()
  const addMutation = useAddUserToGroup(uid)
  const removeMutation = useRemoveUserFromGroup(uid)

  // Get available groups (not already a member)
  const availableGroups = allGroupsResponse?.groups?.filter(
    (g) => !groupMemberships.includes(g.cn)
  ) ?? []

  const handleAddToGroup = async () => {
    if (!selectedGroup) return

    try {
      await addMutation.mutateAsync(selectedGroup)
      toast.success(`Added to group "${selectedGroup}"`)
      setShowAddDialog(false)
      setSelectedGroup('')
      onMembershipChange?.()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to add to group')
    }
  }

  const handleRemoveFromGroup = async () => {
    if (!groupToRemove) return

    try {
      await removeMutation.mutateAsync(groupToRemove)
      toast.success(`Removed from group "${groupToRemove}"`)
      setGroupToRemove(null)
      onMembershipChange?.()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to remove from group')
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">Group Memberships</span>
          <Badge variant="secondary" className="text-xs">
            {groupMemberships.length}
          </Badge>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowAddDialog(true)}
          disabled={availableGroups.length === 0}
        >
          <Plus className="h-3 w-3 mr-1" />
          Add to Group
        </Button>
      </div>

      {groupMemberships.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Not a member of any additional groups
        </p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {groupMemberships.map((cn) => (
            <Badge
              key={cn}
              variant={cn === primaryGroupCn ? 'default' : 'secondary'}
              className="flex items-center gap-1 pr-1"
            >
              <Link
                to={`/posix/groups/${cn}`}
                className="hover:underline flex items-center gap-1"
              >
                {cn}
                {cn === primaryGroupCn && (
                  <span className="text-xs opacity-70">(primary)</span>
                )}
              </Link>
              {cn !== primaryGroupCn && (
                <button
                  type="button"
                  onClick={() => setGroupToRemove(cn)}
                  className="ml-1 hover:bg-destructive/20 rounded p-0.5"
                  title="Remove from group"
                >
                  <X className="h-3 w-3" />
                </button>
              )}
            </Badge>
          ))}
        </div>
      )}

      {/* Add to Group Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add to POSIX Group</DialogTitle>
            <DialogDescription>
              Select a group to add {uid} as a member.
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            <Select
              disabled={groupsLoading}
              onValueChange={setSelectedGroup}
              value={selectedGroup}
            >
              <SelectTrigger>
                <SelectValue placeholder={groupsLoading ? 'Loading...' : 'Select a group'} />
              </SelectTrigger>
              <SelectContent>
                {availableGroups.map((group) => (
                  <SelectItem key={group.cn} value={group.cn}>
                    {group.cn} (GID {group.gidNumber})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleAddToGroup}
              disabled={!selectedGroup || addMutation.isPending}
            >
              {addMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Add to Group
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Remove from Group Confirmation */}
      <AlertDialog open={!!groupToRemove} onOpenChange={() => setGroupToRemove(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove from group?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to remove {uid} from the group "{groupToRemove}"?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRemoveFromGroup}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {removeMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              Remove
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
