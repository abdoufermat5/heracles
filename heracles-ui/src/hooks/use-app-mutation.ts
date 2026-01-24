import {
  useMutation,
  type UseMutationOptions,
  type UseMutationResult,
} from '@tanstack/react-query'
import { toast } from 'sonner'
import { type AppError, type ErrorCode } from '@/lib/errors'
import { useMutationErrorHandler } from './use-mutation-error-handler'

export interface AppMutationOptions<TData, TError, TVariables, TContext>
  extends Omit<UseMutationOptions<TData, TError, TVariables, TContext>, 'onError' | 'onSuccess'> {
  /**
   * Success message to display as a toast
   */
  successMessage?: string | ((data: TData, variables: TVariables) => string)
  /**
   * Custom error messages by error code
   */
  errorMessages?: Partial<Record<ErrorCode, string>>
  /**
   * Whether to show error toast (default: true)
   */
  showErrorToast?: boolean
  /**
   * Whether to handle auth errors automatically (default: true)
   */
  handleAuthErrors?: boolean
  /**
   * Success handler
   */
  onSuccess?: (data: TData, variables: TVariables, context: TContext) => void
  /**
   * Additional error handler (called after toast)
   */
  onError?: (error: AppError, variables: TVariables, context: TContext | undefined) => void
}

/**
 * Wrapper around useMutation with built-in error handling and success toasts
 *
 * @example
 * const createUser = useAppMutation({
 *   mutationFn: usersApi.create,
 *   successMessage: 'User created successfully',
 *   errorMessages: {
 *     [ErrorCode.DUPLICATE_ENTRY]: 'A user with this UID already exists.',
 *   },
 *   onSuccess: () => {
 *     queryClient.invalidateQueries({ queryKey: userKeys.lists() })
 *   },
 * })
 */
export function useAppMutation<
  TData = unknown,
  TError = Error,
  TVariables = void,
  TContext = unknown,
>(
  options: AppMutationOptions<TData, TError, TVariables, TContext>
): UseMutationResult<TData, TError, TVariables, TContext> {
  const {
    successMessage,
    errorMessages,
    showErrorToast = true,
    handleAuthErrors = true,
    onError: customOnError,
    onSuccess: customOnSuccess,
    ...mutationOptions
  } = options

  const handleError = useMutationErrorHandler({
    messages: errorMessages,
    showToast: showErrorToast,
    handleAuthErrors,
  })

  return useMutation({
    ...mutationOptions,
    onSuccess: (data, variables, context) => {
      // Show success toast if message provided
      if (successMessage) {
        const message =
          typeof successMessage === 'function' ? successMessage(data, variables) : successMessage
        toast.success(message)
      }

      // Call custom onSuccess
      customOnSuccess?.(data, variables, context)
    },
    onError: (error, variables, context) => {
      // Handle error with standardized handler
      handleError(error as Error)

      // Call custom error handler
      customOnError?.(error as unknown as AppError, variables, context)
    },
  }) as UseMutationResult<TData, TError, TVariables, TContext>
}
