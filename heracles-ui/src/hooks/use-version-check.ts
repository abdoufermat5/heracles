/**
 * API Version Checking Hook
 *
 * Checks compatibility between the UI and API versions at startup.
 * Shows a non-blocking warning if versions are incompatible.
 */

import { useEffect, useState } from 'react'
import { API_BASE_URL, APP_VERSION } from '@/config/constants'
import { toast } from 'sonner'

interface VersionInfo {
  api: string
  core: string | null
  plugins_package: string | null
  plugins: Array<{
    name: string
    version: string
    minimum_api_version: string | null
  }>
  supported_api_versions: string[]
}

interface CompatibilityResult {
  compatible: boolean
  api_version: string
  warnings: string[]
  errors: string[]
}

interface UseVersionCheckResult {
  isChecking: boolean
  isCompatible: boolean | null
  apiVersion: string | null
  coreVersion: string | null
  warnings: string[]
  versionInfo: VersionInfo | null
}

export function useVersionCheck(): UseVersionCheckResult {
  const [isChecking, setIsChecking] = useState(true)
  const [isCompatible, setIsCompatible] = useState<boolean | null>(null)
  const [apiVersion, setApiVersion] = useState<string | null>(null)
  const [coreVersion, setCoreVersion] = useState<string | null>(null)
  const [warnings, setWarnings] = useState<string[]>([])
  const [versionInfo, setVersionInfo] = useState<VersionInfo | null>(null)

  useEffect(() => {
    const checkVersion = async () => {
      try {
        // First, fetch version info
        const versionResponse = await fetch(`${API_BASE_URL}/version`, {
          credentials: 'include',
        })

        if (versionResponse.ok) {
          const info: VersionInfo = await versionResponse.json()
          setVersionInfo(info)
          setApiVersion(info.api)
          setCoreVersion(info.core)
        }

        // Then check compatibility
        const compatResponse = await fetch(
          `${API_BASE_URL}/version/compatibility?client_version=${APP_VERSION}&client_type=ui`,
          {
            credentials: 'include',
          }
        )

        if (compatResponse.ok) {
          const result: CompatibilityResult = await compatResponse.json()
          setIsCompatible(result.compatible)
          setWarnings([...result.warnings, ...result.errors])

          // Show toast for warnings (non-blocking)
          if (result.errors.length > 0) {
            toast.error('Version Incompatibility', {
              description: result.errors.join('. '),
              duration: 10000,
            })
          } else if (result.warnings.length > 0) {
            toast.warning('Version Notice', {
              description: result.warnings.join('. '),
              duration: 8000,
            })
          }
        }
      } catch (error) {
        // Don't block the app if version check fails
        console.warn('Version check failed:', error)
        setWarnings(['Could not verify API compatibility'])
      } finally {
        setIsChecking(false)
      }
    }

    checkVersion()
  }, [])

  return {
    isChecking,
    isCompatible,
    apiVersion,
    coreVersion,
    warnings,
    versionInfo,
  }
}
