/**
 * SSH User Tab Component
 * 
 * Displays and manages SSH keys for a user account.
 */

import { useState } from 'react'
import { toast } from 'sonner'
import { Key, Plus, Trash2, Power, PowerOff, Copy, Check, AlertTriangle } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

import {
  useUserSSHStatus,
  useActivateUserSSH,
  useDeactivateUserSSH,
  useAddSSHKey,
  useRemoveSSHKey,
} from '@/hooks/use-ssh'
import type { SSHKeyRead } from '@/types/ssh'
import { getKeyTypeName, getKeyStrengthVariant, truncateFingerprint } from '@/types/ssh'

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
  const [copiedFingerprint, setCopiedFingerprint] = useState<string | null>(null)

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
      toast.error(error instanceof Error ? error.message : 'Failed to enable SSH')
    }
  }

  const handleDeactivate = async () => {
    try {
      await deactivateMutation.mutateAsync(uid)
      toast.success('SSH disabled for user')
      setShowDeactivateDialog(false)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to disable SSH')
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
      toast.error(error instanceof Error ? error.message : 'Failed to add SSH key')
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
      toast.error(error instanceof Error ? error.message : 'Failed to remove SSH key')
    }
  }

  const copyFingerprint = (fingerprint: string) => {
    navigator.clipboard.writeText(fingerprint)
    setCopiedFingerprint(fingerprint)
    setTimeout(() => setCopiedFingerprint(null), 2000)
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
            <Key className="h-5 w-5" />
            SSH Keys
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="h-4 w-4" />
            <span>Failed to load SSH status</span>
          </div>
          <Button variant="outline" size="sm" className="mt-4" onClick={() => refetch()}>
            Retry
          </Button>
        </CardContent>
      </Card>
    )
  }

  // SSH not activated
  if (!sshStatus?.hasSsh) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            SSH Keys
          </CardTitle>
          <CardDescription>
            SSH key management is not enabled for this user.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Key className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">SSH Not Enabled</h3>
            <p className="text-muted-foreground mb-6 max-w-md">
              Enable SSH to allow this user to store public keys for SSH authentication.
            </p>
            <Button onClick={handleActivate} disabled={activateMutation.isPending}>
              <Power className="mr-2 h-4 w-4" />
              {activateMutation.isPending ? 'Enabling...' : 'Enable SSH'}
            </Button>
          </div>
        </CardContent>
      </Card>
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
          {sshStatus.keys.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Key className="h-8 w-8 mx-auto mb-4 opacity-50" />
              <p>No SSH keys configured</p>
              <p className="text-sm">Add a public key to enable SSH authentication</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Fingerprint</TableHead>
                  <TableHead>Comment</TableHead>
                  <TableHead>Strength</TableHead>
                  <TableHead className="w-[100px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sshStatus.keys.map((key) => (
                  <TableRow key={key.fingerprint}>
                    <TableCell>
                      <Badge variant="outline">
                        {getKeyTypeName(key.keyType)}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <div className="flex items-center gap-2">
                              <code className="text-xs bg-muted px-2 py-1 rounded font-mono">
                                {truncateFingerprint(key.fingerprint)}
                              </code>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-6 w-6"
                                onClick={() => copyFingerprint(key.fingerprint)}
                              >
                                {copiedFingerprint === key.fingerprint ? (
                                  <Check className="h-3 w-3 text-green-500" />
                                ) : (
                                  <Copy className="h-3 w-3" />
                                )}
                              </Button>
                            </div>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p className="font-mono text-xs">{key.fingerprint}</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {key.comment || '-'}
                    </TableCell>
                    <TableCell>
                      <Badge variant={getKeyStrengthVariant(key.keyType, key.bits)}>
                        {key.bits ? `${key.bits} bits` : 'N/A'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setKeyToDelete(key)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
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
