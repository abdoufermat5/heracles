import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const sizeClasses = {
  sm: 'h-4 w-4',
  md: 'h-8 w-8',
  lg: 'h-12 w-12',
}

export function LoadingSpinner({ size = 'md', className }: LoadingSpinnerProps) {
  return (
    <Loader2 className={cn('animate-spin text-primary', sizeClasses[size], className)} />
  )
}

interface LoadingPageProps {
  message?: string
}

export function LoadingPage({ message = 'Loading...' }: LoadingPageProps) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background/50 backdrop-blur-sm">
      <div className="relative flex flex-col items-center gap-6">
        <div className="relative">
          <div className="absolute inset-0 animate-ping rounded-full bg-primary/20 duration-1000" />
          <div className="relative flex h-24 w-24 items-center justify-center rounded-full bg-background shadow-xl ring-1 ring-border">
            <img
              src="/logo-icon.png"
              alt="Loading..."
              className="h-12 w-12 object-contain animate-pulse"
            />
          </div>
        </div>

        <div className="flex flex-col items-center gap-2">
          <h3 className="text-xl font-semibold tracking-tight text-foreground">Heracles</h3>
          <div className="flex items-center gap-2">
            <LoadingSpinner size="sm" />
            <p className="text-sm text-muted-foreground">{message}</p>
          </div>
        </div>
      </div>
    </div>
  )
}
