import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { toast } from 'sonner'
import { ArrowLeft, Shield, UserPlus, X, Save } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { PageHeader, DetailPageSkeleton, ErrorDisplay, LoadingSpinner, ConfirmDialog } from '@/components/common'
import { useRole, useUpdateRole, useAddRoleMember, useRemoveRoleMember } from '@/hooks/use-roles'
import { AppError } from '@/lib/errors'
import { ROUTES } from '@/config/constants'
import { useRecentStore } from '@/stores'

export function RoleDetailPage() {
    const { cn } = useParams<{ cn: string }>()
    const navigate = useNavigate()
    const [isEditing, setIsEditing] = useState(false)
    const [description, setDescription] = useState('')
    const [addMemberOpen, setAddMemberOpen] = useState(false)
    const [newMemberUid, setNewMemberUid] = useState('')
    const [removeMember, setRemoveMember] = useState<string | null>(null)
    const addRecentItem = useRecentStore((state) => state.addItem)

    const { data: role, isLoading, error, refetch } = useRole(cn || '')
    const updateMutation = useUpdateRole(cn || '')
    const addMemberMutation = useAddRoleMember(cn || '')
    const removeMemberMutation = useRemoveRoleMember(cn || '')

    useEffect(() => {
        if (!role) return
        addRecentItem({
            id: role.cn,
            label: role.cn,
            href: ROUTES.ROLE_DETAIL.replace(':cn', role.cn),
            type: 'role',
            description: role.description,
        })
    }, [addRecentItem, role])

      if (isLoading) {
        return <DetailPageSkeleton />
      }

    if (error || !role) {
        return <ErrorDisplay message={error?.message || 'Role not found'} onRetry={() => refetch()} />
    }

    const handleStartEditing = () => {
        setDescription(role.description || '')
        setIsEditing(true)
    }

    const handleSave = async () => {
        try {
            await updateMutation.mutateAsync({ description })
            toast.success('Role updated successfully')
            setIsEditing(false)
        } catch (error) {
            AppError.toastError(error, 'Failed to update role')
        }
    }

    const handleAddMember = async () => {
        if (!newMemberUid.trim()) return
        try {
            await addMemberMutation.mutateAsync(newMemberUid.trim())
            toast.success(`User "${newMemberUid}" added to role`)
            setNewMemberUid('')
            setAddMemberOpen(false)
            refetch()
        } catch (error) {
            AppError.toastError(error, 'Failed to add member')
        }
    }

    const handleRemoveMember = async () => {
        if (!removeMember) return
        try {
            await removeMemberMutation.mutateAsync(removeMember)
            toast.success(`User "${removeMember}" removed from role`)
            setRemoveMember(null)
            refetch()
        } catch (error) {
            AppError.toastError(error, 'Failed to remove member')
        }
    }

    return (
        <div>
            <PageHeader
                title={role.cn}
                description="Organizational Role"
                actions={
                    <Button variant="outline" onClick={() => navigate(ROUTES.GROUPS)}>
                        <ArrowLeft className="mr-2 h-4 w-4" />
                        Back
                    </Button>
                }
            />

            <div className="space-y-6">
                {/* Role Information */}
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between">
                        <div>
                            <CardTitle className="flex items-center gap-2">
                                <Shield className="h-5 w-5" />
                                Role Information
                            </CardTitle>
                            <CardDescription>Basic role details</CardDescription>
                        </div>
                        {!isEditing && (
                            <Button variant="outline" onClick={handleStartEditing}>
                                Edit
                            </Button>
                        )}
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div>
                            <Label className="text-sm font-medium text-muted-foreground">Role Name</Label>
                            <p className="text-lg font-semibold">{role.cn}</p>
                        </div>
                        <div>
                            <Label className="text-sm font-medium text-muted-foreground">DN</Label>
                            <p className="text-sm font-mono text-muted-foreground">{role.dn}</p>
                        </div>
                        {isEditing ? (
                            <div className="space-y-2">
                                <Label>Description</Label>
                                <Input
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    placeholder="Role description"
                                />
                                <div className="flex gap-2">
                                    <Button onClick={handleSave} disabled={updateMutation.isPending}>
                                        {updateMutation.isPending ? (
                                            <LoadingSpinner size="sm" className="mr-2" />
                                        ) : (
                                            <Save className="mr-2 h-4 w-4" />
                                        )}
                                        Save
                                    </Button>
                                    <Button variant="outline" onClick={() => setIsEditing(false)}>
                                        Cancel
                                    </Button>
                                </div>
                            </div>
                        ) : (
                            <div>
                                <Label className="text-sm font-medium text-muted-foreground">Description</Label>
                                <p>{role.description || 'No description'}</p>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Role Members */}
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between">
                        <div>
                            <CardTitle>Members</CardTitle>
                            <CardDescription>Users assigned to this role ({role.memberCount || 0})</CardDescription>
                        </div>
                        <Button onClick={() => setAddMemberOpen(true)}>
                            <UserPlus className="mr-2 h-4 w-4" />
                            Add Member
                        </Button>
                    </CardHeader>
                    <CardContent>
                        {role.members && role.members.length > 0 ? (
                            <div className="flex flex-wrap gap-2">
                                {role.members.map((member) => (
                                    <Badge key={member} variant="secondary" className="pl-3 pr-1 py-1">
                                        <Link to={`/users/${member}`} className="hover:underline">
                                            {member}
                                        </Link>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="ml-1 h-5 w-5 hover:bg-destructive/20"
                                            onClick={() => setRemoveMember(member)}
                                        >
                                            <X className="h-3 w-3" />
                                        </Button>
                                    </Badge>
                                ))}
                            </div>
                        ) : (
                            <p className="text-muted-foreground">No members assigned to this role.</p>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Add Member Dialog */}
            <Dialog open={addMemberOpen} onOpenChange={setAddMemberOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Add Member to Role</DialogTitle>
                        <DialogDescription>Enter the username of the user to add to this role.</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label htmlFor="uid">Username</Label>
                            <Input
                                id="uid"
                                value={newMemberUid}
                                onChange={(e) => setNewMemberUid(e.target.value)}
                                placeholder="johndoe"
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setAddMemberOpen(false)}>
                            Cancel
                        </Button>
                        <Button onClick={handleAddMember} disabled={addMemberMutation.isPending || !newMemberUid.trim()}>
                            {addMemberMutation.isPending ? (
                                <LoadingSpinner size="sm" className="mr-2" />
                            ) : (
                                <UserPlus className="mr-2 h-4 w-4" />
                            )}
                            Add Member
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Remove Member Confirmation */}
            <ConfirmDialog
                open={!!removeMember}
                onOpenChange={(open) => !open && setRemoveMember(null)}
                title="Remove Member"
                description={`Are you sure you want to remove "${removeMember}" from this role?`}
                confirmLabel="Remove"
                variant="destructive"
                onConfirm={handleRemoveMember}
                isLoading={removeMemberMutation.isPending}
            />
        </div>
    )
}
