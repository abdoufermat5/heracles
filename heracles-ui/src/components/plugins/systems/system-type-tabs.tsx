/**
 * System Type Tabs Component
 *
 * Tab navigation for filtering systems by type
 */

import {
  Server,
  Monitor,
  MonitorSmartphone,
  Printer,
  Cpu,
  Phone,
  Smartphone,
  Layers,
} from 'lucide-react'

import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'

import type { SystemType } from '@/types/systems'
import { SYSTEM_TYPE_LABELS } from '@/types/systems'

// Icon mapping
const SystemTypeIcon: Record<SystemType | 'all', React.ElementType> = {
  all: Layers,
  server: Server,
  workstation: Monitor,
  terminal: MonitorSmartphone,
  printer: Printer,
  component: Cpu,
  phone: Phone,
  mobile: Smartphone,
}

interface SystemTypeTabsProps {
  value: SystemType | 'all'
  onValueChange: (value: SystemType | 'all') => void
  counts?: Record<SystemType | 'all', number>
}

export function SystemTypeTabs({
  value,
  onValueChange,
  counts,
}: SystemTypeTabsProps) {
  const tabs: Array<{ value: SystemType | 'all'; label: string }> = [
    { value: 'all', label: 'All Systems' },
    { value: 'server', label: SYSTEM_TYPE_LABELS.server },
    { value: 'workstation', label: SYSTEM_TYPE_LABELS.workstation },
    { value: 'terminal', label: SYSTEM_TYPE_LABELS.terminal },
    { value: 'printer', label: SYSTEM_TYPE_LABELS.printer },
    { value: 'component', label: SYSTEM_TYPE_LABELS.component },
    { value: 'phone', label: SYSTEM_TYPE_LABELS.phone },
    { value: 'mobile', label: SYSTEM_TYPE_LABELS.mobile },
  ]

  return (
    <Tabs value={value} onValueChange={onValueChange as (v: string) => void}>
      <TabsList className="flex flex-wrap h-auto gap-1 bg-transparent p-0">
        {tabs.map((tab) => {
          const Icon = SystemTypeIcon[tab.value]
          const count = counts?.[tab.value]

          return (
            <TabsTrigger
              key={tab.value}
              value={tab.value}
              className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground gap-2"
            >
              <Icon className="h-4 w-4" />
              <span className="hidden sm:inline">{tab.label}</span>
              {count !== undefined && count > 0 && (
                <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-xs">
                  {count}
                </Badge>
              )}
            </TabsTrigger>
          )
        })}
      </TabsList>
    </Tabs>
  )
}
