import { PageHeader, EmptyState } from '@/components/common'
import { Server } from 'lucide-react'

export function SystemsPage() {
  return (
    <div>
      <PageHeader
        title="Systems"
        description="Manage systems and machines in the directory"
      />

      <EmptyState
        icon={Server}
        title="Coming Soon"
        description="System management will be available in a future release"
      />
    </div>
  )
}
