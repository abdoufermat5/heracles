import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { AppError, ErrorCode } from '@/lib/errors'
import { useAuthStore } from '@/stores/auth-store'
import { ROUTES } from '@/config/constants'

export interface MutationErrorHandlerOptions {
  /**
   * Custom message overrides by error code
   */
  messages?: Partial<Record<ErrorCode, string>>
  /**
   * Whether to show a toast notification (default: true)
   */
  showToast?: boolean
  /**
   * Whether to handle auth errors by redirecting to login (default: true)
   */
  handleAuthErrors?: boolean
  /**
   * Additional callback after error handling
   */
  onError?: (error: AppError) => void
  /**
   * Custom action for the toast
   */
  action?: {
    label: string
    onClick: () => void
  }
}

/**
 * Hook for standardized mutation error handling
 *
 * @example
 * const handleError = useMutationErrorHandler()
 *
 * const mutation = useMutation({
 *   mutationFn: someApi.create,
 *   onError: handleError,
 * })
 */
export function useMutationErrorHandler(options: MutationErrorHandlerOptions = {}) {
  const { showToast = true, handleAuthErrors = true, messages, onError, action } = options
  const navigate = useNavigate()
  const logout = useAuthStore((state) => state.logout)

  return useCallback(
    (error: Error) => {
      // Convert to AppError if needed
      const appError = AppError.isAppError(error) ? error : AppError.from(error)

      // Handle auth errors
      if (handleAuthErrors && appError.isAuthError) {
        logout()
        navigate(ROUTES.LOGIN, { replace: true })

        if (showToast) {
          toast.error(appError.code === ErrorCode.SESSION_EXPIRED
            ? 'Your session has expired. Please log in again.'
            : 'Please log in to continue.')
        }
        return
      }

      // Show toast notification
      if (showToast) {
        const message = messages?.[appError.code] ?? appError.getUserMessage()

        toast.error(message, {
          description: import.meta.env.DEV && appError.message !== message
            ? appError.message
            : undefined,
          action: action
            ? {
                label: action.label,
                onClick: action.onClick,
              }
            : appError.isRetryable
              ? {
                  label: 'Retry',
                  onClick: () => {
                    // This will be overridden by the caller if they want retry functionality
                  },
                }
              : undefined,
        })
      }

      // Call additional error handler
      onError?.(appError)
    },
    [showToast, handleAuthErrors, messages, onError, action, navigate, logout]
  )
}

/**
 * Pre-configured error messages for common operations
 */
export const commonErrorMessages = {
  create: {
    [ErrorCode.VALIDATION_ERROR]: 'Please check your input and try again.',
    [ErrorCode.DUPLICATE_ENTRY]: 'An entry with this name already exists.',
    [ErrorCode.FORBIDDEN]: 'You do not have permission to create this resource.',
  },
  update: {
    [ErrorCode.VALIDATION_ERROR]: 'Please check your input and try again.',
    [ErrorCode.NOT_FOUND]: 'The resource you are trying to update no longer exists.',
    [ErrorCode.CONFLICT]: 'The resource was modified by someone else. Please refresh and try again.',
    [ErrorCode.FORBIDDEN]: 'You do not have permission to update this resource.',
  },
  delete: {
    [ErrorCode.NOT_FOUND]: 'The resource you are trying to delete no longer exists.',
    [ErrorCode.FORBIDDEN]: 'You do not have permission to delete this resource.',
    [ErrorCode.CONFLICT]: 'This resource cannot be deleted because it is in use.',
  },
} as const
