import type { LucideIcon } from 'lucide-react'
import { AlertTriangle, Power } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

/* ---------- Loading Skeleton ---------- */

interface PluginTabSkeletonProps {
  /** Number of skeleton rows in the card body (default 2) */
  rows?: number
}

export function PluginTabSkeleton({ rows = 2 }: PluginTabSkeletonProps) {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-4 w-72" />
      </CardHeader>
      <CardContent className="space-y-4">
        {Array.from({ length: rows }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </CardContent>
    </Card>
  )
}

/* ---------- Error State ---------- */

interface PluginTabErrorProps {
  icon: LucideIcon
  title: string
  message: string
  onRetry: () => void
}

export function PluginTabError({ icon: Icon, title, message, onRetry }: PluginTabErrorProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Icon className="h-5 w-5" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-2 text-destructive">
          <AlertTriangle className="h-4 w-4" />
          <span>{message}</span>
        </div>
        <Button variant="outline" size="sm" className="mt-4" onClick={onRetry}>
          Retry
        </Button>
      </CardContent>
    </Card>
  )
}

/* ---------- Inactive / Not-Enabled State ---------- */

interface PluginTabInactiveProps {
  icon: LucideIcon
  title: string
  heading: string
  description: string
  /** Text on the activate button (e.g. "Enable SSH") */
  activateLabel: string
  onActivate: () => void
  isActivating?: boolean
}

export function PluginTabInactive({
  icon: Icon,
  title,
  heading,
  description,
  activateLabel,
  onActivate,
  isActivating = false,
}: PluginTabInactiveProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Icon className="h-5 w-5" />
          {title}
        </CardTitle>
        <CardDescription>
          {title} is not enabled for this user.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <Icon className="h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-lg font-medium mb-2">{heading}</h3>
          <p className="text-muted-foreground mb-6 max-w-md">{description}</p>
          <Button onClick={onActivate} disabled={isActivating}>
            <Power className="mr-2 h-4 w-4" />
            {isActivating ? 'Enabling...' : activateLabel}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
