/**
 * Password Requirements Component
 *
 * Displays password policy requirements fetched from the config API.
 */

import { useConfigCategory } from '@/hooks/use-config'
import { Skeleton } from '@/components/ui/skeleton'
import { AlertCircle } from 'lucide-react'

interface PasswordRequirementsProps {
  className?: string
}

interface PasswordPolicy {
  minLength: number
  requireUppercase: boolean
  requireLowercase: boolean
  requireNumbers: boolean
  requireSpecial: boolean
}

// Default policy used when config is unavailable
const DEFAULT_POLICY: PasswordPolicy = {
  minLength: 8,
  requireUppercase: true,
  requireLowercase: true,
  requireNumbers: true,
  requireSpecial: false,
}

function getPasswordPolicyFromSettings(settings: Array<{ key: string; value: unknown }>): PasswordPolicy {
  const getValue = (key: string, defaultValue: unknown) => {
    const setting = settings.find((s) => s.key === key)
    return setting?.value ?? defaultValue
  }

  return {
    minLength: Number(getValue('min_length', DEFAULT_POLICY.minLength)),
    requireUppercase: Boolean(getValue('require_uppercase', DEFAULT_POLICY.requireUppercase)),
    requireLowercase: Boolean(getValue('require_lowercase', DEFAULT_POLICY.requireLowercase)),
    requireNumbers: Boolean(getValue('require_numbers', DEFAULT_POLICY.requireNumbers)),
    requireSpecial: Boolean(getValue('require_special', DEFAULT_POLICY.requireSpecial)),
  }
}

function buildRequirementsList(policy: PasswordPolicy): string[] {
  const requirements: string[] = []

  requirements.push(`At least ${policy.minLength} characters long`)

  if (policy.requireUppercase && policy.requireLowercase) {
    requirements.push('Must contain uppercase and lowercase letters')
  } else if (policy.requireUppercase) {
    requirements.push('Must contain at least one uppercase letter')
  } else if (policy.requireLowercase) {
    requirements.push('Must contain at least one lowercase letter')
  }

  if (policy.requireNumbers) {
    requirements.push('Must contain at least one number')
  }

  if (policy.requireSpecial) {
    requirements.push('Must contain at least one special character')
  }

  return requirements
}

export function PasswordRequirements({ className }: PasswordRequirementsProps) {
  const { data: passwordCategory, isLoading, isError } = useConfigCategory('password')

  if (isLoading) {
    return (
      <div className={`rounded-md bg-muted/50 p-3 space-y-2 ${className}`}>
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-3 w-48" />
        <Skeleton className="h-3 w-44" />
        <Skeleton className="h-3 w-36" />
      </div>
    )
  }

  // On error, show default requirements with a subtle warning
  if (isError) {
    const requirements = buildRequirementsList(DEFAULT_POLICY)
    return (
      <div className={`rounded-md bg-muted/50 p-3 text-sm text-muted-foreground ${className}`}>
        <div className="flex items-center gap-2 mb-1">
          <p className="font-medium text-foreground">Password Requirements:</p>
          <span className="flex items-center gap-1 text-xs text-amber-600">
            <AlertCircle className="h-3 w-3" />
            defaults
          </span>
        </div>
        <ul className="list-disc list-inside space-y-0.5">
          {requirements.map((req, index) => (
            <li key={index}>{req}</li>
          ))}
        </ul>
      </div>
    )
  }

  const policy = passwordCategory?.settings
    ? getPasswordPolicyFromSettings(passwordCategory.settings)
    : DEFAULT_POLICY

  const requirements = buildRequirementsList(policy)

  return (
    <div className={`rounded-md bg-muted/50 p-3 text-sm text-muted-foreground ${className}`}>
      <p className="font-medium text-foreground mb-1">Password Requirements:</p>
      <ul className="list-disc list-inside space-y-0.5">
        {requirements.map((req, index) => (
          <li key={index}>{req}</li>
        ))}
      </ul>
    </div>
  )
}
