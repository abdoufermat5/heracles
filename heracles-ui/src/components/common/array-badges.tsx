/**
 * Array Badges Component
 *
 * Displays an array of items as badges with overflow handling.
 * Shows a "+N" badge when there are more items than the max.
 */

import { Badge } from '@/components/ui/badge'

interface ArrayBadgesProps {
  /** Array of items to display */
  items: string[]
  /** Maximum number of badges to show before truncating (default: 3) */
  max?: number
  /** Badge variant (default: 'secondary') */
  variant?: 'default' | 'secondary' | 'outline' | 'destructive'
  /** Text to show when array is empty (default: '-') */
  emptyText?: string
  /** Additional CSS classes for the container */
  className?: string
}

export function ArrayBadges({
  items,
  max = 3,
  variant = 'secondary',
  emptyText = '-',
  className,
}: ArrayBadgesProps) {
  if (items.length === 0) {
    return <span className="text-muted-foreground">{emptyText}</span>
  }

  const displayed = items.slice(0, max)
  const remaining = items.length - max

  return (
    <div className={`flex flex-wrap gap-1 ${className ?? ''}`}>
      {displayed.map((item, i) => (
        <Badge key={i} variant={variant} className="text-xs">
          {item}
        </Badge>
      ))}
      {remaining > 0 && (
        <Badge variant="outline" className="text-xs">
          +{remaining}
        </Badge>
      )}
    </div>
  )
}
