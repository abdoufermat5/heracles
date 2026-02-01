/**
 * Mail Group Tab Component
 *
 * Displays and manages mailing list settings for a group.
 */

import { useState } from 'react'
import { toast } from 'sonner'
import {
  Mails,
  Power,
  PowerOff,
  AlertTriangle,
  Users,
  Forward,
  AtSign,
  Lock,
} from 'lucide-react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
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
  useGroupMailStatus,
  useActivateGroupMail,
  useUpdateGroupMail,
  useDeactivateGroupMail,
} from '@/hooks/use-mail'
import type { MailGroupCreate } from '@/types/mail'

interface MailGroupTabProps {
  cn: string
  displayName: string
}

export function MailGroupTab({ cn, displayName }: MailGroupTabProps) {
  const [showDeactivateDialog, setShowDeactivateDialog] = useState(false)
  const [showActivateDialog, setShowActivateDialog] = useState(false)
  const [activateMail, setActivateMail] = useState('')

  const { data: mailStatus, isLoading, error, refetch } = useGroupMailStatus(cn)
  const activateMutation = useActivateGroupMail()
  const updateMutation = useUpdateGroupMail()
  const deactivateMutation = useDeactivateGroupMail()

  const handleActivate = async () => {
    if (!activateMail.trim()) {
      toast.error('Please enter an email address')
      return
    }

    try {
      const data: MailGroupCreate = {
        mail: activateMail.trim(),
      }
      await activateMutation.mutateAsync({ cn, data })
      toast.success('Mailing list enabled')
      setShowActivateDialog(false)
      setActivateMail('')
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to enable mailing list'
      )
    }
  }

  const handleDeactivate = async () => {
    try {
      await deactivateMutation.mutateAsync(cn)
      toast.success('Mailing list disabled')
      setShowDeactivateDialog(false)
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to disable mailing list'
      )
    }
  }

  const handleLocalOnlyToggle = async (enabled: boolean) => {
    try {
      await updateMutation.mutateAsync({
        cn,
        data: { localOnly: enabled },
      })
      toast.success(
        enabled ? 'Local-only restriction enabled' : 'Local-only restriction disabled'
      )
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to update setting'
      )
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
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mails className="h-5 w-5" />
            Mailing List
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="h-4 w-4" />
            <span>Failed to load mailing list status</span>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="mt-4"
            onClick={() => refetch()}
          >
            Retry
          </Button>
        </CardContent>
      </Card>
    )
  }

  // Mailing list not activated
  if (!mailStatus?.active) {
    return (
      <>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Mails className="h-5 w-5" />
              Mailing List
            </CardTitle>
            <CardDescription>
              Mailing list is not enabled for this group.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <Mails className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">No Mailing List</h3>
              <p className="text-muted-foreground mb-6 max-w-md">
                Enable a mailing list to allow sending email to all group members
                at once.
              </p>
              <Button
                onClick={() => setShowActivateDialog(true)}
                disabled={activateMutation.isPending}
              >
                <Power className="mr-2 h-4 w-4" />
                Enable Mailing List
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Activate Dialog */}
        <Dialog open={showActivateDialog} onOpenChange={setShowActivateDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Enable Mailing List</DialogTitle>
              <DialogDescription>
                Configure the email address for {displayName}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="group-mail">Group Email Address *</Label>
                <Input
                  id="group-mail"
                  type="email"
                  placeholder="group@example.com"
                  value={activateMail}
                  onChange={(e) => setActivateMail(e.target.value)}
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setShowActivateDialog(false)}
              >
                Cancel
              </Button>
              <Button
                onClick={handleActivate}
                disabled={activateMutation.isPending}
              >
                {activateMutation.isPending ? 'Enabling...' : 'Enable'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </>
    )
  }

  const data = mailStatus.data!

  // Mailing list activated
  return (
    <>
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Mails className="h-5 w-5" />
                  Mailing List
                  <Badge variant="secondary">Active</Badge>
                </CardTitle>
                <CardDescription>
                  Mailing list settings for {displayName}
                </CardDescription>
              </div>
              <Button
                variant="outline"
                onClick={() => setShowDeactivateDialog(true)}
              >
                <PowerOff className="mr-2 h-4 w-4" />
                Disable
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Primary Email */}
            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <AtSign className="h-4 w-4" />
                Group Email
              </Label>
              <Input value={data.mail} disabled className="flex-1" />
            </div>

            {/* Local Only Setting */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="flex items-center gap-2">
                  <Lock className="h-4 w-4" />
                  Local Only
                </Label>
                <p className="text-sm text-muted-foreground">
                  Only accept mail from local senders
                </p>
              </div>
              <Switch
                checked={data.localOnly}
                onCheckedChange={handleLocalOnlyToggle}
              />
            </div>

            {/* Max Message Size */}
            {data.maxMessageSizeKb && (
              <div className="space-y-2">
                <Label>Max Message Size</Label>
                <p className="text-sm">
                  {data.maxMessageSizeKb >= 1024
                    ? `${(data.maxMessageSizeKb / 1024).toFixed(1)} MB`
                    : `${data.maxMessageSizeKb} KB`}
                </p>
              </div>
            )}

            {/* Alternate Addresses */}
            {data.alternateAddresses.length > 0 && (
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <AtSign className="h-4 w-4" />
                  Alternate Addresses
                </Label>
                <div className="flex flex-wrap gap-2">
                  {data.alternateAddresses.map((addr) => (
                    <Badge key={addr} variant="outline">
                      {addr}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Forwarding */}
            {data.forwardingAddresses.length > 0 && (
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <Forward className="h-4 w-4" />
                  Forward To Non-Members
                </Label>
                <div className="flex flex-wrap gap-2">
                  {data.forwardingAddresses.map((addr) => (
                    <Badge key={addr} variant="outline">
                      {addr}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            <Separator />

            {/* Members */}
            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <Users className="h-4 w-4" />
                Member Emails
                <Badge variant="secondary">{data.memberEmails.length}</Badge>
              </Label>
              {data.memberEmails.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {data.memberEmails.map((email) => (
                    <Badge key={email} variant="outline">
                      {email}
                    </Badge>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No members with email addresses
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Deactivate Confirmation */}
      <AlertDialog
        open={showDeactivateDialog}
        onOpenChange={setShowDeactivateDialog}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Disable Mailing List</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to disable the mailing list for {displayName}
              ? Messages sent to this address will no longer be delivered to group
              members.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeactivate}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deactivateMutation.isPending ? 'Disabling...' : 'Disable'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
