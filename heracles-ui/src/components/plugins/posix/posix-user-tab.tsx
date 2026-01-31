import { useState } from 'react'
import { toast } from 'sonner'
import { Terminal, Power, PowerOff, AlertTriangle } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
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
  useUserPosix,
  useActivateUserPosix,
  useUpdateUserPosix,
  useDeactivateUserPosix,
} from '@/hooks'
import { useDepartmentStore } from '@/stores'
import { PosixActivateForm } from './posix-activate-form'
import { PosixEditForm } from './posix-edit-form'
import { PosixGroupMemberships } from './posix-group-memberships'
import { AccountStatusBadge } from './posix-account-status'
import type { PosixAccountCreate, PosixAccountUpdate } from '@/types/posix'

interface PosixUserTabProps {
  uid: string
  displayName: string
}

export function PosixUserTab({ uid, displayName }: PosixUserTabProps) {
  const [showDeactivateDialog, setShowDeactivateDialog] = useState(false)
  const [showActivateForm, setShowActivateForm] = useState(false)
  const [deletePersonalGroup, setDeletePersonalGroup] = useState(true)
  const { currentBase } = useDepartmentStore()

  const { data: posixStatus, isLoading, error, refetch } = useUserPosix(uid, currentBase || undefined)
  const activateMutation = useActivateUserPosix(uid)
  const updateMutation = useUpdateUserPosix(uid)
  const deactivateMutation = useDeactivateUserPosix(uid)

  const handleActivate = async (data: PosixAccountCreate) => {
    try {
      await activateMutation.mutateAsync({ data, baseDn: currentBase || undefined })
      toast.success('Unix account enabled successfully')
      setShowActivateForm(false)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to enable Unix account')
    }
  }

  const handleUpdate = async (data: PosixAccountUpdate) => {
    try {
      await updateMutation.mutateAsync({ data, baseDn: currentBase || undefined })
      toast.success('Unix account updated successfully')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to update Unix account')
    }
  }

  const handleDeactivate = async () => {
    try {
      await deactivateMutation.mutateAsync({ deletePersonalGroup, baseDn: currentBase || undefined })
      toast.success('Unix account disabled successfully')
      setShowDeactivateDialog(false)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to disable Unix account')
    }
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-72" />
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Terminal className="h-5 w-5" />
            Unix Account
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-6 text-destructive">
            <p>Failed to load POSIX data</p>
            <Button variant="outline" size="sm" className="mt-2" onClick={() => refetch()}>
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  const isActive = posixStatus?.active ?? false
  const posixData = posixStatus?.data

  // Check if user has a personal group that might be deleted
  const hasPersonalGroup = posixData?.primaryGroupCn === uid

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Terminal className="h-5 w-5" />
              <CardTitle>Unix Account</CardTitle>
              {isActive ? (
                <>
                  <Badge variant="default" className="bg-green-600">
                    <Power className="h-3 w-3 mr-1" />
                    Active
                  </Badge>
                  {posixData?.accountStatus && posixData.accountStatus !== 'active' && (
                    <AccountStatusBadge status={posixData.accountStatus} />
                  )}
                </>
              ) : (
                <Badge variant="secondary">
                  <PowerOff className="h-3 w-3 mr-1" />
                  Inactive
                </Badge>
              )}
            </div>
            {isActive && (
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setShowDeactivateDialog(true)}
              >
                <PowerOff className="h-4 w-4 mr-2" />
                Disable
              </Button>
            )}
          </div>
          <CardDescription>
            {isActive
              ? 'POSIX/Unix account settings for Linux/Unix systems'
              : 'Enable Unix account to allow login on Linux/Unix systems'}
          </CardDescription>
        </CardHeader>

        <CardContent>
          {isActive && posixData ? (
            <div className="space-y-6">
              <PosixEditForm
                data={posixData}
                onSubmit={handleUpdate}
                isSubmitting={updateMutation.isPending}
              />

              <Separator />

              {/* Group Memberships Section */}
              <PosixGroupMemberships
                uid={uid}
                groupMemberships={posixData.groupMemberships ?? []}
                primaryGroupCn={posixData.primaryGroupCn}
                onMembershipChange={() => refetch()}
              />
            </div>
          ) : showActivateForm ? (
            <PosixActivateForm
              uid={uid}
              displayName={displayName}
              onSubmit={handleActivate}
              onCancel={() => setShowActivateForm(false)}
              isSubmitting={activateMutation.isPending}
            />
          ) : (
            <div className="text-center py-8">
              <Terminal className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">Unix Account Not Enabled</h3>
              <p className="text-muted-foreground mb-4">
                This user does not have POSIX attributes. Enable Unix account to allow
                login on Linux/Unix systems with UID, home directory, and shell.
              </p>
              <Button onClick={() => setShowActivateForm(true)}>
                <Power className="h-4 w-4 mr-2" />
                Enable Unix Account
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Deactivate Confirmation Dialog */}
      <AlertDialog open={showDeactivateDialog} onOpenChange={setShowDeactivateDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-destructive" />
              Disable Unix Account?
            </AlertDialogTitle>
            <AlertDialogDescription>
              This will remove all POSIX attributes from this user, including:
              <ul className="list-disc list-inside mt-2 space-y-1">
                <li>UID number ({posixData?.uidNumber})</li>
                <li>Home directory ({posixData?.homeDirectory})</li>
                <li>Login shell</li>
                <li>Group membership settings</li>
              </ul>
              <p className="mt-2 font-medium">
                The user will no longer be able to log in to Unix/Linux systems.
              </p>
            </AlertDialogDescription>
          </AlertDialogHeader>

          {hasPersonalGroup && (
            <div className="flex items-center space-x-2 py-2">
              <Checkbox
                id="delete-personal-group"
                checked={deletePersonalGroup}
                onCheckedChange={(checked) => setDeletePersonalGroup(checked === true)}
              />
              <Label htmlFor="delete-personal-group" className="text-sm">
                Also delete personal group "{uid}" (if empty)
              </Label>
            </div>
          )}

          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeactivate}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deactivateMutation.isPending ? 'Disabling...' : 'Disable Unix Account'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
