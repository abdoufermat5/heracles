/**
 * DHCP Tree View Component
 *
 * Displays the hierarchical structure of a DHCP service configuration.
 */

import { useState } from 'react'
import {
  ChevronRight,
  ChevronDown,
  Server,
  Network,
  Blocks,
  Layers,
  Monitor,
  Users,
  Tag,
  Tags,
  Key,
  Globe,
  RefreshCw,
} from 'lucide-react'

import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import type { DhcpTreeNode, DhcpObjectType } from '@/types/dhcp'
import { DHCP_OBJECT_TYPE_LABELS } from '@/types/dhcp'

// Icon mapping for DHCP object types
const ObjectTypeIcon: Record<DhcpObjectType, React.ElementType> = {
  service: Server,
  shared_network: Network,
  subnet: Blocks,
  pool: Layers,
  host: Monitor,
  group: Users,
  class: Tag,
  subclass: Tags,
  tsig_key: Key,
  dns_zone: Globe,
  failover_peer: RefreshCw,
}

// Color mapping for different node types
const nodeTypeColors: Record<DhcpObjectType, string> = {
  service: 'text-blue-600 dark:text-blue-400',
  shared_network: 'text-purple-600 dark:text-purple-400',
  subnet: 'text-green-600 dark:text-green-400',
  pool: 'text-orange-600 dark:text-orange-400',
  host: 'text-cyan-600 dark:text-cyan-400',
  group: 'text-yellow-600 dark:text-yellow-400',
  class: 'text-pink-600 dark:text-pink-400',
  subclass: 'text-pink-500 dark:text-pink-300',
  tsig_key: 'text-red-600 dark:text-red-400',
  dns_zone: 'text-teal-600 dark:text-teal-400',
  failover_peer: 'text-indigo-600 dark:text-indigo-400',
}

interface TreeNodeProps {
  node: DhcpTreeNode
  level: number
  onNodeClick?: (node: DhcpTreeNode) => void
  selectedDn?: string
}

function TreeNodeComponent({
  node,
  level,
  onNodeClick,
  selectedDn,
}: TreeNodeProps) {
  const [isExpanded, setIsExpanded] = useState(level < 2)
  const hasChildren = node.children && node.children.length > 0
  // Use Server as fallback icon if objectType is not in mapping
  const Icon = ObjectTypeIcon[node.objectType] || Server
  const colorClass = nodeTypeColors[node.objectType] || 'text-muted-foreground'
  const typeLabel = DHCP_OBJECT_TYPE_LABELS[node.objectType] || node.objectType
  const isSelected = selectedDn === node.dn

  return (
    <div className="select-none">
      <div
        className={cn(
          'flex items-center gap-1 py-1 px-2 rounded-md cursor-pointer hover:bg-muted/50 transition-colors',
          isSelected && 'bg-muted'
        )}
        style={{ paddingLeft: `${level * 16 + 8}px` }}
        onClick={() => onNodeClick?.(node)}
      >
        {/* Expand/Collapse button */}
        {hasChildren ? (
          <Button
            variant="ghost"
            size="icon"
            className="h-5 w-5 p-0"
            onClick={(e) => {
              e.stopPropagation()
              setIsExpanded(!isExpanded)
            }}
          >
            {isExpanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </Button>
        ) : (
          <span className="w-5" />
        )}

        {/* Type icon */}
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <span className={colorClass}>
                <Icon className="h-4 w-4" />
              </span>
            </TooltipTrigger>
            <TooltipContent>{typeLabel}</TooltipContent>
          </Tooltip>
        </TooltipProvider>

        {/* Node name */}
        <span className="text-sm font-medium truncate">{node.cn}</span>

        {/* Description if available */}
        {node.dhcpComments && (
          <span className="text-xs text-muted-foreground truncate ml-2">
            - {node.dhcpComments}
          </span>
        )}

        {/* Children count badge */}
        {hasChildren && (
          <span className="ml-auto text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
            {node.children.length}
          </span>
        )}
      </div>

      {/* Children */}
      {isExpanded && hasChildren && (
        <div>
          {node.children.map((child) => (
            <TreeNodeComponent
              key={child.dn}
              node={child}
              level={level + 1}
              onNodeClick={onNodeClick}
              selectedDn={selectedDn}
            />
          ))}
        </div>
      )}
    </div>
  )
}

interface DhcpTreeViewProps {
  tree: DhcpTreeNode | null
  isLoading?: boolean
  onNodeClick?: (node: DhcpTreeNode) => void
  selectedDn?: string
  className?: string
}

export function DhcpTreeView({
  tree,
  isLoading = false,
  onNodeClick,
  selectedDn,
  className,
}: DhcpTreeViewProps) {
  if (isLoading) {
    return (
      <div className={cn('flex items-center justify-center py-8', className)}>
        <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!tree) {
    return (
      <div className={cn('flex items-center justify-center py-8 text-muted-foreground', className)}>
        No DHCP configuration found
      </div>
    )
  }

  return (
    <div className={cn('border rounded-lg p-2 bg-card', className)}>
      {/* Legend */}
      <div className="flex flex-wrap gap-3 px-2 py-2 mb-2 border-b text-xs">
        {Object.entries(DHCP_OBJECT_TYPE_LABELS).map(([type, label]) => {
          const Icon = ObjectTypeIcon[type as DhcpObjectType]
          return (
            <div key={type} className="flex items-center gap-1">
              <Icon className={cn('h-3 w-3', nodeTypeColors[type as DhcpObjectType])} />
              <span className="text-muted-foreground">{label}</span>
            </div>
          )
        })}
      </div>

      {/* Tree */}
      <TreeNodeComponent
        node={tree}
        level={0}
        onNodeClick={onNodeClick}
        selectedDn={selectedDn}
      />
    </div>
  )
}
