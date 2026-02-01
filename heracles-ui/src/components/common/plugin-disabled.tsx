import { PowerOff, Settings } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

interface PluginDisabledProps {
  pluginName: string
  pluginDisplayName?: string
  description?: string
  showSettingsButton?: boolean
}

/**
 * Display a message when a plugin is disabled.
 * Can be used in pages or tabs that depend on a specific plugin.
 */
export function PluginDisabled({
  pluginName,
  pluginDisplayName,
  description,
  showSettingsButton = true,
}: PluginDisabledProps) {
  const navigate = useNavigate()
  const displayName = pluginDisplayName || pluginName.charAt(0).toUpperCase() + pluginName.slice(1)

  return (
    <div className="flex items-center justify-center p-8">
      <Card className="max-w-md">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <div className="rounded-full bg-muted p-4">
              <PowerOff className="h-8 w-8 text-muted-foreground" />
            </div>
          </div>
          <CardTitle>{displayName} Plugin Disabled</CardTitle>
          <CardDescription>
            {description ||
              `The ${displayName} plugin is currently disabled. Enable it in Settings to access this feature.`}
          </CardDescription>
        </CardHeader>
        {showSettingsButton && (
          <CardContent className="flex justify-center">
            <Button onClick={() => navigate('/settings')} variant="outline">
              <Settings className="mr-2 h-4 w-4" />
              Go to Settings
            </Button>
          </CardContent>
        )}
      </Card>
    </div>
  )
}

/**
 * Inline version for use in tabs or smaller spaces
 */
export function PluginDisabledInline({
  pluginName,
  pluginDisplayName,
}: {
  pluginName: string
  pluginDisplayName?: string
}) {
  const navigate = useNavigate()
  const displayName = pluginDisplayName || pluginName.charAt(0).toUpperCase() + pluginName.slice(1)

  return (
    <div className="flex flex-col items-center justify-center py-8 text-center text-muted-foreground">
      <PowerOff className="h-8 w-8 mb-3" />
      <p className="text-sm mb-2">{displayName} plugin is disabled</p>
      <Button
        variant="link"
        size="sm"
        onClick={() => navigate('/settings')}
        className="text-primary"
      >
        Enable in Settings
      </Button>
    </div>
  )
}
