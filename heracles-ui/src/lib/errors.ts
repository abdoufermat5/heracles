/**
 * Error handling utilities for Heracles UI
 * Provides structured error types with user-friendly messages
 */

export const ErrorCode = {
  // Authentication errors (401)
  UNAUTHORIZED: 'UNAUTHORIZED',
  SESSION_EXPIRED: 'SESSION_EXPIRED',

  // Authorization errors (403)
  FORBIDDEN: 'FORBIDDEN',

  // Validation errors (400, 422)
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  INVALID_INPUT: 'INVALID_INPUT',

  // Conflict errors (409)
  CONFLICT: 'CONFLICT',
  DUPLICATE_ENTRY: 'DUPLICATE_ENTRY',

  // Not found errors (404)
  NOT_FOUND: 'NOT_FOUND',

  // Server errors (500+)
  INTERNAL_ERROR: 'INTERNAL_ERROR',
  SERVICE_UNAVAILABLE: 'SERVICE_UNAVAILABLE',

  // Network errors
  NETWORK_ERROR: 'NETWORK_ERROR',
  TIMEOUT: 'TIMEOUT',

  // Generic
  UNKNOWN: 'UNKNOWN',
} as const

export type ErrorCode = (typeof ErrorCode)[keyof typeof ErrorCode]

const USER_MESSAGES: Record<ErrorCode, string> = {
  [ErrorCode.UNAUTHORIZED]: 'Please log in to continue.',
  [ErrorCode.SESSION_EXPIRED]: 'Your session has expired. Please log in again.',
  [ErrorCode.FORBIDDEN]: 'You do not have permission to perform this action.',
  [ErrorCode.VALIDATION_ERROR]: 'Please check your input and try again.',
  [ErrorCode.INVALID_INPUT]: 'The provided data is invalid.',
  [ErrorCode.CONFLICT]: 'This operation conflicts with existing data.',
  [ErrorCode.DUPLICATE_ENTRY]: 'This entry already exists.',
  [ErrorCode.NOT_FOUND]: 'The requested resource was not found.',
  [ErrorCode.INTERNAL_ERROR]: 'An unexpected error occurred. Please try again later.',
  [ErrorCode.SERVICE_UNAVAILABLE]: 'The service is temporarily unavailable. Please try again later.',
  [ErrorCode.NETWORK_ERROR]: 'Unable to connect to the server. Please check your connection.',
  [ErrorCode.TIMEOUT]: 'The request timed out. Please try again.',
  [ErrorCode.UNKNOWN]: 'An unexpected error occurred.',
}

const RETRYABLE_ERRORS: ErrorCode[] = [
  ErrorCode.NETWORK_ERROR,
  ErrorCode.TIMEOUT,
  ErrorCode.SERVICE_UNAVAILABLE,
  ErrorCode.INTERNAL_ERROR,
]

export interface AppErrorOptions {
  message: string
  code: ErrorCode
  statusCode?: number
  details?: Record<string, unknown>
  fieldErrors?: Record<string, string>
  cause?: Error
}

export class AppError extends Error {
  public readonly code: ErrorCode
  public readonly statusCode?: number
  public readonly details?: Record<string, unknown>
  public readonly fieldErrors?: Record<string, string>
  public readonly timestamp: Date

  constructor(options: AppErrorOptions) {
    super(options.message)
    this.name = 'AppError'
    this.code = options.code
    this.statusCode = options.statusCode
    this.details = options.details
    this.fieldErrors = options.fieldErrors
    this.cause = options.cause
    this.timestamp = new Date()

    // Maintains proper stack trace for where error was thrown (V8 only)
    const ErrorWithCapture = Error as typeof Error & {
      captureStackTrace?: (targetObject: object, constructorOpt?: Function) => void
    }
    if (typeof ErrorWithCapture.captureStackTrace === 'function') {
      ErrorWithCapture.captureStackTrace(this, AppError)
    }
  }

  /**
   * Whether this error can be retried
   */
  get isRetryable(): boolean {
    return RETRYABLE_ERRORS.includes(this.code)
  }

  /**
   * Whether this is an authentication error requiring login
   */
  get isAuthError(): boolean {
    return this.code === ErrorCode.UNAUTHORIZED || this.code === ErrorCode.SESSION_EXPIRED
  }

  /**
   * Get validation errors array if present
   */
  getValidationErrors(): string[] {
    const errors = this.details?.validationErrors
    return Array.isArray(errors) ? errors : []
  }

  /**
   * Get a user-friendly message for display
   */
  getUserMessage(): string {
    // Use validation errors if present
    const validationErrors = this.getValidationErrors()
    if (validationErrors.length > 0) {
      return validationErrors.join('. ')
    }

    // Use field errors if present
    if (this.fieldErrors && Object.keys(this.fieldErrors).length > 0) {
      return Object.values(this.fieldErrors).join('. ')
    }

    // Use API detail message if it's user-friendly
    if (this.message && !this.message.includes('HTTP') && this.message.length < 200) {
      return this.message
    }

    // Fall back to default message for error code
    return USER_MESSAGES[this.code] || USER_MESSAGES[ErrorCode.UNKNOWN]
  }

  /**
   * Create an AppError from an API response
   */
  static fromApiResponse(
    response: Response,
    body?: { detail?: string | { message?: string; errors?: string[] }; field_errors?: Record<string, string>; code?: string }
  ): AppError {
    const statusCode = response.status
    let code: ErrorCode
    let validationErrors: string[] | undefined
    
    // Handle structured detail object or plain string
    let message: string
    if (body?.detail && typeof body.detail === 'object') {
      message = body.detail.message || `HTTP ${statusCode}`
      validationErrors = body.detail.errors
    } else {
      message = (body?.detail as string) || `HTTP ${statusCode}`
    }

    // Map HTTP status to error code
    switch (statusCode) {
      case 400:
      case 422:
        code = ErrorCode.VALIDATION_ERROR
        break
      case 401:
        code = ErrorCode.UNAUTHORIZED
        break
      case 403:
        code = ErrorCode.FORBIDDEN
        break
      case 404:
        code = ErrorCode.NOT_FOUND
        break
      case 409:
        code = body?.code === 'DUPLICATE' ? ErrorCode.DUPLICATE_ENTRY : ErrorCode.CONFLICT
        break
      case 503:
        code = ErrorCode.SERVICE_UNAVAILABLE
        break
      default:
        if (statusCode >= 500) {
          code = ErrorCode.INTERNAL_ERROR
        } else {
          code = ErrorCode.UNKNOWN
        }
    }

    return new AppError({
      message,
      code,
      statusCode,
      details: {
        ...body as Record<string, unknown>,
        validationErrors,
      },
      fieldErrors: body?.field_errors,
    })
  }

  /**
   * Create an AppError from a network error
   */
  static fromNetworkError(error: Error): AppError {
    const isTimeout = error.name === 'AbortError' || error.message.includes('timeout')

    return new AppError({
      message: error.message,
      code: isTimeout ? ErrorCode.TIMEOUT : ErrorCode.NETWORK_ERROR,
      cause: error,
    })
  }

  /**
   * Type guard to check if an error is an AppError
   */
  static isAppError(error: unknown): error is AppError {
    return error instanceof AppError
  }

  /**
   * Convert any error to an AppError
   */
  static from(error: unknown): AppError {
    if (AppError.isAppError(error)) {
      return error
    }

    if (error instanceof Error) {
      return new AppError({
        message: error.message,
        code: ErrorCode.UNKNOWN,
        cause: error,
      })
    }

    return new AppError({
      message: String(error),
      code: ErrorCode.UNKNOWN,
    })
  }

  /**
   * Display error as toast notification(s)
   * Shows each validation error separately, or a single error message
   */
  static toastError(error: unknown, fallbackMessage = 'An error occurred'): void {
    // Dynamic import to avoid circular dependency
    import('sonner').then(({ toast }) => {
      const appError = AppError.from(error)
      const validationErrors = appError.getValidationErrors()
      
      if (validationErrors.length > 0) {
        // Show each validation error as a separate toast
        validationErrors.forEach((err) => toast.error(err))
      } else {
        const message = appError.getUserMessage()
        toast.error(message || fallbackMessage)
      }
    })
  }}