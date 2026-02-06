/**
 * Mail User Tab Component
 *
 * Displays and manages mail account settings for a user.
 */

import { useState } from 'react'
import { toast } from 'sonner'
import {
  Mail,
  Power,
  PowerOff,
  AlertTriangle,
  Palmtree,
  Forward,
  AtSign,
  Pencil,
  Plus,
  X,
  HardDrive,
  Gauge,
  Check,
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
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
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
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

import {
  useUserMailStatus,
  useActivateUserMail,
  useUpdateUserMail,
  useDeactivateUserMail,
} from '@/hooks/use-mail'
import {
  formatQuota,
  getQuotaPercentage,
  formatDate,
} from '@/types/mail'
import type { DeliveryMode, MailAccountCreate } from '@/types/mail'

interface MailUserTabProps {
  uid: string
  displayName: string
}

export function MailUserTab({ uid, displayName }: MailUserTabProps) {
  const [showDeactivateDialog, setShowDeactivateDialog] = useState(false)
  const [showActivateDialog, setShowActivateDialog] = useState(false)

  // Activate form state
  const [activateMail, setActivateMail] = useState('')
  const [activateQuota, setActivateQuota] = useState<number>(1024)
  const [activateServer, setActivateServer] = useState('')
  const [activateAliases, setActivateAliases] = useState<string[]>([])
  const [activateAliasInput, setActivateAliasInput] = useState('')

  // Inline edit states
  const [editingQuota, setEditingQuota] = useState(false)
  const [editQuotaValue, setEditQuotaValue] = useState<number>(0)

  const [editingAliases, setEditingAliases] = useState(false)
  const [editAliases, setEditAliases] = useState<string[]>([])
  const [editAliasInput, setEditAliasInput] = useState('')

  const [editingForwards, setEditingForwards] = useState(false)
  const [editForwards, setEditForwards] = useState<string[]>([])
  const [editForwardInput, setEditForwardInput] = useState('')

  // Edit states
  const [editingVacation, setEditingVacation] = useState(false)
  const [vacationMessage, setVacationMessage] = useState('')
  const [vacationStart, setVacationStart] = useState('')
  const [vacationEnd, setVacationEnd] = useState('')

  const { data: mailStatus, isLoading, error, refetch } = useUserMailStatus(uid)
  const activateMutation = useActivateUserMail()
  const updateMutation = useUpdateUserMail()
  const deactivateMutation = useDeactivateUserMail()

  const handleActivate = async () => {
    if (!activateMail.trim()) {
      toast.error('Please enter an email address')
      return
    }

    try {
      const data: MailAccountCreate = {
        mail: activateMail.trim(),
        quotaMb: activateQuota,
        mailServer: activateServer.trim() || undefined,
        alternateAddresses: activateAliases.length > 0 ? activateAliases : undefined,
      }
      await activateMutation.mutateAsync({ uid, data })
      toast.success('Mail account enabled')
      setShowActivateDialog(false)
      setActivateMail('')
      setActivateQuota(1024)
      setActivateServer('')
      setActivateAliases([])
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to enable mail'
      )
    }
  }

  const handleQuotaSave = async () => {
    try {
      await updateMutation.mutateAsync({
        uid,
        data: { quotaMb: editQuotaValue },
      })
      toast.success('Quota updated')
      setEditingQuota(false)
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to update quota'
      )
    }
  }

  const handleAliasesSave = async () => {
    try {
      await updateMutation.mutateAsync({
        uid,
        data: { alternateAddresses: editAliases },
      })
      toast.success('Alternate addresses updated')
      setEditingAliases(false)
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to update addresses'
      )
    }
  }

  const handleForwardsSave = async () => {
    try {
      await updateMutation.mutateAsync({
        uid,
        data: { forwardingAddresses: editForwards },
      })
      toast.success('Forwarding addresses updated')
      setEditingForwards(false)
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to update forwarding'
      )
    }
  }

  const handleDeactivate = async () => {
    try {
      await deactivateMutation.mutateAsync(uid)
      toast.success('Mail account disabled')
      setShowDeactivateDialog(false)
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to disable mail'
      )
    }
  }

  const handleVacationToggle = async (enabled: boolean) => {
    try {
      await updateMutation.mutateAsync({
        uid,
        data: { vacationEnabled: enabled },
      })
      toast.success(enabled ? 'Vacation enabled' : 'Vacation disabled')
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to update vacation'
      )
    }
  }

  const handleVacationSave = async () => {
    try {
      await updateMutation.mutateAsync({
        uid,
        data: {
          vacationMessage: vacationMessage || undefined,
          vacationStart: vacationStart
            ? vacationStart.replace(/-/g, '')
            : undefined,
          vacationEnd: vacationEnd ? vacationEnd.replace(/-/g, '') : undefined,
        },
      })
      toast.success('Vacation settings saved')
      setEditingVacation(false)
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to save vacation'
      )
    }
  }

  const handleDeliveryModeChange = async (mode: DeliveryMode) => {
    try {
      await updateMutation.mutateAsync({
        uid,
        data: { deliveryMode: mode },
      })
      toast.success('Delivery mode updated')
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to update delivery mode'
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
            <Mail className="h-5 w-5" />
            Mail Account
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="h-4 w-4" />
            <span>Failed to load mail status</span>
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

  // Mail not activated
  if (!mailStatus?.active) {
    return (
      <>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Mail className="h-5 w-5" />
              Mail Account
            </CardTitle>
            <CardDescription>
              Mail account is not enabled for this user.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <Mail className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">Mail Not Enabled</h3>
              <p className="text-muted-foreground mb-6 max-w-md">
                Enable mail to configure email settings, forwarding, and
                vacation auto-reply for this user.
              </p>
              <Button
                onClick={() => setShowActivateDialog(true)}
                disabled={activateMutation.isPending}
              >
                <Power className="mr-2 h-4 w-4" />
                Enable Mail Account
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Activate Dialog */}
        <Dialog open={showActivateDialog} onOpenChange={setShowActivateDialog}>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle>Enable Mail Account</DialogTitle>
              <DialogDescription>
                Configure mail settings for {displayName}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="mail-address">Email Address *</Label>
                <Input
                  id="mail-address"
                  type="email"
                  placeholder="user@example.com"
                  value={activateMail}
                  onChange={(e) => setActivateMail(e.target.value)}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="mail-quota">
                    <Gauge className="inline h-3.5 w-3.5 mr-1" />
                    Quota (MB)
                  </Label>
                  <Input
                    id="mail-quota"
                    type="number"
                    min={0}
                    value={activateQuota}
                    onChange={(e) =>
                      setActivateQuota(parseInt(e.target.value, 10) || 0)
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    {formatQuota(activateQuota)}
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="mail-server">
                    <HardDrive className="inline h-3.5 w-3.5 mr-1" />
                    Mail Server
                  </Label>
                  <Input
                    id="mail-server"
                    placeholder="mail1.example.com"
                    value={activateServer}
                    onChange={(e) => setActivateServer(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    Optional, uses default if empty
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Alternate Addresses</Label>
                <div className="flex gap-2">
                  <Input
                    type="email"
                    placeholder="alias@example.com"
                    value={activateAliasInput}
                    onChange={(e) => setActivateAliasInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (
                        e.key === 'Enter' &&
                        activateAliasInput.trim() &&
                        !activateAliases.includes(activateAliasInput.trim())
                      ) {
                        e.preventDefault()
                        setActivateAliases([
                          ...activateAliases,
                          activateAliasInput.trim(),
                        ])
                        setActivateAliasInput('')
                      }
                    }}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    disabled={!activateAliasInput.trim()}
                    onClick={() => {
                      if (
                        activateAliasInput.trim() &&
                        !activateAliases.includes(activateAliasInput.trim())
                      ) {
                        setActivateAliases([
                          ...activateAliases,
                          activateAliasInput.trim(),
                        ])
                        setActivateAliasInput('')
                      }
                    }}
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
                {activateAliases.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {activateAliases.map((alias) => (
                      <Badge key={alias} variant="secondary" className="gap-1">
                        {alias}
                        <button
                          type="button"
                          onClick={() =>
                            setActivateAliases(
                              activateAliases.filter((a) => a !== alias)
                            )
                          }
                          className="ml-0.5 hover:text-destructive"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                )}
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
                {activateMutation.isPending ? 'Enabling...' : 'Enable Mail'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </>
    )
  }

  const data = mailStatus.data!
  const quotaPercent = getQuotaPercentage(data.quotaUsedMb, data.quotaMb)

  // Mail activated - show settings
  return (
    <>
      <div className="space-y-4">
        {/* Main Mail Card */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Mail className="h-5 w-5" />
                  Mail Account
                  <Badge variant="secondary">Active</Badge>
                </CardTitle>
                <CardDescription>
                  Mail settings for {displayName}
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
                Primary Email
              </Label>
              <div className="flex items-center gap-2">
                <Input value={data.mail} disabled className="flex-1" />
              </div>
            </div>

            {/* Quota */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label className="flex items-center gap-2">
                  <Gauge className="h-4 w-4" />
                  Quota
                </Label>
                {editingQuota ? (
                  <div className="flex items-center gap-2">
                    <Input
                      type="number"
                      min={0}
                      className="w-28 h-8 text-sm"
                      value={editQuotaValue}
                      onChange={(e) =>
                        setEditQuotaValue(parseInt(e.target.value, 10) || 0)
                      }
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleQuotaSave()
                        if (e.key === 'Escape') setEditingQuota(false)
                      }}
                    />
                    <span className="text-xs text-muted-foreground">MB</span>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={handleQuotaSave}
                      disabled={updateMutation.isPending}
                    >
                      <Check className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={() => setEditingQuota(false)}
                    >
                      <X className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">
                      {formatQuota(data.quotaUsedMb)} / {formatQuota(data.quotaMb)}
                    </span>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => {
                            setEditQuotaValue(data.quotaMb ?? 1024)
                            setEditingQuota(true)
                          }}
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>Edit quota</TooltipContent>
                    </Tooltip>
                  </div>
                )}
              </div>
              {!editingQuota && data.quotaMb && (
                <Progress value={quotaPercent} />
              )}
            </div>

            {/* Delivery Mode */}
            <div className="space-y-2">
              <Label>Delivery Mode</Label>
              <Select
                value={data.deliveryMode}
                onValueChange={(v) => handleDeliveryModeChange(v as DeliveryMode)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="normal">Normal</SelectItem>
                  <SelectItem value="forward_only">Forward Only</SelectItem>
                  <SelectItem value="local_only">Local Only</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {data.deliveryMode === 'forward_only' &&
                  'Mail is forwarded without keeping a local copy'}
                {data.deliveryMode === 'local_only' &&
                  'Only accept mail from local senders'}
                {data.deliveryMode === 'normal' && 'Normal mail delivery'}
              </p>
            </div>

            {/* Alternate Addresses */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label className="flex items-center gap-2">
                  <AtSign className="h-4 w-4" />
                  Alternate Addresses
                </Label>
                {!editingAliases && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => {
                          setEditAliases([...data.alternateAddresses])
                          setEditAliasInput('')
                          setEditingAliases(true)
                        }}
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Edit aliases</TooltipContent>
                  </Tooltip>
                )}
              </div>
              {editingAliases ? (
                <div className="space-y-2">
                  <div className="flex gap-2">
                    <Input
                      type="email"
                      placeholder="alias@example.com"
                      className="h-8 text-sm"
                      value={editAliasInput}
                      onChange={(e) => setEditAliasInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (
                          e.key === 'Enter' &&
                          editAliasInput.trim() &&
                          !editAliases.includes(editAliasInput.trim())
                        ) {
                          e.preventDefault()
                          setEditAliases([...editAliases, editAliasInput.trim()])
                          setEditAliasInput('')
                        }
                      }}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      className="h-8 w-8"
                      disabled={!editAliasInput.trim()}
                      onClick={() => {
                        if (
                          editAliasInput.trim() &&
                          !editAliases.includes(editAliasInput.trim())
                        ) {
                          setEditAliases([...editAliases, editAliasInput.trim()])
                          setEditAliasInput('')
                        }
                      }}
                    >
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {editAliases.map((addr) => (
                      <Badge key={addr} variant="secondary" className="gap-1">
                        {addr}
                        <button
                          type="button"
                          onClick={() =>
                            setEditAliases(editAliases.filter((a) => a !== addr))
                          }
                          className="ml-0.5 hover:text-destructive"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </Badge>
                    ))}
                    {editAliases.length === 0 && (
                      <span className="text-xs text-muted-foreground">No aliases</span>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={handleAliasesSave}
                      disabled={updateMutation.isPending}
                    >
                      {updateMutation.isPending ? 'Saving...' : 'Save'}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setEditingAliases(false)}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {data.alternateAddresses.length > 0 ? (
                    data.alternateAddresses.map((addr) => (
                      <Badge key={addr} variant="outline">
                        {addr}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-sm text-muted-foreground">None</span>
                  )}
                </div>
              )}
            </div>

            {/* Forwarding */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label className="flex items-center gap-2">
                  <Forward className="h-4 w-4" />
                  Forwarding To
                </Label>
                {!editingForwards && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => {
                          setEditForwards([...data.forwardingAddresses])
                          setEditForwardInput('')
                          setEditingForwards(true)
                        }}
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Edit forwarding</TooltipContent>
                  </Tooltip>
                )}
              </div>
              {editingForwards ? (
                <div className="space-y-2">
                  <div className="flex gap-2">
                    <Input
                      type="email"
                      placeholder="forward@example.com"
                      className="h-8 text-sm"
                      value={editForwardInput}
                      onChange={(e) => setEditForwardInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (
                          e.key === 'Enter' &&
                          editForwardInput.trim() &&
                          !editForwards.includes(editForwardInput.trim())
                        ) {
                          e.preventDefault()
                          setEditForwards([
                            ...editForwards,
                            editForwardInput.trim(),
                          ])
                          setEditForwardInput('')
                        }
                      }}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      className="h-8 w-8"
                      disabled={!editForwardInput.trim()}
                      onClick={() => {
                        if (
                          editForwardInput.trim() &&
                          !editForwards.includes(editForwardInput.trim())
                        ) {
                          setEditForwards([
                            ...editForwards,
                            editForwardInput.trim(),
                          ])
                          setEditForwardInput('')
                        }
                      }}
                    >
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {editForwards.map((addr) => (
                      <Badge key={addr} variant="secondary" className="gap-1">
                        {addr}
                        <button
                          type="button"
                          onClick={() =>
                            setEditForwards(
                              editForwards.filter((a) => a !== addr)
                            )
                          }
                          className="ml-0.5 hover:text-destructive"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </Badge>
                    ))}
                    {editForwards.length === 0 && (
                      <span className="text-xs text-muted-foreground">
                        No forwarding addresses
                      </span>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={handleForwardsSave}
                      disabled={updateMutation.isPending}
                    >
                      {updateMutation.isPending ? 'Saving...' : 'Save'}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setEditingForwards(false)}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {data.forwardingAddresses.length > 0 ? (
                    data.forwardingAddresses.map((addr) => (
                      <Badge key={addr} variant="outline">
                        {addr}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-sm text-muted-foreground">None</span>
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Vacation Card */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Palmtree className="h-5 w-5" />
                  Vacation Auto-Reply
                </CardTitle>
                <CardDescription>
                  Automatically reply to incoming messages
                </CardDescription>
              </div>
              <Switch
                checked={data.vacationEnabled}
                onCheckedChange={handleVacationToggle}
              />
            </div>
          </CardHeader>
          {data.vacationEnabled && (
            <CardContent className="space-y-4">
              <Separator />
              {editingVacation ? (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="vacation-message">Message</Label>
                    <Textarea
                      id="vacation-message"
                      placeholder="I'm currently out of office..."
                      value={vacationMessage}
                      onChange={(e) => setVacationMessage(e.target.value)}
                      rows={4}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="vacation-start">Start Date</Label>
                      <Input
                        id="vacation-start"
                        type="date"
                        value={vacationStart}
                        onChange={(e) => setVacationStart(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="vacation-end">End Date</Label>
                      <Input
                        id="vacation-end"
                        type="date"
                        value={vacationEnd}
                        onChange={(e) => setVacationEnd(e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      onClick={handleVacationSave}
                      disabled={updateMutation.isPending}
                    >
                      {updateMutation.isPending ? 'Saving...' : 'Save'}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => setEditingVacation(false)}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {data.vacationMessage && (
                    <div className="p-3 bg-muted rounded-md">
                      <p className="text-sm whitespace-pre-wrap">
                        {data.vacationMessage}
                      </p>
                    </div>
                  )}
                  {(data.vacationStart || data.vacationEnd) && (
                    <div className="flex gap-4 text-sm text-muted-foreground">
                      {data.vacationStart && (
                        <span>From: {formatDate(data.vacationStart)}</span>
                      )}
                      {data.vacationEnd && (
                        <span>Until: {formatDate(data.vacationEnd)}</span>
                      )}
                    </div>
                  )}
                  <Button
                    variant="outline"
                    onClick={() => {
                      setVacationMessage(data.vacationMessage || '')
                      setVacationStart(formatDate(data.vacationStart))
                      setVacationEnd(formatDate(data.vacationEnd))
                      setEditingVacation(true)
                    }}
                  >
                    Edit Settings
                  </Button>
                </div>
              )}
            </CardContent>
          )}
        </Card>
      </div>

      {/* Deactivate Confirmation */}
      <AlertDialog
        open={showDeactivateDialog}
        onOpenChange={setShowDeactivateDialog}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Disable Mail Account</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to disable the mail account for {displayName}
              ? This will remove all mail settings including forwarding and
              vacation configuration.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeactivate}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deactivateMutation.isPending ? 'Disabling...' : 'Disable Mail'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
