import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'
import { FileQuestion } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface EmptyStateProps {
  icon?: LucideIcon
  illustration?: ReactNode
  title: string
  description?: string
  action?: {
    label: string
    onClick: () => void
  }
  secondaryAction?: {
    label: string
    onClick: () => void
  }
}

function DefaultIllustration() {
  return (
    <svg
      viewBox="0 0 120 120"
      className="h-20 w-20 text-muted-foreground"
      aria-hidden="true"
    >
      <circle cx="60" cy="60" r="48" fill="currentColor" opacity="0.08" />
      <rect x="34" y="36" width="52" height="60" rx="8" fill="currentColor" opacity="0.12" />
      <rect x="42" y="46" width="36" height="6" rx="3" fill="currentColor" opacity="0.35" />
      <rect x="42" y="58" width="28" height="6" rx="3" fill="currentColor" opacity="0.25" />
      <rect x="42" y="70" width="22" height="6" rx="3" fill="currentColor" opacity="0.2" />
      <circle cx="78" cy="82" r="10" fill="currentColor" opacity="0.16" />
    </svg>
  )
}

export function EmptyState({
  icon: Icon = FileQuestion,
  illustration,
  title,
  description,
  action,
  secondaryAction,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="relative mb-4">
        <div className="absolute inset-0 rounded-full bg-muted/40 blur-2xl" />
        <div className="relative flex items-center justify-center">
          {illustration ?? <DefaultIllustration />}
        </div>
      </div>
      <Icon className="h-5 w-5 text-muted-foreground mb-2" />
      <h3 className="text-lg font-semibold">{title}</h3>
      {description && (
        <p className="text-muted-foreground mt-2 max-w-md">{description}</p>
      )}
      {(action || secondaryAction) && (
        <div className="mt-4 flex items-center gap-2">
          {action && (
            <Button onClick={action.onClick}>
              {action.label}
            </Button>
          )}
          {secondaryAction && (
            <Button variant="outline" onClick={secondaryAction.onClick}>
              {secondaryAction.label}
            </Button>
          )}
        </div>
      )}
    </div>
  )
}
