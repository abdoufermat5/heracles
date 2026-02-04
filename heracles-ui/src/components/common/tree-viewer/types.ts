import type { ReactNode } from 'react'

/**
 * Base interface for tree node data
 */
export interface TreeNodeData {
  /** Unique identifier for the node */
  id: string
  /** Display label for the node */
  label: string
  /** Optional icon to display */
  icon?: ReactNode
  /** Child nodes */
  children?: TreeNodeData[]
  /** Additional data attached to the node */
  data?: Record<string, unknown>
}

/**
 * Props for custom node rendering
 */
export interface TreeNodeRenderProps<T extends TreeNodeData = TreeNodeData> {
  /** The node data */
  node: T
  /** Current depth level (0-based) */
  depth: number
  /** Whether the node is expanded */
  isExpanded: boolean
  /** Whether the node is selected */
  isSelected: boolean
  /** Whether the node has children */
  hasChildren: boolean
  /** Toggle expanded state */
  onToggle: () => void
  /** Select this node */
  onSelect: () => void
}

/**
 * Configuration for tree viewer behavior
 */
export interface TreeViewerConfig {
  /** Whether to expand all nodes by default */
  defaultExpandAll?: boolean
  /** Initial expanded node IDs */
  defaultExpandedIds?: string[]
  /** Whether to allow multiple selection */
  multiSelect?: boolean
  /** Whether to show connecting lines */
  showLines?: boolean
  /** Whether nodes are collapsible */
  collapsible?: boolean
  /** Animation duration in ms (0 to disable) */
  animationDuration?: number
  /** Indentation per level in pixels */
  indentSize?: number
}

/**
 * Props for the TreeViewer component
 */
export interface TreeViewerProps<T extends TreeNodeData = TreeNodeData> {
  /** Tree data to display */
  data: T[]
  /** Currently selected node ID(s) */
  selectedId?: string | string[]
  /** Called when a node is selected */
  onSelect?: (node: T) => void
  /** Called when a node is double-clicked */
  onDoubleClick?: (node: T) => void
  /** Called when expanded state changes */
  onExpandedChange?: (expandedIds: string[]) => void
  /** Custom node renderer */
  renderNode?: (props: TreeNodeRenderProps<T>) => ReactNode
  /** Custom empty state */
  emptyState?: ReactNode
  /** Configuration options */
  config?: TreeViewerConfig
  /** Additional class name */
  className?: string
}
