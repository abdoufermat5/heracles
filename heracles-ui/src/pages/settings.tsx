import { PageHeader, EmptyState } from '@/components/common'
import { Settings } from 'lucide-react'

export function SettingsPage() {
  return (
    <div>
      <PageHeader
        title="Settings"
        description="Configure your Heracles instance"
        breadcrumbs={[{ label: 'Settings' }]}
      />

      <EmptyState
        icon={Settings}
        title="Coming Soon"
        description="Settings will be available in a future release"
      />
    </div>
  )
}
