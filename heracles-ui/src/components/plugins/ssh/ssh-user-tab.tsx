/**
 * SSH User Tab Component
 * 
 * Displays and manages SSH keys for a user account.
 */

import { useState } from 'react'
import { toast } from 'sonner'
import { Key, Plus, PowerOff } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { PluginTabSkeleton, PluginTabError, PluginTabInactive } from '@/components/plugins/plugin-tab-shell'
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

import { SshKeysTable } from './ssh-keys-table'
import {
  useUserSSHStatus,
  useActivateUserSSH,
  useDeactivateUserSSH,
  useAddSSHKey,
  useRemoveSSHKey,
} from '@/hooks/use-ssh'
import { AppError } from '@/lib/errors'
import type { SSHKeyRead } from '@/types/ssh'

interface SSHUserTabProps {
  uid: string
  displayName: string
}

export function SSHUserTab({ uid, displayName }: SSHUserTabProps) {
  const [showDeactivateDialog, setShowDeactivateDialog] = useState(false)
  const [showAddKeyDialog, setShowAddKeyDialog] = useState(false)
  const [keyToDelete, setKeyToDelete] = useState<SSHKeyRead | null>(null)
  const [newKeyValue, setNewKeyValue] = useState('')
  const [newKeyComment, setNewKeyComment] = useState('')

  const { data: sshStatus, isLoading, error, refetch } = useUserSSHStatus(uid)
  const activateMutation = useActivateUserSSH()
  const deactivateMutation = useDeactivateUserSSH()
  const addKeyMutation = useAddSSHKey()
  const removeKeyMutation = useRemoveSSHKey()

  const handleActivate = async () => {
    try {
      await activateMutation.mutateAsync({ uid })
      toast.success('SSH enabled for user')
    } catch (error) {
      AppError.toastError(error, 'Failed to enable SSH')
    }
  }

  const handleDeactivate = async () => {
    try {
      await deactivateMutation.mutateAsync(uid)
      toast.success('SSH disabled for user')
      setShowDeactivateDialog(false)
    } catch (error) {
      AppError.toastError(error, 'Failed to disable SSH')
    }
  }

  const handleAddKey = async () => {
    if (!newKeyValue.trim()) {
      toast.error('Please enter an SSH public key')
      return
    }

    try {
      await addKeyMutation.mutateAsync({
        uid,
        data: {
          key: newKeyValue.trim(),
          comment: newKeyComment.trim() || undefined,
        },
      })
      toast.success('SSH key added successfully')
      setShowAddKeyDialog(false)
      setNewKeyValue('')
      setNewKeyComment('')
    } catch (error) {
      AppError.toastError(error, 'Failed to add SSH key')
    }
  }

  const handleRemoveKey = async () => {
    if (!keyToDelete) return

    try {
      await removeKeyMutation.mutateAsync({
        uid,
        fingerprint: keyToDelete.fingerprint,
      })
      toast.success('SSH key removed')
      setKeyToDelete(null)
    } catch (error) {
      AppError.toastError(error, 'Failed to remove SSH key')
    }
  }

  if (isLoading) {
    return <PluginTabSkeleton />
  }

  if (error) {
    return (
      <PluginTabError
        icon={Key}
        title="SSH Keys"
        message="Failed to load SSH status"
        onRetry={() => refetch()}
      />
    )
  }

  // SSH not activated
  if (!sshStatus?.hasSsh) {
    return (
      <PluginTabInactive
        icon={Key}
        title="SSH Keys"
        heading="SSH Not Enabled"
        description="Enable SSH to allow this user to store public keys for SSH authentication."
        activateLabel="Enable SSH"
        onActivate={handleActivate}
        isActivating={activateMutation.isPending}
      />
    )
  }

  // SSH activated - show keys
  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Key className="h-5 w-5" />
                SSH Keys
                <Badge variant="secondary">{sshStatus.keyCount} key{sshStatus.keyCount !== 1 ? 's' : ''}</Badge>
              </CardTitle>
              <CardDescription>
                Manage SSH public keys for {displayName}
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button onClick={() => setShowAddKeyDialog(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Add Key
              </Button>
              <Button 
                variant="outline" 
                onClick={() => setShowDeactivateDialog(true)}
              >
                <PowerOff className="mr-2 h-4 w-4" />
                Disable SSH
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <SshKeysTable
            keys={sshStatus.keys}
            onDelete={setKeyToDelete}
            emptyMessage="No SSH keys configured"
          />
        </CardContent>
      </Card>

      {/* Add Key Dialog */}
      <Dialog open={showAddKeyDialog} onOpenChange={setShowAddKeyDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Add SSH Key</DialogTitle>
            <DialogDescription>
              Paste the public key from your SSH key pair (usually found in ~/.ssh/id_*.pub)
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="ssh-key">Public Key *</Label>
              <Textarea
                id="ssh-key"
                placeholder="ssh-ed25519 AAAA... user@host"
                className="font-mono text-sm h-32"
                value={newKeyValue}
                onChange={(e) => setNewKeyValue(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Supported types: RSA, Ed25519, ECDSA, DSA, SK (Security Keys)
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="ssh-comment">Comment (optional)</Label>
              <Input
                id="ssh-comment"
                placeholder="My laptop key"
                value={newKeyComment}
                onChange={(e) => setNewKeyComment(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                A label to identify this key (overrides comment in key)
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddKeyDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddKey} disabled={addKeyMutation.isPending}>
              {addKeyMutation.isPending ? 'Adding...' : 'Add Key'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Key Confirmation */}
      <AlertDialog open={!!keyToDelete} onOpenChange={(open) => !open && setKeyToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove SSH Key</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to remove this SSH key?
              <div className="mt-2 p-2 bg-muted rounded">
                <p className="text-sm font-mono">{keyToDelete?.fingerprint}</p>
                {keyToDelete?.comment && (
                  <p className="text-sm text-muted-foreground mt-1">{keyToDelete.comment}</p>
                )}
              </div>
              This will revoke SSH access using this key.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRemoveKey}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {removeKeyMutation.isPending ? 'Removing...' : 'Remove Key'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Deactivate SSH Confirmation */}
      <AlertDialog open={showDeactivateDialog} onOpenChange={setShowDeactivateDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Disable SSH</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to disable SSH for {displayName}?
              This will remove all SSH keys and revoke SSH access.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeactivate}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deactivateMutation.isPending ? 'Disabling...' : 'Disable SSH'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
