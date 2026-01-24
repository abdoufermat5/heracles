/**
 * Delete Dialog Component
 *
 * Specialized confirmation dialog for delete operations.
 * Provides consistent UX for all delete confirmations across the app.
 */

import { ConfirmDialog } from '../confirm-dialog'

interface DeleteDialogProps {
  /** Whether the dialog is open */
  open: boolean
  /** Callback when open state changes */
  onOpenChange: (open: boolean) => void
  /** Name of the item being deleted (displayed in confirmation) */
  itemName: string
  /** Type of item (e.g., 'user', 'group', 'role') */
  itemType?: string
  /** Optional custom title (defaults to "Delete {itemType}?") */
  title?: string
  /** Optional custom description */
  description?: string
  /** Callback when deletion is confirmed */
  onConfirm: () => void
  /** Whether the delete operation is in progress */
  isLoading?: boolean
}

export function DeleteDialog({
  open,
  onOpenChange,
  itemName,
  itemType = 'item',
  title,
  description,
  onConfirm,
  isLoading = false,
}: DeleteDialogProps) {
  const defaultTitle = `Delete ${itemType}?`
  const defaultDescription = `Are you sure you want to delete "${itemName}"? This action cannot be undone.`

  return (
    <ConfirmDialog
      open={open}
      onOpenChange={onOpenChange}
      title={title ?? defaultTitle}
      description={description ?? defaultDescription}
      confirmLabel="Delete"
      cancelLabel="Cancel"
      variant="destructive"
      onConfirm={onConfirm}
      isLoading={isLoading}
    />
  )
}
