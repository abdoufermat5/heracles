/**
 * DHCP Tree View Component (Refactored)
 *
 * Uses the generic TreeViewer component with DHCP-specific node rendering.
 */

import * as React from 'react'
import {
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
import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { TreeViewer, type TreeNodeData, type TreeNodeRenderProps } from '@/components/common'
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

/**
 * Extended tree node with DHCP-specific data
 */
type DhcpNode = TreeNodeData & {
  objectType: DhcpObjectType
  dhcpComments?: string | null
}

/**
 * Convert DHCP tree node to TreeViewer format
 */
function convertToTreeNodes(node: DhcpTreeNode): DhcpNode {
  const converted: DhcpNode = {
    id: node.dn,
    label: node.cn,
    objectType: node.objectType,
    dhcpComments: node.dhcpComments,
    children: node.children?.map(convertToTreeNodes),
    data: {
      dn: node.dn,
      cn: node.cn,
      objectType: node.objectType,
    },
  }
  return converted
}

/**
 * Custom DHCP node renderer
 */
function DhcpNodeRenderer({
  node,
  isExpanded,
  isSelected,
  hasChildren,
  onToggle,
  onSelect,
}: TreeNodeRenderProps<DhcpNode>) {
  const objectType = node.objectType as DhcpObjectType
  const Icon = ObjectTypeIcon[objectType] || Server
  const colorClass = nodeTypeColors[objectType] || 'text-muted-foreground'
  const typeLabel = DHCP_OBJECT_TYPE_LABELS[objectType] || objectType

  return (
    <div
      className={cn(
        'group flex items-center gap-1 py-1 px-2 rounded-md cursor-pointer transition-colors',
        'hover:bg-muted/50',
        isSelected && 'bg-muted'
      )}
      onClick={onSelect}
    >
      {/* Expand/Collapse button */}
      {hasChildren ? (
        <Button
          variant="ghost"
          size="icon"
          className="h-5 w-5 p-0"
          onClick={(e: React.MouseEvent) => {
            e.stopPropagation()
            onToggle()
          }}
        >
          <svg
            className={cn(
              'h-4 w-4 transition-transform',
              isExpanded && 'rotate-90'
            )}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>
        </Button>
      ) : (
        <span className="w-5" />
      )}

      {/* Type icon with tooltip */}
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
      <span className="text-sm font-medium truncate">{node.label}</span>

      {/* Description if available */}
      {node.dhcpComments && (
        <span className="text-xs text-muted-foreground truncate ml-2">
          - {node.dhcpComments}
        </span>
      )}

      {/* Children count badge */}
      {hasChildren && (
        <Badge variant="secondary" className="ml-auto text-xs h-5">
          {node.children?.length}
        </Badge>
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
  // Convert DHCP tree to TreeViewer format
  const treeData = React.useMemo(() => {
    if (!tree) return []
    return [convertToTreeNodes(tree)]
  }, [tree])

  // Handle selection - convert back to DHCP node format
  const handleSelect = React.useCallback(
    (selectedNode: DhcpNode) => {
      if (onNodeClick) {
        // Reconstruct the original DhcpTreeNode structure
        const dhcpNode: DhcpTreeNode = {
          dn: selectedNode.id,
          cn: selectedNode.label,
          objectType: selectedNode.objectType,
          dhcpComments: selectedNode.dhcpComments,
          children: [], // Children not needed for click handler
        }
        onNodeClick(dhcpNode)
      }
    },
    [onNodeClick]
  )

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
        <Server className="h-8 w-8 mr-3 opacity-30" />
        No DHCP configuration found
      </div>
    )
  }

  return (
    <div className={cn('border rounded-lg bg-card', className)}>
      {/* Legend */}
      <div className="flex flex-wrap gap-3 px-3 py-2 border-b text-xs bg-muted/30">
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
      <div className="p-2">
        <TreeViewer
          data={treeData}
          selectedId={selectedDn}
          onSelect={handleSelect}
          renderNode={DhcpNodeRenderer}
          config={{
            defaultExpandAll: false,
            defaultExpandedIds: tree ? [tree.dn] : [], // Expand root by default
            showLines: false,
            indentSize: 16,
            animationDuration: 150,
          }}
        />
      </div>
    </div>
  )
}
