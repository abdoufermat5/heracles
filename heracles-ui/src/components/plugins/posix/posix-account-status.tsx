/**
 * POSIX Account Status Badge
 * 
 * Displays the computed account status with appropriate styling.
 */

import { 
  CheckCircle, 
  XCircle, 
  Clock, 
  AlertTriangle,
  Lock 
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import type { AccountStatus } from '@/types/posix'

interface AccountStatusBadgeProps {
  status: AccountStatus
  className?: string
}

const statusConfig: Record<AccountStatus, {
  label: string
  variant: 'default' | 'secondary' | 'destructive' | 'outline'
  icon: typeof CheckCircle
  description: string
  className?: string
}> = {
  active: {
    label: 'Active',
    variant: 'default',
    icon: CheckCircle,
    description: 'Account is active and password is valid',
    className: 'bg-green-600 hover:bg-green-700',
  },
  expired: {
    label: 'Expired',
    variant: 'destructive',
    icon: XCircle,
    description: 'Account has expired (shadowExpire date passed)',
  },
  password_expired: {
    label: 'Password Expired',
    variant: 'destructive',
    icon: AlertTriangle,
    description: 'Password has expired and must be changed',
  },
  grace_time: {
    label: 'Grace Period',
    variant: 'outline',
    icon: Clock,
    description: 'Password expired but still in grace period',
    className: 'border-yellow-500 text-yellow-600',
  },
  locked: {
    label: 'Locked',
    variant: 'destructive',
    icon: Lock,
    description: 'Account is locked (grace period expired)',
  },
}

export function AccountStatusBadge({ status, className }: AccountStatusBadgeProps) {
  const config = statusConfig[status] || statusConfig.active
  const Icon = config.icon

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge 
            variant={config.variant} 
            className={`${config.className ?? ''} ${className ?? ''}`}
          >
            <Icon className="h-3 w-3 mr-1" />
            {config.label}
          </Badge>
        </TooltipTrigger>
        <TooltipContent>
          <p>{config.description}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

/**
 * Compute account status client-side (for display purposes when not provided by API)
 */
export function computeAccountStatus(
  shadowLastChange?: number,
  shadowMax?: number,
  shadowInactive?: number,
  shadowExpire?: number,
): AccountStatus {
  const today = Math.floor(Date.now() / (1000 * 60 * 60 * 24)) // Days since epoch

  // Check if account has expired
  if (shadowExpire !== undefined && shadowExpire > 0) {
    if (today >= shadowExpire) {
      return 'expired'
    }
  }

  // Check if password has expired
  if (shadowLastChange !== undefined && shadowMax !== undefined) {
    const passwordExpireDate = shadowLastChange + shadowMax

    if (today >= passwordExpireDate) {
      // Password expired, check for grace time
      if (shadowInactive !== undefined && shadowInactive > 0) {
        const graceEnd = passwordExpireDate + shadowInactive
        if (today < graceEnd) {
          return 'grace_time'
        } else {
          return 'locked'
        }
      }
      return 'password_expired'
    }
  }

  // Check if password change is forced (shadowLastChange = 0)
  if (shadowLastChange === 0) {
    return 'password_expired'
  }

  return 'active'
}
