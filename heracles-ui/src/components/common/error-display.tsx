import { AlertCircle, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'

interface ErrorDisplayProps {
  title?: string
  message: string
  onRetry?: () => void
}

export function ErrorDisplay({ title = 'Error', message, onRetry }: ErrorDisplayProps) {
  return (
    <Card className="border-destructive">
      <CardContent className="flex flex-col items-center justify-center py-8 text-center">
        <AlertCircle className="h-12 w-12 text-destructive mb-4" />
        <h3 className="text-lg font-semibold">{title}</h3>
        <p className="text-muted-foreground mt-2 max-w-md">{message}</p>
        {onRetry && (
          <Button variant="outline" className="mt-4" onClick={onRetry}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Try again
          </Button>
        )}
      </CardContent>
    </Card>
  )
}
