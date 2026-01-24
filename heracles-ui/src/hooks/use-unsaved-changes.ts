import { useEffect, useCallback, useState } from 'react'
import { useBlocker, type Blocker } from 'react-router-dom'

interface UseUnsavedChangesOptions {
  /**
   * Whether there are unsaved changes
   */
  isDirty: boolean
  /**
   * Custom message for the browser's beforeunload dialog (not all browsers show custom messages)
   */
  message?: string
  /**
   * Whether to enable blocking (default: true when isDirty)
   */
  enabled?: boolean
}

interface UseUnsavedChangesReturn {
  /**
   * The blocker state from react-router
   */
  blocker: Blocker
  /**
   * Whether the confirmation dialog should be shown
   */
  showDialog: boolean
  /**
   * Confirm navigation (proceed)
   */
  confirmNavigation: () => void
  /**
   * Cancel navigation (stay on page)
   */
  cancelNavigation: () => void
}

/**
 * Hook to prevent navigation when there are unsaved changes
 *
 * @example
 * const form = useForm()
 * const { blocker, showDialog, confirmNavigation, cancelNavigation } = useUnsavedChanges({
 *   isDirty: form.formState.isDirty,
 * })
 *
 * return (
 *   <>
 *     <form>...</form>
 *     <UnsavedChangesDialog
 *       open={showDialog}
 *       onConfirm={confirmNavigation}
 *       onCancel={cancelNavigation}
 *     />
 *   </>
 * )
 */
export function useUnsavedChanges({
  isDirty,
  message = 'You have unsaved changes. Are you sure you want to leave?',
  enabled = true,
}: UseUnsavedChangesOptions): UseUnsavedChangesReturn {
  const [showDialog, setShowDialog] = useState(false)

  // Block navigation when there are unsaved changes
  const blocker = useBlocker(
    useCallback(
      ({ currentLocation, nextLocation }: { currentLocation: { pathname: string }; nextLocation: { pathname: string } }) =>
        enabled && isDirty && currentLocation.pathname !== nextLocation.pathname,
      [enabled, isDirty]
    )
  )

  // Show dialog when blocker is triggered
  useEffect(() => {
    if (blocker.state === 'blocked') {
      setShowDialog(true)
    }
  }, [blocker.state])

  // Handle browser's beforeunload event
  useEffect(() => {
    if (!enabled || !isDirty) return

    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault()
      // Modern browsers ignore custom messages, but we still need to set returnValue
      e.returnValue = message
      return message
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [enabled, isDirty, message])

  const confirmNavigation = useCallback(() => {
    if (blocker.state === 'blocked') {
      blocker.proceed()
    }
    setShowDialog(false)
  }, [blocker])

  const cancelNavigation = useCallback(() => {
    if (blocker.state === 'blocked') {
      blocker.reset()
    }
    setShowDialog(false)
  }, [blocker])

  return {
    blocker,
    showDialog,
    confirmNavigation,
    cancelNavigation,
  }
}
