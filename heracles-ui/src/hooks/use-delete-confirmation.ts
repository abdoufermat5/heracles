import { useState, useCallback } from 'react'
import { toast } from 'sonner'
import { AppError } from '@/lib/errors'

export interface DeleteConfirmationOptions<T> {
    /** Function to execute the delete */
    onDelete: (item: T) => Promise<void>
    /** Get the display name of the item for the dialog */
    getItemName: (item: T) => string
    /** Entity type for the dialog title, e.g. "User", "Group" */
    entityType: string
    /** Optional success message override */
    successMessage?: (item: T) => string
    /** Optional description override */
    getDescription?: (item: T) => string
}

export interface DeleteConfirmationResult<T> {
    /** The item pending deletion, or null */
    itemToDelete: T | null
    /** Call this to open the delete confirmation dialog */
    requestDelete: (item: T) => void
    /** Call this to execute the deletion */
    confirmDelete: () => Promise<void>
    /** Call this to cancel/close the dialog */
    cancelDelete: () => void
    /** Whether delete is in progress */
    isDeleting: boolean
    /** Props to spread on ConfirmDialog component */
    dialogProps: {
        open: boolean
        onOpenChange: (open: boolean) => void
        title: string
        description: string
        confirmLabel: string
        variant: 'destructive'
        onConfirm: () => Promise<void>
        isLoading: boolean
    }
}

/**
 * Reusable hook for delete confirmation dialogs.
 * Reduces boilerplate from 4x useState + handleDelete + ConfirmDialog to a single hook.
 *
 * @example
 * ```tsx
 * const deleteConfirmation = useDeleteConfirmation({
 *   onDelete: (user) => deleteMutation.mutateAsync(user.uid),
 *   getItemName: (user) => user.uid,
 *   entityType: 'User',
 * })
 *
 * // In JSX:
 * <Button onClick={() => deleteConfirmation.requestDelete(user)}>Delete</Button>
 * <ConfirmDialog {...deleteConfirmation.dialogProps} />
 * ```
 */
export function useDeleteConfirmation<T>(
    options: DeleteConfirmationOptions<T>
): DeleteConfirmationResult<T> {
    const { onDelete, getItemName, entityType, successMessage, getDescription } = options

    const [itemToDelete, setItemToDelete] = useState<T | null>(null)
    const [isDeleting, setIsDeleting] = useState(false)

    const requestDelete = useCallback((item: T) => {
        setItemToDelete(item)
    }, [])

    const cancelDelete = useCallback(() => {
        if (!isDeleting) {
            setItemToDelete(null)
        }
    }, [isDeleting])

    const confirmDelete = useCallback(async () => {
        if (!itemToDelete) return

        setIsDeleting(true)
        try {
            await onDelete(itemToDelete)
            const message =
                successMessage?.(itemToDelete) ??
                `${entityType} "${getItemName(itemToDelete)}" deleted successfully`
            toast.success(message)
            setItemToDelete(null)
        } catch (error) {
            AppError.toastError(error, `Failed to delete ${entityType.toLowerCase()}`)
        } finally {
            setIsDeleting(false)
        }
    }, [itemToDelete, onDelete, entityType, getItemName, successMessage])

    const itemName = itemToDelete ? getItemName(itemToDelete) : ''
    const description = itemToDelete
        ? getDescription?.(itemToDelete) ??
        `Are you sure you want to delete ${entityType.toLowerCase()} "${itemName}"? This action cannot be undone.`
        : `Are you sure you want to delete ${entityType.toLowerCase()}? This action cannot be undone.`

    return {
        itemToDelete,
        requestDelete,
        confirmDelete,
        cancelDelete,
        isDeleting,
        dialogProps: {
            open: !!itemToDelete,
            onOpenChange: (open: boolean) => {
                if (!open) cancelDelete()
            },
            title: `Delete ${entityType}`,
            description,
            confirmLabel: 'Delete',
            variant: 'destructive' as const,
            onConfirm: confirmDelete,
            isLoading: isDeleting,
        },
    }
}
