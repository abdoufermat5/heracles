import { API_BASE_URL, TOKEN_STORAGE_KEY, REFRESH_TOKEN_KEY } from '@/config/constants'
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

  private getToken(): string | null {
    return localStorage.getItem(TOKEN_STORAGE_KEY)
  }

  private getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY)
  }

  private setTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem(TOKEN_STORAGE_KEY, accessToken)
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
  }

  clearTokens(): void {
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
  }

  private async refreshAccessToken(): Promise<boolean> {
    const refreshToken = this.getRefreshToken()
    if (!refreshToken) return false

    try {
      const response = await fetch(`${this.baseUrl}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })

      if (!response.ok) return false

      const data = await response.json()
      this.setTokens(data.access_token, data.refresh_token)
      return true
    } catch {
      return false
    }
  }

  async request<T>(
    endpoint: string,
    options: RequestInit = {},
    timeout: number = this.defaultTimeout
  ): Promise<T> {
    const token = this.getToken()
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    }

    if (token) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`
    }

    // Create abort controller for timeout
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), timeout)

    let response: Response
    try {
      response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers,
        signal: controller.signal,
      })
    } catch (error) {
      clearTimeout(timeoutId)
      throw AppError.fromNetworkError(error instanceof Error ? error : new Error(String(error)))
    }
    clearTimeout(timeoutId)

    // Try to refresh token on 401
    if (response.status === 401 && token) {
      const refreshed = await this.refreshAccessToken()
      if (refreshed) {
        const newToken = this.getToken()
        ;(headers as Record<string, string>)['Authorization'] = `Bearer ${newToken}`

        const retryController = new AbortController()
        const retryTimeoutId = setTimeout(() => retryController.abort(), timeout)

        try {
          response = await fetch(`${this.baseUrl}${endpoint}`, {
            ...options,
            headers,
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
