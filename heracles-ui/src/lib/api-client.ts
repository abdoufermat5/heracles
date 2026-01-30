import { API_BASE_URL } from '@/config/constants'
import { AppError, ErrorCode } from '@/lib/errors'

const DEFAULT_TIMEOUT = 30000 // 30 seconds

interface ApiErrorResponse {
  detail?: string
  field_errors?: Record<string, string>
  code?: string
}

class ApiClient {
  private baseUrl: string
  private defaultTimeout: number

  constructor(baseUrl: string = API_BASE_URL, timeout: number = DEFAULT_TIMEOUT) {
    this.baseUrl = baseUrl
    this.defaultTimeout = timeout
  }

  // Tokens are now handled by HttpOnly cookies
  clearTokens(): void {
    // No-op
  }

  private async refreshAccessToken(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
      })

      return response.ok
    } catch {
      return false
    }
  }

  async request<T>(
    endpoint: string,
    options: RequestInit = {},
    timeout: number = this.defaultTimeout
  ): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    }

    // Create abort controller for timeout
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), timeout)

    let response: Response
    try {
      response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers,
        credentials: 'include',
        signal: controller.signal,
      })
    } catch (error) {
      clearTimeout(timeoutId)
      throw AppError.fromNetworkError(error instanceof Error ? error : new Error(String(error)))
    }
    clearTimeout(timeoutId)

    // Try to refresh token on 401
    if (response.status === 401) {
      const refreshed = await this.refreshAccessToken()
      if (refreshed) {

        const retryController = new AbortController()
        const retryTimeoutId = setTimeout(() => retryController.abort(), timeout)

        try {
          response = await fetch(`${this.baseUrl}${endpoint}`, {
            ...options,
            headers,
            credentials: 'include',
            signal: retryController.signal,
          })
        } catch (error) {
          clearTimeout(retryTimeoutId)
          throw AppError.fromNetworkError(
            error instanceof Error ? error : new Error(String(error))
          )
        }
        clearTimeout(retryTimeoutId)
      } else {
        // Token refresh failed, throw session expired error
        throw new AppError({
          message: 'Session expired',
          code: ErrorCode.SESSION_EXPIRED,
          statusCode: 401,
        })
      }
    }

    if (!response.ok) {
      const errorBody: ApiErrorResponse = await response.json().catch(() => ({
        detail: 'An unexpected error occurred',
      }))
      throw AppError.fromApiResponse(response, errorBody)
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return {} as T
    }

    return response.json()
  }

  async get<T>(endpoint: string, params?: Record<string, string | number | undefined>): Promise<T> {
    let url = endpoint
    if (params) {
      const searchParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          searchParams.append(key, String(value))
        }
      })
      const queryString = searchParams.toString()
      if (queryString) {
        url = `${endpoint}?${queryString}`
      }
    }
    return this.request<T>(url)
  }

  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async put<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async patch<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' })
  }
}

export const apiClient = new ApiClient()
